#ifndef __FCSCHEDTOOL_LOAD_H__
#define __FCSCHEDTOOL_LOAD_H__

#include <faust/dsp/dsp.h>

dsp* load_shared_dsp(const std::string& path, void** handle);

void unload_shared_dsp(dsp* dsp, void* handle);

#endif

