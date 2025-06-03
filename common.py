import os
import matplotlib.pyplot as plt

# Superscalar vector size
scaling_factor = 4

# Max number of PMU events that can run together
max_events_by_run = 4

root_dir = os.path.dirname(os.path.abspath(__file__))

build_dir_ext = 'fcsched'
faust_bencharch = os.path.join(root_dir, 'arch/bencharch.cpp')
faust_testarch = os.path.join(root_dir, 'arch/testarch.cpp')
faust_lang = 'ocpp'

deep_first = '0'
breadth_first = '1'
interleaved = '2'
reverse_breadth_first = '3'
list_scheduling = '4'

clang = 'clang++'
gcc = 'g++'
native = 'native'
generic = 'x86-64'

time = 'time(ns)'
cycles = 'cycles'
instructions = 'instructions'
uops_ge_1 = 'uops_executed.thread_cycles_ge_1'
uops_ge_2 = 'uops_executed.thread_cycles_ge_2'
uops_ge_3 = 'uops_executed.thread_cycles_ge_3'
uops_ge_4 = 'uops_executed.thread_cycles_ge_4'
stalls_total = 'cycle_activity:stalls_total'
stalls_mem = 'cycle_activity:stalls_mem_any'
fp_arith_scalar = 'fp_arith_inst_retired.scalar_single'
fp_arith_packed_2 = 'fp_arith_inst_retired.128b_packed_single'
fp_arith_packed_4 = 'fp_arith_inst_retired.256b_packed_single'
l1_dcache_loads = 'l1-dcache-loads'
l1_dcache_load_misses = 'l1-dcache-load-misses'
l1_dcache_stores = 'l1-dcache-stores'
l1_dcache_store_misses = 'l1-dcache-store-misses'
llc_loads = 'llc-loads'
llc_load_misses = 'llc-load-misses'
llc_stores = 'llc-stores'
llc_store_misses = 'llc-store-misses'

stalls_event_list = [cycles, uops_ge_1, stalls_mem, stalls_total]
uops_event_list = [uops_ge_1, uops_ge_2, uops_ge_3, uops_ge_4]
stat_event_list = [stalls_total, stalls_mem, uops_ge_1, uops_ge_2, uops_ge_3, uops_ge_4,
                   fp_arith_scalar, fp_arith_packed_2, fp_arith_packed_4,
                   l1_dcache_loads, l1_dcache_load_misses, l1_dcache_stores, l1_dcache_store_misses,
                   llc_loads, llc_load_misses, llc_stores, llc_store_misses]

preset_event_lists = {
    'stalls': stalls_event_list,
    'uops': uops_event_list,
    'all': stat_event_list
}


def get_preset_events(extended: bool) -> list[str]:
    result = [key
              for key, value in preset_event_lists.items()
              if extended or len(value) <= max_events_by_run]
    return sorted(result)


strategy_labels = {
    deep_first: 'deep-first',
    breadth_first: 'breadth-first',
    interleaved: 'interleaved',
    reverse_breadth_first: 'reverse_breadth_first',
    list_scheduling: 'list',
}

strategy_labels_short = {
    deep_first: 'DF',
    breadth_first: 'BF',
    interleaved: 'I',
    reverse_breadth_first: 'RBF',
    list_scheduling: 'LS',
}

compiler_labels = {
    clang: 'clang',
    gcc: 'gcc',
}

arch_labels = {
    native: 'native',
    generic: 'x86-64',
}

strategies = [deep_first, breadth_first, interleaved, reverse_breadth_first, list_scheduling]
compilers = [clang, gcc]
archs = [native, generic]


def find_faust():
    try:
        return os.environ['FAUST']
    except KeyError:
        return 'faust'


def setup_matplotlib(output):
    style = './report.mplstyle'
    if os.path.exists(style):
        plt.style.use(style)
    # When outputing to png format, we need a higher DPI.
    if output:
        plt.rcParams['figure.dpi'] = 512
