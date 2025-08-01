#include <iostream>

#include "load.h"
#include "ui.h"

#define NBSAMPLES 44100
#define IMPULSE_SIZE 441

static void print_usage(int argc, char* argv[])
{
    std::cerr << "Usage: " << argv[0] << " program.so" << std::endl;
}

int main(int argc, char* argv[])
{
    int nprograms = argc - 1;
    if (nprograms != 1) {
        print_usage(argc, argv);
        exit(1);
    }

    foreign_dsp d(argv[1]);

    d.init(44100);

    UI ui;
    d.buildUserInterface(&ui);

    srand(0xABCD);

    // Create the input buffers
    float* inputs[256];
    for (int i = 0; i < d.getNumInputs(); i++) {
        inputs[i] = new float[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            inputs[i][j] = -1 + 2 * (rand() / (float)RAND_MAX);
        }
    }

    // Create the output buffers
    float* outputs[256];
    for (int i = 0; i < d.getNumOutputs(); i++) {
        outputs[i] = new float[NBSAMPLES];
    }

    // Compile the Impulse Response
    d.compute(NBSAMPLES, inputs, outputs);

    // Print the NBSAMPLES of the impulse response
    for (int i = 0; i < NBSAMPLES; i++) {
        std::cout << outputs[0][i];
        for (int j = 1; j < d.getNumOutputs(); j++) {
            std::cout << ";" << outputs[j][i];
        }
        std::cout << std::endl;
    }

    for (int i = 0; i < d.getNumOutputs(); i++) {
        delete[] outputs[i];
    }

    for (int i = 0; i < d.getNumInputs(); i++) {
        delete[] inputs[i];
    }

    return 0;
}
