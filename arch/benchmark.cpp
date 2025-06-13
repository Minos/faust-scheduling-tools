#include <fstream>
#include <iostream>

#include <unistd.h>

#include "dsp_measuring.h"
#include "mydsp.h"
#include "pfm_utils.h"

#define NBSAMPLES 512
#define NBITERATIONS 1000

static void print_usage(int argc, char* argv[])
{
    std::cerr << "Usage: " << argv[0]
              << " [-o output] [-e events] [-n number_of_loops] [-b buffer_size]" << std::endl;
}

int main(int argc, char* argv[])
{
    int                        opt;
    bool                       raw      = false;
    int                        nsamples = NBSAMPLES;
    int                        nloops   = NBITERATIONS;
    std::optional<std::string> output_path;
    std::vector<std::string>   events;

    while ((opt = getopt(argc, argv, "ro:e:n:b:")) != -1) {
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
            case 'b':
                nsamples = atoi(optarg);
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

    d.init(44100);

    srand(0);

    // Create the input and output buffers
    FAUSTFLOAT*** inputs  = new FAUSTFLOAT**[nloops];
    FAUSTFLOAT*** outputs = new FAUSTFLOAT**[nloops];

    for (int it = 0; it < nloops; it++) {
        inputs[it] = new FAUSTFLOAT*[d.getNumInputs()];
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            inputs[it][ch] = new FAUSTFLOAT[nsamples];
        }

        outputs[it] = new FAUSTFLOAT*[d.getNumOutputs()];
        for (int ch = 0; ch < d.getNumOutputs(); ch++) {
            outputs[it][ch] = new FAUSTFLOAT[nsamples];
        }
    }

    d.observe_events(events);

    while (!d.start_reached()) {
        d.compute(nsamples, inputs[0], outputs[0]);
    }

    while (!d.end_reached()) {
        int it = d.get_current_iteration();

        FAUSTFLOAT** input  = inputs[it];
        FAUSTFLOAT** output = outputs[it];
        // Fill the input buffers with white noise
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            for (int s = 0; s < nsamples; s++) {
                input[ch][s] = -1 + 2 * (rand() / (float)RAND_MAX);
            }
        }

        d.compute(nsamples, input, output);
    }

    pfm_utils_terminate();

    for (int it = 0; it < nloops; it++) {
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            delete[] inputs[it][ch];
        }
        for (int ch = 0; ch < d.getNumOutputs(); ch++) {
            delete[] outputs[it][ch];
        }
        delete[] inputs[it];
        delete[] outputs[it];
    }
    delete[] inputs;
    delete[] outputs;

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
