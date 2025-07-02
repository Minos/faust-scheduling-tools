#ifndef __FCSCHEDTOOL_UI_H__
#define __FCSCHEDTOOL_UI_H__

#include <cstring>

#include <faust/dsp/dsp.h>
#include <faust/gui/meta.h>

struct UI {
   public:
    virtual ~UI() {}
    void openTabBox(const char* label) {}
    void openHorizontalBox(const char* label) {}
    void openVerticalBox(const char* label) {}
    void closeBox() {}
    void addCheckButton(const char* label, float* zone) {}
    void addVerticalSlider(const char* label, float* zone, float min, float max,
                           float step, float init)
    {
    }
    void addHorizontalSlider(const char* label, float* zone, float min, float max,
                             float step, float init)
    {
    }
    void addNumEntry(const char* label, float* zone, float min, float max,
                     float step, float init)
    {
    }
    void addHorizontalBargraph(const char* label, float* zone, float min, float max)
    {
    }
    void addVerticalBargraph(const char* label, float* zone, float min, float max) {}
    void addText(const char* text) {}
    void declare(float* zone, const char* key, const char* value) {}
    void declare(const char* key, const char* value) {}

    void addButton(const char* label, float* zone)
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
