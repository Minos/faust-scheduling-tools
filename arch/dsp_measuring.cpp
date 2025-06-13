#include <chrono>
#include <cmath>
#include <iostream>
#include <mutex>

#include <perfmon/pfmlib_perf_event.h>

#include "pfm_utils.h"

#include "dsp_measuring.h"

self_measuring_dsp::self_measuring_dsp(dsp* dsp, int nb_iterations)
    : decorator_dsp(dsp), nb_iterations(nb_iterations), durations(nb_iterations)
{
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
}

void self_measuring_dsp::open_events()
{
    for (const auto& event : events) {
        int fd = pfm_utils_open_named_event(event.c_str(), main_counter);
        if (main_counter == -1) {
            main_counter = fd;
        }
        perf_counters.push_back(fd);
    }
}

void self_measuring_dsp::compute(int count, float** inputs, float** outputs)
{
    if (events.size() > 0 && perf_counters.size() == 0) {
        open_events();
    }

    for (auto c : perf_counters) {
        ioctl(c, PERF_EVENT_IOC_RESET, 0);
    }

    auto start = std::chrono::high_resolution_clock::now();
    for (auto c : perf_counters) {
        ioctl(c, PERF_EVENT_IOC_ENABLE, 0);
    }

    fDSP->compute(count, inputs, outputs);

    for (auto c : perf_counters) {
        ioctl(c, PERF_EVENT_IOC_DISABLE, 0);
    }

    auto end = std::chrono::high_resolution_clock::now();

    if (current_iteration >= 0 && current_iteration < nb_iterations) {
        std::chrono::nanoseconds duration = end - start;
        durations[current_iteration]      = duration.count();

        for (int i = 0; i < events.size(); i++) {
            read(perf_counters[i], &perf_measures[i][current_iteration], sizeof(long long));
        }
    }

    current_iteration++;

    if (current_iteration == nb_iterations) {
        end_cv.notify_all();
    }
}

bool self_measuring_dsp::start_reached() const
{
    return current_iteration >= 0;
}

bool self_measuring_dsp::end_reached() const
{
    return current_iteration >= nb_iterations;
}

int self_measuring_dsp::get_current_iteration() const
{
    return current_iteration;
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
                      const std::string& name, std::function<std::string(int)> fmt)
{
    struct event_stat stat = event_statistics(array);
    output << "\033[0m" << std::format("{:<32} ", name) << "\033[0m"
           << "\033[93maverage: " << fmt(stat.avg) << ", "
           << "\033[94mstd. dev.: " << std::format("{:6.02f}%", stat.stddev * 100.0 / stat.avg)
           << ", "
           << "\033[92mmin: " << fmt(stat.min) << ", "
           << "\033[91mmax: " << fmt(stat.max) << "\033[0m\n";
}
