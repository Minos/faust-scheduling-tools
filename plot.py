from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Optional, List, Dict

import os

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np

from build import (FaustStrategy, CompilationStrategy, Scheduling, 
                   FaustBenchmark, FaustBenchmarkResult)
from perf import PerfEvent


class PlotType(StrEnum):
    STALLS = 'stalls'
    UOPS = 'uops'
    SUMMARY = 'summary'

    @staticmethod
    def parse(arg: str) -> Optional[PlotType]:
        try:
            return PlotType(arg)
        except ValueError:
            return None

    def events(self) -> List[PerfEvent]:
        if self == PlotType.STALLS:
            return [PerfEvent.cycles(),
                    PerfEvent.instructions(),
                    PerfEvent.stalls_mem(),
                    PerfEvent.stalls_total()]
        elif self == PlotType.UOPS:
            return [PerfEvent.uops_ge_1(),
                    PerfEvent.uops_ge_2(),
                    PerfEvent.uops_ge_3(),
                    PerfEvent.uops_ge_4()]
        elif self == PlotType.SUMMARY:
            return [PerfEvent.stalls_total(),
                    PerfEvent.stalls_mem(),
                    PerfEvent.uops_ge_1(),
                    PerfEvent.uops_ge_2(),
                    PerfEvent.uops_ge_3(),
                    PerfEvent.uops_ge_4(),
                    PerfEvent.fp_arith_scalar(),
                    PerfEvent.fp_arith_packed_2(),
                    PerfEvent.fp_arith_packed_4(),
                    PerfEvent.l1_dcache_loads(),
                    PerfEvent.l1_dcache_load_misses(),
                    PerfEvent.l1_dcache_stores(),
                    PerfEvent.l1_dcache_store_misses(),
                    PerfEvent.llc_loads(),
                    PerfEvent.llc_load_misses(),
                    PerfEvent.llc_stores(),
                    PerfEvent.llc_store_misses()]
        else:
            return []

    @staticmethod
    def all(extended: bool = True) -> List[PlotType]:
        return sorted([t for t in PlotType if extended or len(t.events()) <= 4])


def faust_strategy_label(strategy: FaustStrategy) -> str:
    if strategy.scheduling == Scheduling.DEEP_FIRST:
        return 'deep-first'
    if strategy.scheduling == Scheduling.REVERSE_DEEP_FIRST:
      return 'reverse-deep-first'
    if strategy.scheduling == Scheduling.BREADTH_FIRST:
      return 'breadth-first'
    if strategy.scheduling == Scheduling.REVERSE_BREADTH_FIRST:
      return 'reverse-breadth-first'
    if strategy.scheduling == Scheduling.INTERLEAVED:
      return 'interleaved'
    if strategy.scheduling == Scheduling.ADAPTIVE:
      return 'adaptive'
    if strategy.scheduling == Scheduling.REVERSE_ADAPTIVE:
        return 'reverse-adaptive'
    return 'unknown'


def faust_strategy_label_short(strategy: FaustStrategy) -> str:
    if strategy.scheduling == Scheduling.DEEP_FIRST:
        return 'DF'
    if strategy.scheduling == Scheduling.REVERSE_DEEP_FIRST:
        return 'RDF'
    if strategy.scheduling == Scheduling.BREADTH_FIRST:
        return 'BF'
    if strategy.scheduling == Scheduling.REVERSE_BREADTH_FIRST:
        return 'RBF'
    if strategy.scheduling == Scheduling.INTERLEAVED:
        return 'I'
    if strategy.scheduling == Scheduling.ADAPTIVE:
        return 'A'
    if strategy.scheduling == Scheduling.REVERSE_ADAPTIVE:
        return 'RA'
    return '??'


def compilation_strategy_label(strategy: CompilationStrategy) -> str:
    return f'{strategy.compiler} {strategy.architecture}'


def line_color(event: PerfEvent) -> str:
    if event == PerfEvent.instructions():
        return 'xkcd:dark orange'
    elif event == PerfEvent.uops_ge_1():
        return 'xkcd:pale green'
    elif event == PerfEvent.uops_ge_2():
        return 'xkcd:light green'
    elif event == PerfEvent.uops_ge_3():
        return 'xkcd:green'
    elif event == PerfEvent.uops_ge_4():
        return 'xkcd:dark green'
    elif event == PerfEvent.stalls_total():
        return 'xkcd:light purple'
    elif event == PerfEvent.stalls_mem():
        return 'xkcd:purple'
    elif event == PerfEvent.fp_arith_packed_4():
        return '#AA0422'
    elif event == PerfEvent.fp_arith_packed_2():
        return '#C03D55'
    elif event == PerfEvent.fp_arith_scalar():
        return '#BFAB3C'
    elif event == PerfEvent.l1_dcache_load_misses():
        return 'xkcd:orange'
    elif event == PerfEvent.l1_dcache_store_misses():
        return 'xkcd:red'
    else:
        return 'black'


def setup_matplotlib(output: Optional[str]):
    style = './report.mplstyle'
    if os.path.exists(style):
        plt.style.use(style)
    # When outputing to png format, we need a higher DPI.
    if output is not None:
        plt.rcParams['figure.dpi'] = 512


def plot_stalls(run_result: FaustBenchmarkResult, ax: Axes):
    x = np.arange(1, run_result.loops + 1)
    lw = 0.5

    instructions = run_result.events[PerfEvent.instructions()] / 4
    mem_stalls = run_result.events[PerfEvent.stalls_mem()]
    total_stalls = run_result.events[PerfEvent.stalls_total()]

    ax.fill_between(x, instructions + mem_stalls, instructions + total_stalls,
                    lw=lw,
                    color=line_color(PerfEvent.stalls_total()),
                    label="stalls(other)")

    ax.fill_between(x, instructions, instructions + mem_stalls,
                    lw=lw,
                    color=line_color(PerfEvent.stalls_mem()),
                    label="stalls(mem)")

    ax.fill_between(x, 0, instructions,
                    lw=lw,
                    color=line_color(PerfEvent.instructions()),
                    label="instr/4")

    ax.plot(x, run_result.events[PerfEvent.cycles()], lw=lw, label="cycles", color="black")

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_uops(run_result: FaustBenchmarkResult, ax: Axes):
    x = np.arange(1, run_result.loops + 1)
    lw = 0.5

    ax.fill_between(x, 0, run_result.events[PerfEvent.uops_ge_1()],
                    lw=lw,
                    color=line_color(PerfEvent.uops_ge_1()),
                    label="cycles with 1 uop")

    ax.fill_between(x, 0, run_result.events[PerfEvent.uops_ge_2()],
                    lw=lw,
                    color=line_color(PerfEvent.uops_ge_2()),
                    label="cycles with 2 uops")

    ax.fill_between(x, 0, run_result.events[PerfEvent.uops_ge_3()],
                    lw=lw,
                    color=line_color(PerfEvent.uops_ge_3()),
                    label="cycles with 3 uops")

    ax.fill_between(x, 0, run_result.events[PerfEvent.uops_ge_4()],
                    lw=lw,
                    color=line_color(PerfEvent.uops_ge_3()),
                    label="cycles with 4 uops")

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_events(run_result: FaustBenchmarkResult, ax: Axes):
    x = np.arange(1, run_result.loops + 1)
    lw = 1

    for ev, y in run_result.events.items():
        ax.plot(x, y, lw=lw, label=ev)

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_benchmark_loops(
        benchmark: FaustBenchmark,
        *,
        plot_type: Optional[PlotType] = None,
        output_directory: Optional[str] = None
):
    setup_matplotlib(output_directory)

    results = benchmark.run()

    print(f'PLOT   {benchmark.program.src}')

    plot_fn = plot_events
    if plot_type == PlotType.STALLS:
        plot_fn = plot_stalls
    elif plot_type == PlotType.UOPS:
        plot_fn = plot_uops

    ymax = max([np.max(run.events[k]) for run in results for k in run.events.keys()]) * 1.1

    nvariants = len(benchmark.compilation_strategies)
    if nvariants == 1:
        figsize = (6, 6)
    elif nvariants == 2:
        figsize = (8, 6)
    else:
        figsize = (12, 6)

    if nvariants == 1:
        ncols = 1
        nrows = len(benchmark.faust_strategies)
    else:
        ncols = len(benchmark.faust_strategies)
        nrows = nvariants

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=figsize,
        sharey=True,
        sharex=True,
        squeeze=False,
    )

    for result, ax in zip(results, (axes.T if nvariants >= 4 else axes).flatten()):
        plot_fn(result, ax)
        compilation_strategy = result.run.compilation_strategy
        ax.set_title(
            f"{compilation_strategy.compiler} {compilation_strategy.architecture}, "
            f"{faust_strategy_label_short(result.run.faust_strategy)}"
        )
        ax.set_ylim(ymin=0, ymax=ymax)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncols=4, loc="lower center")
    fig.suptitle(benchmark.program.name)

    plt.subplots_adjust(hspace=0.5)

    if output_directory:
        os.makedirs(output_directory, mode=0o755, exist_ok=True)
        filename = f'{benchmark.program.name}_{benchmark.bench_type.value}_{benchmark.loops}'
        if plot_type is not None:
            filename += f'_{plot_type.value}'
        filename += f'.png'
        plt.savefig(os.path.join(output_directory, filename), bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def denoise(array: np.typing.NDArray) -> np.floating:
    return np.quantile(array, 0.2)


def get_denoised_value(event: PerfEvent, 
                       results: List[FaustBenchmarkResult]) -> np.typing.NDArray:
    return np.asarray([denoise(r.events[event]) for r in results])


def plot_broken_bar(ax, y, height, sections: list[tuple[np.typing.NDArray, str, str]], *,
                    total=None, legend=''):
    left = 0
    for (x, label, color) in sections:
        ax.barh(y, x, height, left=left, label=label, color=color)
        left += x

    rects = ax.barh(y, total if total is not None else left, height,
                    fill=False, edgecolor='black')
    ax.bar_label(rects, labels=[legend for _ in y], padding=4, fontsize=8)


def plot_benchmark_summary(
        benchmark: FaustBenchmark, 
        output_directory: Optional[str]
):
    setup_matplotlib(output_directory)

    results = benchmark.run()

    print(f'PLOT   {benchmark.program.src}')

    nlines = 3
    nticks = len(results)
    y = np.arange(nticks)

    fig, ax = plt.subplots()

    height = 1 / (nlines + 0.5)
    thickness = 0.8

    uops_ge_4 = get_denoised_value(PerfEvent.uops_ge_4(), results)
    uops_ge_3 = get_denoised_value(PerfEvent.uops_ge_3(), results)
    uops_ge_2 = get_denoised_value(PerfEvent.uops_ge_2(), results)
    uops_ge_1 = get_denoised_value(PerfEvent.uops_ge_1(), results)

    uops_eq_4 = uops_ge_4
    uops_eq_3 = uops_ge_3 - uops_ge_4
    uops_eq_2 = uops_ge_2 - uops_ge_3
    uops_eq_1 = uops_ge_1 - uops_ge_2

    mem_stalls = get_denoised_value(PerfEvent.stalls_mem(), results)
    other_stalls = get_denoised_value(PerfEvent.stalls_total(), results) - mem_stalls

    plot_broken_bar(ax, y, height * thickness, [
        (uops_eq_4, 'cycles with 4 uops', line_color(PerfEvent.uops_ge_4())),
        (uops_eq_3, 'cycles with 3 uops', line_color(PerfEvent.uops_ge_3())),
        (uops_eq_2, 'cycles with 2 uops', line_color(PerfEvent.uops_ge_2())),
        (uops_eq_1, 'cycles with 1 uop', line_color(PerfEvent.uops_ge_1())),
        (mem_stalls, 'stalled cycles (memory)', line_color(PerfEvent.stalls_mem())),
        (other_stalls, 'stalled cycles (other)', line_color(PerfEvent.stalls_total())),
    ], legend='cycles')

    plot_broken_bar(ax, y + height, height * thickness, [
        (4 * get_denoised_value(PerfEvent.fp_arith_packed_4(), results), 
         '4-packed fp ops', 
         line_color(PerfEvent.fp_arith_packed_4())),
        (2 * get_denoised_value(PerfEvent.fp_arith_packed_2(), results), 
         '2-packed fp ops', 
         line_color(PerfEvent.fp_arith_packed_2())),
        (get_denoised_value(PerfEvent.fp_arith_scalar(), results), 
         'scalar fp ops', 
         line_color(PerfEvent.fp_arith_scalar())),
    ], legend='vectorization')

    l1_dcache_store_misses = get_denoised_value(PerfEvent.l1_dcache_store_misses(), results)
    l1_dcache_load_misses = get_denoised_value(PerfEvent.l1_dcache_load_misses(), results)
    l1_dcache_stores = get_denoised_value(PerfEvent.l1_dcache_stores(), results)
    l1_dcache_loads = get_denoised_value(PerfEvent.l1_dcache_loads(), results)
    l1_total = l1_dcache_store_misses + l1_dcache_load_misses + l1_dcache_stores + l1_dcache_loads

    plot_broken_bar(ax, y + height * 2, height * thickness, [
        (l1_dcache_store_misses, 'L1 dcache store misses', 
         line_color(PerfEvent.l1_dcache_store_misses())),
        (l1_dcache_load_misses, 'L1 dcache load misses', 
         line_color(PerfEvent.l1_dcache_load_misses())),
    ], total=l1_total, legend='memory access')

    ax.invert_yaxis()
    yticks = [f'{compilation_strategy_label(r.run.compilation_strategy)}, '
              f'{faust_strategy_label_short(r.run.faust_strategy)}' 
              for r in results]
    ax.set_yticks(y + height * (nlines / 2 - 0.5), yticks)
    ax.margins(x=0.2)

    fig.legend(ncols=1, bbox_to_anchor=(1.27, 0.8))
    fig.suptitle(benchmark.program.name)

    plt.subplots_adjust(hspace=0.5)

    if output_directory:
        os.makedirs(output_directory, mode=0o755, exist_ok=True)
        filename = f'{benchmark.program.name}_{benchmark.bench_type.value}_{benchmark.loops}' \
                   f'_summary.png'
        plt.savefig(os.path.join(output_directory, filename), bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_times( 
        benchmarks: List[FaustBenchmark], 
        output_file: Optional[str]):

    relative_performance: Dict[FaustStrategy, List[np.floating]] = defaultdict(list)
    for benchmark in benchmarks:
        results = benchmark.run()
        times = np.array([denoise(r.times) for r in results])
        # times /= np.average(times)
        for i, result in enumerate(results):
            relative_performance[result.run.faust_strategy].append(times[i])

    print('PLOT')

    setup_matplotlib(output_file)

    fig, ax = plt.subplots()
    x = np.arange(len(benchmarks))
    xticks = [b.program.name for b in benchmarks]
    ax.set_xticks(x, xticks)

    strategies = list(relative_performance.keys())
    ncols = len(strategies)
    width = 1 / (ncols + 1)

    offset = 0
    for strategy, times in relative_performance.items():
        ax.plot(x, np.asarray(times),
                label=faust_strategy_label(strategy))
        offset += width
        print(f'Strategy {faust_strategy_label(strategy)} average performance: {np.mean(np.asarray(times))}')

    fig.legend()

    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
    else:
        plt.show()

    plt.close()
