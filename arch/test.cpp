#include <iostream>

#include "mydsp.h"

#define NBSAMPLES 44100
#define IMPULSE_SIZE 441

int main(int argc, char* argv[])
{
    dsp* d = create_dsp();

    if (d == nullptr) {
        std::cerr << "Failed to create DSP object\n";
        return 1;
    }
    d->init(44100);

    UI ui;
    d->buildUserInterface(&ui);

    srand(0xABCD);

    // Create the input buffers
    FAUSTFLOAT* inputs[256];
    for (int i = 0; i < d->getNumInputs(); i++) {
        inputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            inputs[i][j] = -1 + 2 * (rand() / (float) RAND_MAX);
        }
    }

    // Create the output buffers
    FAUSTFLOAT* outputs[256];
    for (int i = 0; i < d->getNumOutputs(); i++) {
        outputs[i] = new FAUSTFLOAT[NBSAMPLES];
    }

    // Compile the Impulse Response
    d->compute(NBSAMPLES, inputs, outputs);

    // Print the NBSAMPLES of the impulse response
    for (int i = 0; i < NBSAMPLES; i++) {
        std::cout << outputs[0][i];
        for (int j = 1; j < d->getNumOutputs(); j++) {
            std::cout << ";" << outputs[j][i];
        }
        std::cout << std::endl;
    }

    return 0;
}
