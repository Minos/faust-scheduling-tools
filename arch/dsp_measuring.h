#ifndef __DSP_MEASURING_H__
#define __DSP_MEASURING_H__

#include <array>
#include <condition_variable>
#include <mutex>

#include <faust/dsp/dsp.h>

/*
 * PFM units are in limited number. If we're measuring more than MAX_COUNTERS events, we will group
 * them by this number and run more loops to get the requested number of measures.
 */
#define MAX_COUNTERS 4

class self_measuring_dsp : public decorator_dsp {
    int nb_iterations;
    int current_iteration = 0;

    std::vector<std::string> events;

    std::vector<std::array<float, MAX_COUNTERS>> perf_groups;

    bool events_opened = false;
    int  current_group = 0;

    // FIXME: Use a fixed-length array to control allocations
    std::vector<long long>              durations;
    std::vector<std::vector<long long>> perf_measures;

    std::mutex              end_mutex;
    std::condition_variable end_cv;

    void* handle = nullptr;

   public:
    explicit self_measuring_dsp(dsp* dsp, int nb_iterations = 1000);
    explicit self_measuring_dsp(const std::string& path, int nb_iterations = 1000);
    ~self_measuring_dsp() override;

    void compute(int count, float** inputs, float** outputs) override;

    void observe_event(const std::string& event_name);
    void observe_events(const std::vector<std::string>& event_names);

    // Run the DSP for a few hundred loops to ignore initialization effects
    void warmup(int buffer_size, int nb_iterations = 200);

    // Returns true if the measuring vectors have been filled
    bool end_reached() const;

    int get_current_iteration() const;
    int get_total_iterations() const;

    void wait();

    void print_measures_pretty(std::ostream& output) const;
    void print_measures_raw(std::ostream& output) const;

   private:
    void open_events();
};

class dsp_runner {
   public:
    virtual ~dsp_runner() = default;

    virtual void run(self_measuring_dsp& dsp) = 0;
};

#endif
