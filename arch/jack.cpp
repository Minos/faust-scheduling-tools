#include <iostream>

#include "jack.h"

jack_dsp_runner::jack_dsp_runner() = default;

void jack_dsp_runner::run(self_measuring_dsp& d)
{
    jackaudio audio;

    if (!audio.init("mydsp", &d)) {
        std::cerr << "Unable to init audio" << std::endl;
        exit(1);
    }
    
    if (!audio.start()) {
        std::cerr << "Unable to start audio" << std::endl;
        exit(1);
    }

    d.wait();

    audio.stop();
}
