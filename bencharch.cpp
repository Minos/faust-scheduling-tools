#include <algorithm>
#include <cerrno>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>

#define NBSAMPLES 44100
#define NBITERATIONS 1000

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
    virtual void openTabBox(const char* label)                                         = 0;
    virtual void openHorizontalBox(const char* label)                                  = 0;
    virtual void openVerticalBox(const char* label)                                    = 0;
    virtual void closeBox()                                                            = 0;
    virtual void addButton(const char* label, FAUSTFLOAT* zone)                        = 0;
    virtual void addCheckButton(const char* label, FAUSTFLOAT* zone)                   = 0;
    virtual void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                   FAUSTFLOAT max, FAUSTFLOAT step, FAUSTFLOAT init)   = 0;
    virtual void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                     FAUSTFLOAT max, FAUSTFLOAT step, FAUSTFLOAT init) = 0;
    virtual void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max,
                             FAUSTFLOAT step, FAUSTFLOAT init)                         = 0;
    virtual void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                       FAUSTFLOAT max)                                 = 0;
    virtual void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min,
                                     FAUSTFLOAT max)                                   = 0;
    virtual void addText(const char* text)                                             = 0;
    virtual void declare(float* zone, const char* key, const char* value)              = 0;
    virtual void declare(const char* key, const char* value)                           = 0;
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

#include <algorithm>
#include <cmath>
#include <cstdint>

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

<<includeIntrinsic>>

<<includeclass>>

int main(int argc, char* argv[])
{
    long N = NBITERATIONS;  // How long the minimum should be stable to be the result

    if (argc > 2) {
        std::cerr << "Usage: " << argv[0] << " [optional int parameter]" << std::endl;
        return 1;
    }

    if (argc == 2) {
        char* endptr;
        errno    = 0;  // To distinguish success/failure after call
        long val = strtol(argv[1], &endptr, 10);

        // Check for various possible errors
        if ((errno == ERANGE && (val == LONG_MAX || val == LONG_MIN)) || (errno != 0 && val == 0)) {
            std::cerr << "Conversion error: " << argv[1] << std::endl;
            return 1;
        }

        if (endptr == argv[1]) {
            std::cerr << "No digits were found in: " << argv[1] << std::endl;
            return 1;
        }

        // If we got here, strtol() successfully parsed a number
        N = val;
    }
    mydsp* d = new mydsp();

    if (d == nullptr) {
        std::cerr << "Failed to create DSP object\n";
        return 1;
    }
    d->init(44100);

    // Create the input buffers
    FAUSTFLOAT* inputs[256];
    for (int i = 0; i < d->getNumInputs(); i++) {
        inputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            inputs[i][j] = 0.0;
        }
        inputs[i][0] = 1.0;
    }

    // Create the output buffers
    FAUSTFLOAT* outputs[256];
    for (int i = 0; i < d->getNumOutputs(); i++) {
        outputs[i] = new FAUSTFLOAT[NBSAMPLES];
        for (int j = 0; j < NBSAMPLES; j++) {
            outputs[i][j] = 0.0;
        }
    }
    // warmup
    d->compute(NBSAMPLES, inputs, outputs);

    // benchmark
    auto start = std::chrono::high_resolution_clock::now();

    d->compute(NBSAMPLES, inputs, outputs);

    auto end = std::chrono::high_resolution_clock::now();

    std::chrono::duration<double> totalduration(0);
    std::chrono::duration<double> mindur = end - start;

    while (N-- > 0) {
        start = std::chrono::high_resolution_clock::now();
        d->compute(NBSAMPLES, inputs, outputs);
        end                                    = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> duration = end - start;
        totalduration += duration;
        if (duration < mindur) {
            mindur = duration;
        }
    }

    delete d;

    std::cerr 
        << mindur.count() * 1000 << ";msec;minimum;" 
        << totalduration.count() * 1000 / NBITERATIONS << ";msec;average"
        << std::endl;

    return 0;
}
