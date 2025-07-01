from __future__ import annotations

from enum import StrEnum


class PerfEvent(StrEnum):
    CYCLES = 'cycles'
    INSTRUCTIONS = 'instructions'
    UOPS_GE_1 = 'uops_executed.thread_cycles_ge_1'
    UOPS_GE_2 = 'uops_executed.thread_cycles_ge_2'
    UOPS_GE_3 = 'uops_executed.thread_cycles_ge_3'
    UOPS_GE_4 = 'uops_executed.thread_cycles_ge_4'
    STALLS_TOTAL = 'cycle_activity:stalls_total'
    STALLS_MEM = 'cycle_activity:stalls_mem_any'
    FP_ARITH_SCALAR = 'fp_arith_inst_retired.scalar_single'
    FP_ARITH_PACKED_2 = 'fp_arith_inst_retired.128b_packed_single'
    FP_ARITH_PACKED_4 = 'fp_arith_inst_retired.256b_packed_single'
    L1_DCACHE_LOADS = 'l1-dcache-loads'
    L1_DCACHE_LOAD_MISSES = 'l1-dcache-load-misses'
    L1_DCACHE_STORES = 'l1-dcache-stores'
    L1_DCACHE_STORE_MISSES = 'l1-dcache-store-misses'
    LLC_LOADS = 'llc-loads'
    LLC_LOAD_MISSES = 'llc-load-misses'
    LLC_STORES = 'llc-stores'
    LLC_STORE_MISSES = 'llc-store-misses'
