#include <functional>
#include <map>
#include <optional>

#include <perfmon/pfmlib_perf_event.h>

#include <faust/dsp/dsp.h>

class self_measuring_dsp : public decorator_dsp {
    int nb_iterations;
    int current_iteration = -10;  // Warmup period

    std::vector<std::string> events;
    std::vector<int>         perf_counters;
    int                      main_counter = -1;

    std::vector<long long>              durations;
    std::vector<std::vector<long long>> perf_measures;

   public:
    explicit self_measuring_dsp(dsp* dsp, int nb_iterations = 1000);
    void compute(int count, float** inputs, float** outputs) override;

    void observe_event(const std::string& event_name);
    void observe_events(const std::vector<std::string>& event_names);

    // Returns true if the warmup iterations are over
    bool start_reached() const;

    // Returns true if the measuring vectors have been filled
    bool end_reached() const;

    int get_current_iteration() const;

    void print_measures_pretty(std::ostream& output) const;
    void print_measures_raw(std::ostream& output) const;
};

struct event_stat {
    long long avg;
    long long stddev;
    long long min;
    long long max;
};

struct event_stat event_statistics(const std::vector<long long>& array);

std::string format_hr_nanoseconds(int n);
std::string format_hr(int n);

void print_statistics(std::ostream& output, const std::vector<long long>& array,
                      const std::string& name, std::function<std::string(int)> fmt = format_hr);

int perf_event_open_named(const char* str, int group_fd);
