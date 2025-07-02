#ifndef __FCSCHEDTOOL_BASIC_H__
#define __FCSCHEDTOOL_BASIC_H__

#include "dsp_measuring.h"

class basic_dsp_runner : public dsp_runner {
   public:
    const int sample_rate;
    const int buffer_size;

    basic_dsp_runner(int sample_rate, int buffer_size);
    virtual ~basic_dsp_runner() = default;

    virtual void run(self_measuring_dsp& d) override;
};

#endif
