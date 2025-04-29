import os
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

import common
from run import run_strategies


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
    x = np.arange(0, run_result.loops)
    lw = 0.5

    instr = run_result.events[common.instructions] / common.scaling_factor
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
    ax.fill_between(x, 0, instr, lw=lw, color="xkcd:burnt orange", label="instr/4")

    ax.plot(x, run_result.events[common.cycles], lw=lw, label="cycles", color="black")

    ax.set_ylim(ymin=0)
    ax.set_xlim(xmin=0, xmax=len(x))


def plot_events(run_result, ax):
    x = np.arange(0, run_result.loops)
    lw = 1

    for ev, y in run_result.events.items():
        ax.plot(x, y, lw=lw, label=ev)

    ax.set_ylim(ymin=0)
    ax.set_xlim(xmin=0, xmax=len(x))


def plot_multiple_runs(
    path, compilers, archs, *,
    output_file=None, events=common.stalls_event_list, nloops=1000,
    plot_fn=plot_stalls, override=False
):
    directory, filename = os.path.split(path)
    program_name, _ = os.path.splitext(filename)

    results = run_strategies(
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
        ax.set_ylim(ymax=ymax)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncols=4, loc="lower center")
    fig.suptitle(program_name)

    plt.subplots_adjust(hspace=0.5)

    if output_file:
        plt.savefig(output_file, bbox_inches="tight")
    else:
        plt.show()
