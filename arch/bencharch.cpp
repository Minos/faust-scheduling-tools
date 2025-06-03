#include <perfmon/perf_event.h>
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
#include <fstream>
#include <functional>
#include <iostream>

#define NBSAMPLES 44100
#define NBITERATIONS 1000

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

static void print_usage(int argc, char *argv[]) {
    std::cerr << "Usage: " << argv[0] 
              << " [-o output] [-e events] [-n number_of_loops]" 
              << std::endl;
}

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
    void openTabBox(const char* label) {}
    void openHorizontalBox(const char* label) {}
    void openVerticalBox(const char* label) {}
    void closeBox() {}
    void addCheckButton(const char* label, FAUSTFLOAT* zone) {}
    void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                           FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                             FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                     FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max)
    {
    }
    void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max) {}
    void addText(const char* text) {}
    void declare(float* zone, const char* key, const char* value) {}
    void declare(const char* key, const char* value) {}

    void addButton(const char* label, FAUSTFLOAT* zone)
    {
        static const char* patterns[] = {"play", "gate", "hit", NULL};
        for (int i = 0; patterns[i] != NULL; i++) {
            if (strcasestr(label, patterns[i])) {
                *zone = 1;
            }
        }
    }
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
;

static void check_pfm_return_code(int code)
{
    if (code != PFM_SUCCESS) {
        std::cerr << "Error: " << pfm_strerror(code) << std::endl;
        pfm_terminate();
        exit(code);
    }
}

static int perf_event_open(perf_event_attr* hw_event, int group_fd)
{
    return syscall(SYS_perf_event_open, hw_event, 0, -1, group_fd, 0);
}

static int perf_event_open_named(const char* str, int group_fd)
{
    int                   ret;
    perf_event_attr       attr = {.size = sizeof(perf_event_attr)};
    pfm_perf_encode_arg_t arg  = {.attr = &attr, .size = sizeof(pfm_perf_encode_arg_t)};

    ret = pfm_get_os_event_encoding(str, PFM_PLM3, PFM_OS_PERF_EVENT_EXT, &arg);
    if (ret != PFM_SUCCESS) {
        std::cerr << "Error opening event " << str << ": " << pfm_strerror(ret) << std::endl;
        pfm_terminate();
        exit(ret);
    }

    attr.disabled       = 1;
    attr.exclude_kernel = 1;
    attr.exclude_hv     = 1;

    return perf_event_open(&attr, group_fd);
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

static void print_statistics(std::ostream& output, long long array[], int nloops, const char* name,
                             std::function<std::string(int)> fmt = hr)
{
    struct event_stat stat = statistics(array, nloops);
    output << "\033[0m" << std::format("{:<32} ", name) << "\033[0m"
           << "\033[93maverage: " << fmt(stat.avg) << ", "
           << "\033[94mstd. dev.: " << std::format("{:6.02f}%", stat.stddev * 100.0 / stat.avg)
           << ", "
           << "\033[92mmin: " << fmt(stat.min) << ", "
           << "\033[91mmax: " << fmt(stat.max) << "\033[0m\n";
}

static void print_raw(std::ostream& output, long long* durations, long long* counts,
                      unsigned int nloops, const std::vector<std::string>& names)
{
    // headers
    output << "time(ns);";
    for (const std::string& name : names) {
        output << name << ";";
    }
    output << std::endl;

    // counts
    for (int i = 0; i < nloops; i++) {
        output << durations[i] << ";";
        for (int c = 0; c < names.size(); c++) {
            output << counts[c * nloops + i] << ";";
        }
        output << std::endl;
    }
}

static void parse_events(const char *arg, std::vector<std::string>& events)
{
    const char* event = arg;
    const char* end;
    size_t      size;

    while ((end = strchr(event, ',')) != NULL) {
        size = end - event;
        events.emplace_back(event, size);
        event = end + 1;
    }

    events.emplace_back(event);
}

int main(int argc, char* argv[])
{
    int                      opt;
    bool                     raw    = false;
    int                      nloops = NBITERATIONS;
    std::unique_ptr<char>    output;
    std::vector<std::string> events;

    while ((opt = getopt(argc, argv, "ro:e:n:")) != -1) {
        switch (opt) {
            case 'r':
                raw = true;
                break;
            case 'o':
                output.reset(strdup(optarg));
                break;
            case 'e':
                parse_events(optarg, events);
                break;
            case 'n':
                nloops = atoi(optarg);
                break;
            default:
                print_usage(argc, argv);
                return 1;
        }
    }

    if (nloops == 0) {
        print_usage(argc, argv);
        return 1;
    }

    if (output) {
        raw = true;
    }

    mydsp* d = new mydsp();

    if (d == nullptr) {
        std::cerr << "Failed to create DSP object\n";
        return 1;
    }

    UI ui;
    d->buildUserInterface(&ui);

    d->init(44100);

    srand(0);

    // Create the input buffers
    FAUSTFLOAT* inputs[256];
    for (int i = 0; i < d->getNumInputs(); i++) {
        inputs[i] = new FAUSTFLOAT[NBSAMPLES];
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

    std::vector<int> counters(events.size(), -1);

    for (int i = 0; i < events.size(); i++) {
        counters[i] = perf_event_open_named(events[i].c_str(), counters[0]);
    }

    long long* durations = new long long[nloops];
    long long* counts    = new long long[nloops * events.size()];

    // warmup
    for (int i = 0; i < 100; i++) {
        d->compute(NBSAMPLES, inputs, outputs);
    }

    for (int i = 0; i < nloops; i++) {
        // Fill the input buffers with white noise
        for (int i = 0; i < d->getNumInputs(); i++) {
            for (int j = 0; j < NBSAMPLES; j++) {
                inputs[i][j] = -1 + 2 * (rand() / (float) RAND_MAX);
            }
        }

        for (int c : counters) {
            ioctl(c, PERF_EVENT_IOC_RESET, 0);
        }

        start = std::chrono::high_resolution_clock::now();

        for (int c : counters) {
            ioctl(c, PERF_EVENT_IOC_ENABLE, 0);
        }

        d->compute(NBSAMPLES, inputs, outputs);

        for (int c : counters) {
            ioctl(c, PERF_EVENT_IOC_DISABLE, 0);
        }

        end                               = std::chrono::high_resolution_clock::now();
        std::chrono::nanoseconds duration = end - start;
        durations[i]                      = duration.count();

        for (int k = 0; k < counters.size(); k++) {
            read(counters[k], &counts[k * nloops + i], sizeof(long long));
        }
    }

    pfm_terminate();

    for (int i = 0; i < d->getNumInputs(); i++) {
        delete[] inputs[i];
    }

    for (int i = 0; i < d->getNumOutputs(); i++) {
        delete[] outputs[i];
    }

    delete d;

    if (raw) {
        std::ofstream output_file;
        std::ostream *out;
        if (output) {
            output_file.open(output.get());
            out = &output_file;
        } else {
            out = &std::cout;
        }
        print_raw(*out, durations, counts, nloops, events);
    } else {
        std::cout << "\033[1;4m" << argv[0] << "\033[0m\n";
        print_statistics(std::cout, durations, nloops, "time(ns)", hr_nanoseconds);
        for (int c = 0; c < events.size(); c++) {
            print_statistics(std::cout, counts + c * nloops, nloops, events[c].c_str());
        }
        std::cout << "\n";
    }

    delete[] durations;
    delete[] counts;

    return 0;
}
