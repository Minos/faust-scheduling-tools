#ifndef __MYDSP_H__
#define __MYDSP_H__

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <faust/dsp/dsp.h>
#include <faust/gui/meta.h>

class UI {
   public:
    virtual ~UI() {}
    void openTabBox(const char* label) {}
    void openHorizontalBox(const char* label) {}
    void openVerticalBox(const char* label) {}
    void closeBox() {}
    void addCheckButton(const char* label, FAUSTFLOAT* zone) {}
    void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                           FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                             FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                     FAUSTFLOAT step, FAUSTFLOAT init)
    {
    }
    void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max)
    {
    }
    void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max) {}
    void addText(const char* text) {}
    void declare(float* zone, const char* key, const char* value) {}
    void declare(const char* key, const char* value) {}

    void addButton(const char* label, FAUSTFLOAT* zone)
    {
        static const char* patterns[] = {"play", "gate", "hit", NULL};
        for (int i = 0; patterns[i] != NULL; i++) {
            if (strcasestr(label, patterns[i])) {
                *zone = 1;
            }
        }
    }
};

#endif
