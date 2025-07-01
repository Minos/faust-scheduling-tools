#include <iostream>

#include "alsa.h"

alsa_dsp_runner::alsa_dsp_runner(int sample_rate, int buffer_size)
    : dsp_runner(), audio(sample_rate, buffer_size)
{
}

void alsa_dsp_runner::run(self_measuring_dsp& d)
{
    if (!audio.init("mydsp", &d)) {
        std::cerr << "Unable to init audio" << std::endl;
        exit(1);
    }

    if (!audio.start()) {
        std::cerr << "Unable to start audio" << std::endl;
    }

    d.wait();

    audio.stop();
}
