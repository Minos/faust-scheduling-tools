#ifndef __FCSCHEDTOOL_ALSA_H__
#define __FCSCHEDTOOL_ALSA_H__

#include "dsp_measuring.h"

class alsa_dsp_runner : public dsp_runner {
    int sample_rate;
    int buffer_size;

   public:
    alsa_dsp_runner(int sample_rate, int buffer_size);

    virtual void run(self_measuring_dsp& d) override;
};

#endif
