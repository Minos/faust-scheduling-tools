#include <fstream>
#include <iostream>
#include <optional>

#include <getopt.h>

#include "alsa.h"
#include "basic.h"
#include "dsp_measuring.h"
#include "mydsp.h"
#include "pfm_utils.h"

#define SAMPLE_RATE 44100
#define NBSAMPLES 256
#define NBITERATIONS 1000

enum run_type {
    BASIC,
    ALSA,
};

static void print_usage(int argc, char* argv[])
{
    std::cerr << "Usage: " << argv[0]
              << " [-o output] [-e events] [-n number_of_loops] [-b buffer_size]"
              << " program1.so [program2.so ...]" << std::endl;
}

int main(int argc, char* argv[])
{
    int         opt;
    int         option_index;
    const char* optname;

    bool raw         = false;
    int  buffer_size = NBSAMPLES;
    int  nloops      = NBITERATIONS;

    std::optional<std::string> output_path;
    std::vector<std::string>   events;

    run_type                    rtype  = BASIC;
    std::unique_ptr<dsp_runner> runner = nullptr;

    static struct option long_options[] = {
        {"alsa", no_argument, 0, 0},
        {"basic", no_argument, 0, 0},
    };

    while ((opt = getopt_long(argc, argv, "ro:e:n:b:", long_options, &option_index)) != -1) {
        switch (opt) {
            case 0:
                optname = long_options[option_index].name;
                if (!strcmp(optname, "alsa")) {
                    rtype = ALSA;
                } else if (!strcmp(optname, "basic")) {
                    rtype = BASIC;
                }
                break;
            case 'r':
                raw = true;
                break;
            case 'o':
                output_path.emplace(optarg);
                break;
            case 'e':
                pfm_utils_parse_events(optarg, events);
                break;
            case 'n':
                nloops = atoi(optarg);
                break;
            case 'b':
                buffer_size = atoi(optarg);
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

    if (output_path.has_value()) {
        raw = true;
    }

    switch (rtype) {
        case BASIC:
            runner = std::make_unique<basic_dsp_runner>(SAMPLE_RATE, buffer_size);
            break;
        case ALSA:
            runner = std::make_unique<alsa_dsp_runner>(SAMPLE_RATE, buffer_size);
            break;
    }

    int nprograms = argc - optind;
    if (nprograms <= 0) {
        print_usage(argc, argv);
        return 1;
    }

    std::vector<std::string> dsp_paths(nprograms);
    for (int i = 0; i < nprograms; i++) {
        dsp_paths[i] = argv[optind + i];
    }

    pfm_utils_initialize();

    for (const std::string& path : dsp_paths) {
        self_measuring_dsp d(path, nloops);

        UI ui;
        d.buildUserInterface(&ui);
        d.observe_events(events);

        runner->run(d);

        if (raw) {
            if (output_path.has_value()) {
                std::ofstream output(output_path.value());
                d.print_measures_raw(output);
            } else {
                d.print_measures_raw(std::cout);
            }
        } else {
            std::cerr << "\033[1;4m" << path << "\033[0m\n";
            d.print_measures_pretty(std::cerr);
            std::cerr << "\n";
        }
    }

    pfm_utils_terminate();

    return 0;
}
