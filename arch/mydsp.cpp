#include "mydsp.h"

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

<< includeIntrinsic >>
<< includeclass >>

dsp* create_dsp()
{
    return new mydsp();
}
