#include <iostream>

#include <faust/misc.h>
#include <faust/audio/alsa-dsp.h>

#include "alsa.h"

alsa_dsp_runner::alsa_dsp_runner(int sample_rate, int buffer_size)
    : sample_rate(sample_rate), buffer_size(buffer_size)
{
}

void alsa_dsp_runner::run(self_measuring_dsp& d)
{
    alsaaudio audio(sample_rate, buffer_size);

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
