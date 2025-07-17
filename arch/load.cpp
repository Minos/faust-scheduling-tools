#include <iostream>

#include <dlfcn.h>

#include "load.h"

foreign_dsp::foreign_dsp(const std::string& path) : decorator_dsp(nullptr)
{
    handle = dlopen(path.c_str(), RTLD_LAZY);
    if (handle == nullptr) {
        std::cerr << dlerror() << std::endl;
        exit(1);
    }

    dsp* (*create_dsp)() = (dsp* (*)()) dlsym(handle, "create_dsp");
    if (create_dsp == nullptr) {
        std::cerr << dlerror() << std::endl;
        handle = nullptr;
        exit(1);
    }

    fDSP = create_dsp();
}

foreign_dsp::~foreign_dsp()
{
    delete fDSP;

    // Avoid a double-free from decorator_dsp::~decorator_dsp()
    fDSP = nullptr;

    dlclose(handle);
}
