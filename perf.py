from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerfEvent:
    value: str

    def __lt__(self, other) -> bool:
        return self.value.__lt__(other.value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value

    @staticmethod
    def cycles() -> PerfEvent:
        return PerfEvent('cycles')

    @staticmethod
    def instructions() -> PerfEvent:
        return PerfEvent('instructions')

    @staticmethod
    def uops_ge_1() -> PerfEvent:
        return PerfEvent('uops_executed.thread_cycles_ge_1')

    @staticmethod
    def uops_ge_2() -> PerfEvent:
        return PerfEvent('uops_executed.thread_cycles_ge_2')

    @staticmethod
    def uops_ge_3() -> PerfEvent:
        return PerfEvent('uops_executed.thread_cycles_ge_3')

    @staticmethod
    def uops_ge_4() -> PerfEvent:
        return PerfEvent('uops_executed.thread_cycles_ge_4')

    @staticmethod
    def stalls_total() -> PerfEvent:
        return PerfEvent('cycle_activity:stalls_total')

    @staticmethod
    def stalls_mem() -> PerfEvent:
        return PerfEvent('cycle_activity:stalls_mem_any')

    @staticmethod
    def fp_arith_scalar() -> PerfEvent:
        return PerfEvent('fp_arith_inst_retired.scalar_single')

    @staticmethod
    def fp_arith_packed_2() -> PerfEvent:
        return PerfEvent('fp_arith_inst_retired.128b_packed_single')

    @staticmethod
    def fp_arith_packed_4() -> PerfEvent:
        return PerfEvent('fp_arith_inst_retired.256b_packed_single')

    @staticmethod
    def l1_dcache_loads() -> PerfEvent:
        return PerfEvent('l1-dcache-loads')

    @staticmethod
    def l1_dcache_load_misses() -> PerfEvent:
        return PerfEvent('l1-dcache-load-misses')

    @staticmethod
    def l1_dcache_stores() -> PerfEvent:
        return PerfEvent('l1-dcache-stores')

    @staticmethod
    def l1_dcache_store_misses() -> PerfEvent:
        return PerfEvent('l1-dcache-store-misses')

    @staticmethod
    def llc_loads() -> PerfEvent:
        return PerfEvent('llc-loads')

    @staticmethod
    def llc_load_misses() -> PerfEvent:
        return PerfEvent('llc-load-misses')

    @staticmethod
    def llc_stores() -> PerfEvent:
        return PerfEvent('llc-stores')

    @staticmethod
    def llc_store_misses() -> PerfEvent:
        return PerfEvent('llc-store-misses')
