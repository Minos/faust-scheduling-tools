#include <chrono>
#include <cmath>
#include <cstring>
#include <functional>
#include <iostream>

#include <string.h>

#include <perfmon/pfmlib_perf_event.h>

#include "load.h"
#include "pfm_utils.h"

#include "dsp_measuring.h"

struct event_stat {
    long long avg;
    long long stddev;
    long long min;
    long long max;
};

struct event_stat event_statistics(const std::vector<long long>& array)
{
    struct event_stat s;

    s.min = array[0];
    s.max = array[0];

    long long total = 0;
    for (long long sample : array) {
        total += sample;

        if (s.min > sample) {
            s.min = sample;
        }
        if (s.max < sample) {
            s.max = sample;
        }
    }
    s.avg = (double)total / array.size();

    double deviation = 0;
    for (long long sample : array) {
        deviation += pow(sample - s.avg, 2);
    }
    s.stddev = sqrt(deviation / array.size());

    return s;
}

std::string format_hr_nanoseconds(int n)
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

std::string format_hr(int n)
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

void print_statistics(std::ostream& output, const std::vector<long long>& array,
                      const std::string& name, std::function<std::string(int)> fmt = format_hr)
{
    struct event_stat stat = event_statistics(array);
    output << "\033[0m" << std::format("{:<32} ", name) << "\033[0m"
           << "\033[93maverage: " << fmt(stat.avg) << ", "
           << "\033[94mstd. dev.: " << std::format("{:6.02f}%", stat.stddev * 100.0 / stat.avg)
           << ", "
           << "\033[92mmin: " << fmt(stat.min) << ", "
           << "\033[91mmax: " << fmt(stat.max) << "\033[0m\n";
}

self_measuring_dsp::self_measuring_dsp(dsp* dsp, int nb_iterations)
    : decorator_dsp(dsp), nb_iterations(nb_iterations), durations(nb_iterations)
{
}

self_measuring_dsp::self_measuring_dsp(const std::string& path, int nb_iterations)
    : nb_iterations(nb_iterations), durations(nb_iterations)
{
    fDSP = load_shared_dsp(path, &handle);
}

self_measuring_dsp::~self_measuring_dsp()
{
    if (handle != nullptr) {
        // If we loaded the DSP from a library, we need to free it before the library is unloaded
        // and set it to nullptr to prevent a double-free from the base class
        unload_shared_dsp(fDSP, handle);
        fDSP = nullptr;
    }
}

void self_measuring_dsp::observe_event(const std::string& event_name)
{
    events.emplace_back(event_name);

    // Pre-allocate measures buffer
    perf_measures.emplace_back(nb_iterations);
}

void self_measuring_dsp::observe_events(const std::vector<std::string>& event_names)
{
    for (auto event_name : event_names) {
        observe_event(event_name);
    }

    int groups_size = std::max((events.size() - 1) / MAX_COUNTERS + 1, (size_t)0);
    perf_groups.assign(groups_size, {-1});
}

void self_measuring_dsp::open_events()
{
    for (int i = 0; i < events.size(); i++) {
        auto& group = perf_groups[i / MAX_COUNTERS];
        int   pos   = i % MAX_COUNTERS;
        int   fd    = pfm_utils_open_named_event(events[i].c_str(), group[0]);
        group[pos]  = fd;
    }

    events_opened = true;
}

void self_measuring_dsp::compute(int count, float** inputs, float** outputs)
{
    // We need to open perf events in the thread that will run them
    if (!events_opened) {
        open_events();
    }

    std::optional<std::array<float, MAX_COUNTERS>> group;
    if (perf_groups.size() > 0) {
        group.emplace(perf_groups[current_group]);
    }

    if (group.has_value()) {
        ioctl((*group)[0], PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP);
        ioctl((*group)[0], PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP);
    }

    auto start = std::chrono::high_resolution_clock::now();
    fDSP->compute(count, inputs, outputs);
    auto end = std::chrono::high_resolution_clock::now();

    if (group.has_value()) {
        ioctl((*group)[0], PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP);
    }

    if (current_iteration >= 0 && current_iteration < nb_iterations) {
        std::chrono::nanoseconds duration = end - start;
        durations[current_iteration]      = duration.count();

        if (group.has_value()) {
            int offset = current_group * MAX_COUNTERS;
            for (int i = 0; i < MAX_COUNTERS; i++) {
                if ((*group)[i] <= 0) {
                    break;
                }
                long long* read_addr = &perf_measures[offset + i][current_iteration];
                read((*group)[i], read_addr, sizeof(long long));
            }
        }
    }

    if (++current_group >= perf_groups.size()) {
        current_group = 0;
        current_iteration++;
    }

    if (current_iteration == nb_iterations) {
        end_cv.notify_all();
    }
}

void self_measuring_dsp::warmup(int buffer_size, int nb_iterations)
{
    float** inputs  = new float*[fDSP->getNumInputs()];
    float** outputs = new float*[fDSP->getNumOutputs()];

    for (int ch = 0; ch < fDSP->getNumInputs(); ch++) {
        inputs[ch] = new float[buffer_size];
        memset(inputs[ch], 0, buffer_size * sizeof(float));
    }

    for (int ch = 0; ch < fDSP->getNumOutputs(); ch++) {
        outputs[ch] = new float[buffer_size];
    }

    for (int i = 0; i < nb_iterations; i++) {
        fDSP->compute(buffer_size, inputs, outputs);
    }

    for (int ch = 0; ch < fDSP->getNumOutputs(); ch++) {
        delete[] outputs[ch];
    }

    for (int ch = 0; ch < fDSP->getNumInputs(); ch++) {
        delete[] inputs[ch];
    }

    delete[] outputs;
    delete[] inputs;
}

bool self_measuring_dsp::end_reached() const
{
    return current_iteration >= nb_iterations;
}

int self_measuring_dsp::get_current_iteration() const
{
    return current_iteration;
}

int self_measuring_dsp::get_total_iterations() const
{
    return nb_iterations;
}

void self_measuring_dsp::wait()
{
    std::unique_lock lock(end_mutex);
    end_cv.wait(lock);
}

void self_measuring_dsp::print_measures_pretty(std::ostream& output) const
{
    print_statistics(output, durations, "time(ns)", format_hr_nanoseconds);
    for (int i = 0; i < events.size(); i++) {
        print_statistics(output, perf_measures[i], events[i]);
    }
}

void self_measuring_dsp::print_measures_raw(std::ostream& output) const
{
    // headers
    output << "time(ns);";
    for (auto event : events) {
        output << event << ";";
    }
    output << std::endl;

    // counts
    for (int i = 0; i < nb_iterations; i++) {
        output << durations[i] << ";";
        for (int e = 0; e < events.size(); e++) {
            output << perf_measures[e][i] << ";";
        }
        output << std::endl;
    }
}
