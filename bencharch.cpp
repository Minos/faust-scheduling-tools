#include <perfmon/pfmlib_perf_event.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <format>
#include <functional>
#include <iostream>

#define NBSAMPLES 44100
#define NBITERATIONS 1000
#define NBCOUNTERS 4

#ifndef FAUSTFLOAT
#define FAUSTFLOAT float
#endif

#ifndef FAUSTCLASS
#define FAUSTCLASS mydsp
#endif

#ifdef __APPLE__
#define exp10f __exp10f
#define exp10 __exp10
#endif

#if defined(_WIN32)
#define RESTRICT __restrict
#else
#define RESTRICT __restrict__
#endif

template <class T>
const T& min(const T& a, const T& b)
{
    return (b < a) ? b : a;
}

template <class T>
const T& max(const T& a, const T& b)
{
    return (b < a) ? a : b;
}

class UI {
   public:
    virtual ~UI() {}
    virtual void openTabBox(const char* label)                                         = 0;
    virtual void openHorizontalBox(const char* label)                                  = 0;
    virtual void openVerticalBox(const char* label)                                    = 0;
    virtual void closeBox()                                                            = 0;
    virtual void addButton(const char* label, FAUSTFLOAT* zone)                        = 0;
    virtual void addCheckButton(const char* label, FAUSTFLOAT* zone)                   = 0;
    virtual void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                   FAUSTFLOAT max, FAUSTFLOAT step, FAUSTFLOAT init)   = 0;
    virtual void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                     FAUSTFLOAT max, FAUSTFLOAT step, FAUSTFLOAT init) = 0;
    virtual void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                             FAUSTFLOAT step, FAUSTFLOAT init)                         = 0;
    virtual void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                       FAUSTFLOAT max)                                 = 0;
    virtual void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                     FAUSTFLOAT max)                                   = 0;
    virtual void addText(const char* text)                                             = 0;
    virtual void declare(float* zone, const char* key, const char* value)              = 0;
    virtual void declare(const char* key, const char* value)                           = 0;
};

class Meta {
   public:
    virtual ~Meta() {}
    virtual void declare(const char* key, const char* value) = 0;
};

class dsp {
   private:
   public:
    virtual ~dsp() {}
    virtual void buildUserInterface(UI* ui_interface)                          = 0;
    virtual void compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs) = 0;
    virtual void init(int samplingFreq)                                        = 0;
    virtual void instanceClear()                                               = 0;
    virtual void instanceConstants(int samplingFreq)                           = 0;
    virtual void instanceInit(int samplingFreq)                                = 0;
    virtual void instanceResetUserInterface()                                  = 0;
    virtual int  getNumInputs()                                                = 0;
    virtual int  getNumOutputs()                                               = 0;
    virtual int  getSampleRate()                                               = 0;
    virtual dsp* clone()                                                       = 0;
};

#ifndef FAUSTFLOAT
#define FAUSTFLOAT float
#endif

#include <algorithm>
#include <cmath>
#include <cstdint>

#ifndef FAUSTCLASS
#define FAUSTCLASS mydsp
#endif

#ifdef __APPLE__
#define exp10f __exp10f
#define exp10 __exp10
#endif

#if defined(_WIN32)
#define RESTRICT __restrict
#else
#define RESTRICT __restrict__
#endif

<< includeIntrinsic >>

<< includeclass >>

static void check_pfm_return_code(int code)
{
    if (code != PFM_SUCCESS) {
        printf("ERROR: %s\n", pfm_strerror(code));
        pfm_terminate();
        exit(code);
    }
}

static long perf_event_open(struct perf_event_attr* hw_event, int group_fd)
{
    return syscall(SYS_perf_event_open, hw_event, 0, -1, group_fd, 0);
}

static struct perf_event_attr perf_event_generic(__u32 type, __u64 config)
{
    return {
        .type           = type,
        .size           = sizeof(struct perf_event_attr),
        .config         = config,
        .disabled       = 1,
        .exclude_kernel = 1,
        .exclude_hv     = 1,
    };
}

static struct perf_event_attr perf_event_native(const char* str)
{
    int                    ret;
    struct perf_event_attr attr = {};
    pfm_perf_encode_arg_t  arg  = {.attr = &attr, .size = sizeof(pfm_perf_encode_arg_t)};

    ret = pfm_get_os_event_encoding(str, PFM_PLM3, PFM_OS_PERF_EVENT_EXT, &arg);
    check_pfm_return_code(ret);

    attr.disabled       = 1;
    attr.exclude_kernel = 1;
    attr.exclude_hv     = 1;

    return attr;
}

static long perf_event_open_generic(__u32 type, __u64 config, long group_fd)
{
    struct perf_event_attr pe = perf_event_generic(type, config);
    return perf_event_open(&pe, group_fd);
}

static long perf_event_open_native(const char* str, long group_fd)
{
    struct perf_event_attr pe = perf_event_native(str);
    return perf_event_open(&pe, group_fd);
}

struct event_stat {
    long long avg;
    long long stddev;
    long long min;
    long long max;
};

static struct event_stat statistics(long long array[], int count)
{
    struct event_stat s;

    s.min = array[0];
    s.max = array[0];

    long long total = 0;
    for (int i = 0; i < count; i++) {
        total += array[i];

        if (s.min > array[i]) {
            s.min = array[i];
        }
        if (s.max < array[i]) {
            s.max = array[i];
        }
    }
    s.avg = total / (double)count;

    double deviation = 0;
    for (int i = 0; i < count; i++) {
        deviation += pow(array[i] - s.avg, 2);
    }
    s.stddev = sqrt(deviation / count);

    return s;
}

static std::string hr_nanoseconds(int n)
{
    if (n / 1000 == 0) {
        return std::format("{}", n);
    } else if (n / 1e6 < 1) {
        return std::format("{:6.02f}μs", n / 1e3);
    } else if (n / 1e9 < 1) {
        return std::format("{:6.02f}ms", n / 1e6);
    } else {
        return std::format("{:7.02f}s", n / 1e9);
    }
}

static std::string hr(int n)
{
    if (n / 1000 == 0) {
        return std::format("{:8d}", n);
    } else if (n / 1e6 < 1) {
        return std::format("{:7.02f}K", n / 1e3);
    } else if (n / 1e9 < 1) {
        return std::format("{:7.02f}M", n / 1e6);
    } else {
        return std::format("{:7.02f}G", n / 1e9);
    }
}

static void print_statistics(std::ostream& output, long long array[], int count, const char* name,
                             std::function<std::string(int)> fmt = hr)
{
    struct event_stat stat = statistics(array, count);
    output << "\033[0m" << std::format("{: >16}: ", name) << "\033[0m"
           << "\033[93maverage: " << fmt(stat.avg) << ", "
           << "\033[94mstd. dev.: " << std::format("{:6.02f}%", stat.stddev * 100.0 / stat.avg)
           << ", "
           << "\033[92mmin: " << fmt(stat.min) << ", "
           << "\033[91mmax: " << fmt(stat.max) << "\033[0m\n";
}

static void print_raw(std::ostream& output, long long* durations, long long* counts,
                      const char** names)
{
    // headers
    output << "time(ns);";
    for (int c = 0; c < NBCOUNTERS; c++) {
        output << names[c] << ";";
    }
    output << std::endl;

    // counts
    for (int i = 0; i < NBITERATIONS; i++) {
        output << durations[i] << ";";
        for (int c = 0; c < NBCOUNTERS; c++) {
            output << counts[c * NBITERATIONS + i] << ";";
        }
        output << std::endl;
    }
}

int main(int argc, char* argv[])
{
    bool raw = false;
    int  opt;

    while ((opt = getopt(argc, argv, "r")) != -1) {
        switch (opt) {
            case 'r':
                raw = true;
                break;
            default:
                std::cerr << "Usage: " << argv[0] << " [-d]" << std::endl;
        }
    }

    mydsp* d = new mydsp();

    if (d == nullptr) {
        std::cerr << "Failed to create DSP object\n";
        return 1;
    }
    d->init(44100);

    // Create the input buffers
    FAUSTFLOAT* inputs[256];
    for (int i = 0; i < d->getNumInputs(); i++) {
        inputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            inputs[i][j] = 0.0;
        }
        inputs[i][0] = 1.0;
    }

    // Create the output buffers
    FAUSTFLOAT* outputs[256];
    for (int i = 0; i < d->getNumOutputs(); i++) {
        outputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            outputs[i][j] = 0.0;
        }
    }

    check_pfm_return_code(pfm_initialize());

    // benchmark
    auto start = std::chrono::high_resolution_clock::now();
    auto end   = std::chrono::high_resolution_clock::now();

    long leader = perf_event_open_generic(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, -1);

    long counters[NBCOUNTERS] = {
        leader,
        perf_event_open_generic(PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS, leader),
        perf_event_open_native("CYCLE_ACTIVITY:STALLS_TOTAL", leader),
        perf_event_open_native("CYCLE_ACTIVITY:STALLS_MEM_ANY", leader),
    };
    const char* names[NBCOUNTERS] = {
        "cycles",
        "instructions",
        "stalls_total",
        "stalls_mem_any",
    };

    long long* durations = new long long[NBITERATIONS];
    long long* counts    = new long long[NBITERATIONS * NBCOUNTERS];

    // warmup
    for (int i = 0; i < 100; i++) {
        d->compute(NBSAMPLES, inputs, outputs);
    }

    for (int i = 0; i < NBITERATIONS; i++) {
        for (int c = 0; c < NBCOUNTERS; c++) {
            ioctl(counters[c], PERF_EVENT_IOC_RESET, 0);
        }

        start = std::chrono::high_resolution_clock::now();

        for (int c = 0; c < NBCOUNTERS; c++) {
            ioctl(counters[c], PERF_EVENT_IOC_ENABLE, 0);
        }

        d->compute(NBSAMPLES, inputs, outputs);

        for (int c = 0; c < NBCOUNTERS; c++) {
            ioctl(counters[c], PERF_EVENT_IOC_DISABLE, 0);
        }

        end                               = std::chrono::high_resolution_clock::now();
        std::chrono::nanoseconds duration = end - start;
        durations[i]                      = duration.count();

        for (int c = 0; c < NBCOUNTERS; c++) {
            read(counters[c], &counts[c * NBITERATIONS + i], sizeof(long long));
        }
    }

    delete d;

    if (raw) {
        print_raw(std::cout, durations, counts, names);
    } else {
        std::cout << "\033[1;4m" << argv[0] << "\033[0m\n";
        print_statistics(std::cout, durations, NBITERATIONS, "time(ns)", hr_nanoseconds);
        for (int c = 0; c < NBCOUNTERS; c++) {
            print_statistics(std::cout, counts + c * NBITERATIONS, NBITERATIONS, names[c]);
        }
        std::cout << "\n";
    }

    delete[] durations;
    delete[] counts;

    return 0;
}
