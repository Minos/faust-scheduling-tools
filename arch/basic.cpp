#include <faust/audio/alsa-dsp.h>

#include "basic.h"

#define CYCLE_SIZE 64

basic_dsp_runner::basic_dsp_runner(int sample_rate, int buffer_size)
    : sample_rate(sample_rate), buffer_size(buffer_size)
{
}

void basic_dsp_runner::run(self_measuring_dsp& d)
{
    int nloops = d.get_total_iterations();

    d.init(44100);

    srand(0);

    // Create the input and output buffers
    FAUSTFLOAT*** inputs  = new FAUSTFLOAT**[CYCLE_SIZE];
    FAUSTFLOAT*** outputs = new FAUSTFLOAT**[CYCLE_SIZE];

    for (int i = 0; i < CYCLE_SIZE; i++) {
        inputs[i] = new FAUSTFLOAT*[d.getNumInputs()];
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            inputs[i][ch] = new FAUSTFLOAT[buffer_size];
        }

        outputs[i] = new FAUSTFLOAT*[d.getNumOutputs()];
        for (int ch = 0; ch < d.getNumOutputs(); ch++) {
            outputs[i][ch] = new FAUSTFLOAT[buffer_size];
        }
    }

    while (!d.end_reached()) {
        int it = d.get_current_iteration();

        FAUSTFLOAT** input  = inputs[it % CYCLE_SIZE];
        FAUSTFLOAT** output = outputs[it % CYCLE_SIZE];
        // Fill the input buffers with white noise
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            for (int s = 0; s < buffer_size; s++) {
                input[ch][s] = -1 + 2 * (rand() / (float)RAND_MAX);
            }
        }

        d.compute(buffer_size, input, output);
    }

    for (int i = 0; i < CYCLE_SIZE; i++) {
        for (int ch = 0; ch < d.getNumInputs(); ch++) {
            delete[] inputs[i][ch];
        }
        for (int ch = 0; ch < d.getNumOutputs(); ch++) {
            delete[] outputs[i][ch];
        }
        delete[] inputs[i];
        delete[] outputs[i];
    }
    delete[] inputs;
    delete[] outputs;
}
