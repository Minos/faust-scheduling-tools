#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>

#define NBSAMPLES 44100
#define IMPULSE_SIZE 441

#ifndef FAUSTFLOAT
#define FAUSTFLOAT float
#endif

#ifndef FAUSTCLASS
#define FAUSTCLASS mydsp
#endif

#ifdef __APPLE__
#define exp10f __exp10f
#define exp10 __exp10
#endif

#if defined(_WIN32)
#define RESTRICT __restrict
#else
#define RESTRICT __restrict__
#endif

template <class T>
const T& min(const T& a, const T& b)
{
    return (b < a) ? b : a;
}

template <class T>
const T& max(const T& a, const T& b)
{
    return (b < a) ? a : b;
}

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
        static const char *patterns[] = {"play", "gate", "hit", NULL};
        for (int i=0; patterns[i] != NULL; i++) {
            if (strcasestr(label, patterns[i])) {
                *zone = 1;
            }
        }
    }

};

class Meta {
   public:
    virtual ~Meta() {}
    virtual void declare(const char* key, const char* value) = 0;
};

class dsp {
   private:
   public:
    virtual ~dsp() {}
    virtual void buildUserInterface(UI* ui_interface)                          = 0;
    virtual void compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs) = 0;
    virtual void init(int samplingFreq)                                        = 0;
    virtual void instanceClear()                                               = 0;
    virtual void instanceConstants(int samplingFreq)                           = 0;
    virtual void instanceInit(int samplingFreq)                                = 0;
    virtual void instanceResetUserInterface()                                  = 0;
    virtual int  getNumInputs()                                                = 0;
    virtual int  getNumOutputs()                                               = 0;
    virtual int  getSampleRate()                                               = 0;
    virtual dsp* clone()                                                       = 0;
};

#ifndef FAUSTFLOAT
#define FAUSTFLOAT float
#endif

#ifndef FAUSTCLASS
#define FAUSTCLASS mydsp
#endif

#ifdef __APPLE__
#define exp10f __exp10f
#define exp10 __exp10
#endif

#if defined(_WIN32)
#define RESTRICT __restrict
#else
#define RESTRICT __restrict__
#endif

<< includeIntrinsic >>

<< includeclass >>

int main(int argc, char* argv[])
{
    mydsp* d = new mydsp();

    if (d == nullptr) {
        std::cerr << "Failed to create DSP object\n";
        return 1;
    }
    d->init(44100);

    UI ui;
    d->buildUserInterface(&ui);

    // Create the input buffers
    FAUSTFLOAT* inputs[256];
    for (int i = 0; i < d->getNumInputs(); i++) {
        inputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            inputs[i][j] = 0.0;
        }
        for (int j = 0; j < IMPULSE_SIZE; j++) {
            inputs[i][j] = 1.0;
        }
    }

    // Create the output buffers
    FAUSTFLOAT* outputs[256];
    for (int i = 0; i < d->getNumOutputs(); i++) {
        outputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            outputs[i][j] = 0.0;
        }
    }

    // Compile the Impulse Response
    d->compute(NBSAMPLES, inputs, outputs);

    // Print the NBSAMPLES of the impulse response
    for (int i = 0; i < NBSAMPLES; i++) {
        std::cout << outputs[0][i];
        for (int j = 1; j < d->getNumOutputs(); j++) {
            std::cout << ";" << outputs[j][i];
        }
        std::cout << std::endl;
    }

    return 0;
}
