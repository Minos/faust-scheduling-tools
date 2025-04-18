import os

# Superscalar vector size
scaling_factor = 4

deep_first = "0"
breadth_first = "1"
interleaved = "2"
reverse_breadth_first = "3"
custom = "4"

clang = "clang++"
gcc = "g++"
native = "native"
generic = "x86-64"

time = "time(ns)"
cycles = "cycles"
instructions = "instructions"
stalls_total = "stalls_total"
stalls_mem = "stalls_mem_any"


STRATEGY_LABELS = {
    deep_first: "deep-first",
    breadth_first: "breadth-first",
    interleaved: "interleaved",
    reverse_breadth_first: "reverse_breadth_first",
    custom: "custom",
}

STRATEGY_LABELS_SHORT = {
    deep_first: "DF",
    breadth_first: "BF",
    interleaved: "I",
    reverse_breadth_first: "RBF",
    custom: "CUS",
}

COMPILER_LABELS = {
    clang: "clang",
    gcc: "gcc",
}

ARCH_LABELS = {
    native: "native",
    generic: "generic",
}

STRATEGIES = [deep_first, breadth_first, interleaved, reverse_breadth_first]
COMPILERS = [clang, gcc]
ARCHS = [native, generic]


def find_dsp(path):
    if path.endswith(".dsp"):
        return path
    if os.path.isdir(path):
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.endswith(".dsp")
        ]
