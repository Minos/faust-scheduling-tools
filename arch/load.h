#ifndef __FCSCHEDTOOL_LOAD_H__
#define __FCSCHEDTOOL_LOAD_H__

#include <faust/dsp/dsp.h>

class foreign_dsp : public decorator_dsp {
    void* handle;

   public:
    explicit foreign_dsp(const std::string& path);
    ~foreign_dsp();
};

dsp* load_shared_dsp(const std::string& path, void** handle);

void unload_shared_dsp(dsp* dsp, void* handle);

#endif
