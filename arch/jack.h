#ifndef __FCSCHEDTOOL_JACK_H__
#define __FCSCHEDTOOL_JACK_H__

#include "dsp_measuring.h"

class jack_dsp_runner : public dsp_runner {
   public:
    jack_dsp_runner();

    virtual void run(self_measuring_dsp& d) override;
};

#endif
