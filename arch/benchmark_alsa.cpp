#include <fstream>
#include <iostream>
#include <optional>

#include <faust/audio/alsa-dsp.h>

#include "mydsp.h"
#include "pfm_utils.h"
#include "dsp_measuring.h"

#define NBITERATIONS 1000

static void print_usage(int argc, char* argv[])
{
    std::cerr << "Usage: " << argv[0] << " [-o output] [-e events] [-n number_of_loops]"
              << std::endl;
}

int main(int argc, char* argv[])
{
    int                        opt;
    bool                       raw    = false;
    int                        nloops = NBITERATIONS;
    std::optional<std::string> output_path;
    std::vector<std::string>   events;

    while ((opt = getopt(argc, argv, "ro:e:n:")) != -1) {
        switch (opt) {
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

    pfm_utils_initialize();

    self_measuring_dsp d(create_dsp(), nloops);

    UI ui;
    d.buildUserInterface(&ui);

    alsaaudio audio(argc, argv, &d);
    if (!audio.init(argv[0], &d)) {
        std::cerr << "Unable to init audio" << std::endl;
        exit(1);
    }

    d.observe_events(events);

    if (!audio.start()) {
        std::cerr << "Unable to start audio" << std::endl;
    }

    d.wait();

    audio.stop();

    pfm_utils_terminate();

    if (raw) {
        if (output_path.has_value()) {
            std::ofstream output(output_path.value());
            d.print_measures_raw(output);
        } else {
            d.print_measures_raw(std::cout);
        }
    } else {
        std::cout << "\033[1;4m" << argv[0] << "\033[0m\n";
        d.print_measures_pretty(std::cout);
        std::cout << "\n";
    }

    return 0;
}
