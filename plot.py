import os
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from build import split_prog_name
import common
import run


color_uops_1 = 'xkcd:pale green'
color_uops_2 = 'xkcd:light green'
color_uops_3 = 'xkcd:green'
color_uops_4 = 'xkcd:dark green'
color_stalls_other = 'xkcd:light purple'
color_stalls_memory = 'xkcd:purple'
color_vec4 = '#AA0422'
color_vec2 = '#C03D55'
color_scalar = '#BFAB3C'
color_l1_load_misses = 'xkcd:orange'
color_l1_store_misses = 'xkcd:red'


class Run:
    strategy: str
    compiler: str
    arch: str
    loops: int
    events: dict[str, np.typing.NDArray]
    times: Optional[np.typing.NDArray]

    def __init__(self, strategy: str, compiler: str, arch: str):
        self.strategy = strategy
        self.compiler = compiler
        self.arch = arch
        self.loops = 0
        self.events = {}
        self.times = None

    def characteristics(self) -> str:
        return f"ss{self.strategy}_{self.compiler}_{self.arch}"


class Program:
    name: str
    runs: list[Run]

    def __init__(self, name):
        self.name = name
        self.runs = []


def plot_stalls(run_result, ax):
    x = np.arange(1, run_result.loops + 1)
    lw = 0.5

    instr = run_result.events[common.uops_ge_1]
    st_m = run_result.events[common.stalls_mem]
    st_t = run_result.events[common.stalls_total]

    ax.fill_between(
        x,
        instr + st_m,
        instr + st_t,
        lw=lw,
        color="xkcd:light purple",
        label="stalls(other)",
    )
    ax.fill_between(
        x, instr, instr + st_m, lw=lw, color="xkcd:purple", label="stalls(mem)"
    )
    ax.fill_between(x, 0, instr, lw=lw, color="#1E7304", label="uops >= 1")

    ax.plot(x, run_result.events[common.cycles], lw=lw, label="cycles", color="black")

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_uops(run_result, ax):
    x = np.arange(1, run_result.loops + 1)
    lw = 0.5

    uops_1 = run_result.events[common.uops_ge_1]
    uops_2 = run_result.events[common.uops_ge_2]
    uops_3 = run_result.events[common.uops_ge_3]
    uops_4 = run_result.events[common.uops_ge_4]

    ax.fill_between(x, 0, uops_1, lw=lw, label="cycles with 1 uop")
    ax.fill_between(x, 0, uops_2, lw=lw, label="cycles with 2 uops")
    ax.fill_between(x, 0, uops_3, lw=lw, label="cycles with 3 uops")
    ax.fill_between(x, 0, uops_4, lw=lw, label="cycles with 4 uops")

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_events(run_result, ax):
    x = np.arange(1, run_result.loops + 1)
    lw = 1

    for ev, y in run_result.events.items():
        ax.plot(x, y, lw=lw, label=ev)

    ax.set_xlim(xmin=1, xmax=len(x))


def plot_multiple_runs(
    path, compilers, archs, *,
    output_file=None, events=[], nloops=1000,
    plot_fn=plot_events, override=False
):
    directory, filename = os.path.split(path)
    program_name, _ = os.path.splitext(filename)

    results = run.run_strategies(
        directory, program_name,
        compilers=compilers,
        archs=archs,
        events=events,
        nloops=nloops,
        override=override
    )

    ymax = max([np.max(run.events[k]) for run in results for k in run.events.keys()]) * 1.1

    ncols = len(compilers) * len(archs)
    if ncols == 1:
        figsize = (6, 6)
    elif ncols == 2:
        figsize = (8, 6)
    else:
        figsize = (12, 6)

    fig, axes = plt.subplots(
        len(common.strategies),
        ncols,
        figsize=figsize,
        sharey=True,
        sharex=True,
        squeeze=False,
    )

    for res, ax in zip(results, (axes if len(results) == 16 else axes.T).flatten()):
        plot_fn(res, ax)
        ax.set_title(f"{common.strategy_labels[res.run.strategy]}")
        ax.set_title(
            f"{common.compiler_labels[res.run.compiler]} {common.arch_labels[res.run.arch]}, "
            f"{common.strategy_labels_short[res.run.strategy]}"
        )
        ax.set_ylim(ymin=0, ymax=ymax)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncols=4, loc="lower center")
    fig.suptitle(program_name)

    plt.subplots_adjust(hspace=0.5)

    if output_file:
        plt.savefig(output_file, bbox_inches="tight")
    else:
        plt.show()


def get_denoised_value(event: str, runs: list[run.RunResult]) -> np.typing.NDArray:
    return np.asarray([np.quantile(r.events[event], 0.2) for r in runs])


def plot_broken_bar(ax, y, height, sections: list[tuple[np.typing.NDArray, str, str]], *,
                    total=None, legend=''):
    left = 0
    for (x, label, color) in sections:
        ax.barh(y, x, height, left=left, label=label, color=color)
        left += x

    rects = ax.barh(y, total if total is not None else left, height,
                    fill=False, edgecolor='black')
    ax.bar_label(rects, labels=[legend for _ in y], padding=4, fontsize=8)


def plot_multiple_runs_summary(path, compilers, archs, *, output_file=None):
    directory, program_name = split_prog_name(path)

    results = run.run_strategies_grouped(
            directory, program_name, 
            compilers=compilers, archs=archs,
            events=common.stat_event_list)

    nlines = 3
    nticks = len(results)
    y = np.arange(nticks)

    fig, ax = plt.subplots()

    height = 1 / (nlines + 0.5)
    thickness = 0.8

    uops_eq_4 = get_denoised_value(common.uops_ge_4, results)
    uops_eq_3 = get_denoised_value(common.uops_ge_3, results) - uops_eq_4
    uops_eq_2 = get_denoised_value(common.uops_ge_2, results) - uops_eq_4 - uops_eq_3
    uops_eq_1 = get_denoised_value(common.uops_ge_1, results) - uops_eq_4 - uops_eq_3 - uops_eq_2
    mem_stalls = get_denoised_value(common.stalls_mem, results)
    other_stalls = get_denoised_value(common.stalls_total, results) - mem_stalls

    plot_broken_bar(ax, y, height * thickness, [
        (uops_eq_4, 'cycles with 4 uops', color_uops_4),
        (uops_eq_3, 'cycles with 3 uops', color_uops_3),
        (uops_eq_2, 'cycles with 2 uops', color_uops_2),
        (uops_eq_1, 'cycles with 1 uop', color_uops_1),
        (mem_stalls, 'stalled cycles (memory)', color_stalls_memory),
        (other_stalls, 'stalled cycles (other)', color_stalls_other),
    ], legend='cycles')

    plot_broken_bar(ax, y + height, height * thickness, [
        (4 * get_denoised_value(common.fp_arith_packed_4, results), '4-packed fp ops', color_vec4),
        (2 * get_denoised_value(common.fp_arith_packed_2, results), '2-packed fp ops', color_vec2),
        (get_denoised_value(common.fp_arith_scalar, results), 'scalar fp ops', color_scalar),
    ], legend='vectorization')

    l1_dcache_store_misses = get_denoised_value(common.l1_dcache_store_misses, results)
    l1_dcache_load_misses = get_denoised_value(common.l1_dcache_load_misses, results)
    l1_dcache_stores = get_denoised_value(common.l1_dcache_stores, results)
    l1_dcache_loads = get_denoised_value(common.l1_dcache_loads, results)
    l1_total = l1_dcache_store_misses + l1_dcache_load_misses + l1_dcache_stores + l1_dcache_loads

    plot_broken_bar(ax, y + height * 2, height * thickness, [
        (l1_dcache_store_misses, 'L1 dcache store misses', color_l1_store_misses),
        (l1_dcache_load_misses, 'L1 dcache load misses', color_l1_load_misses),
    ], total=l1_total, legend='memory access')

    ax.invert_yaxis()
    yticks = [f'{common.strategy_labels_short[r.run.strategy]}' for r in results]
    ax.set_yticks(y + height * (nlines / 2 - 0.5), yticks)
    ax.margins(x=0.2)

    fig.legend(ncols=1, bbox_to_anchor=(1.27, 0.8))
    fig.suptitle(program_name)

    plt.subplots_adjust(hspace=0.5)

    if output_file:
        plt.savefig(output_file, bbox_inches="tight")
    else:
        plt.show()
