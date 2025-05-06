import os
import matplotlib.pyplot as plt

# Superscalar vector size
scaling_factor = 4

root_dir = os.path.dirname(os.path.abspath(__file__))

build_dir_ext = "fcsched"
faust_bencharch = os.path.join(root_dir, "arch/bencharch.cpp")
faust_testarch = os.path.join(root_dir, "arch/testarch.cpp")
faust_lang = "ocpp"

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
stalls_total = "cycle_activity:stalls_total"
stalls_mem = "cycle_activity:stalls_mem_any"
nop = "inst_retired.nop"

stalls_event_list = [cycles, instructions, stalls_mem, stalls_total]

strategy_labels = {
    deep_first: "deep-first",
    breadth_first: "breadth-first",
    interleaved: "interleaved",
    reverse_breadth_first: "reverse_breadth_first",
    custom: "custom",
}

strategy_labels_short = {
    deep_first: "DF",
    breadth_first: "BF",
    interleaved: "I",
    reverse_breadth_first: "RBF",
    custom: "CUS",
}

compiler_labels = {
    clang: "clang",
    gcc: "gcc",
}

arch_labels = {
    native: "native",
    generic: "x86-64",
}

strategies = [deep_first, breadth_first, interleaved, reverse_breadth_first]
compilers = [clang, gcc]
archs = [native, generic]


def find_faust():
    try:
        return os.environ['FAUST']
    except KeyError:
        return "faust"


def setup_matplotlib(output):
    style = "./report.mplstyle"
    if os.path.exists(style):
        plt.style.use(style)
    # When outputing to png format, we need a higher DPI.
    if output:
        plt.rcParams["figure.dpi"] = 512
