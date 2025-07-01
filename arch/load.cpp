#include <iostream>

#include <dlfcn.h>

#include "load.h"

dsp* load_shared_dsp(const std::string& path, void** handle)
{
    *handle = dlopen(path.c_str(), RTLD_LAZY);
    if (*handle == nullptr) {
        std::cerr << dlerror() << std::endl;
        exit(1);
    }

    dsp* (*create_dsp)() = (dsp* (*)()) dlsym(*handle, "create_dsp");
    if (create_dsp == nullptr) {
        std::cerr << dlerror() << std::endl;
        *handle = nullptr;
        exit(1);
    }

    return create_dsp();
}

void unload_shared_dsp(dsp* dsp, void* handle)
{
    delete dsp;
    dlclose(handle);
}
