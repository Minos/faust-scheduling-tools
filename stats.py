import itertools
import os

import matplotlib.pyplot as plt
import numpy as np

import common
import run


def denoised_average(a: np.typing.NDArray) -> float:
    half_size = a.shape[0] // 2
    return float(np.average(np.sort(a)[:half_size]))


def events_statistics(results: list[run.RunResult]) -> dict[str, dict[str, float]]:
    """
    Returns a dictionary where keys are the events measured in results, and
    values are a dictionary of average value by strategy. The values in this
    dictionary are normalized by the average values of all stategies for the
    same event
    """
    if len(results) == 0:
        return {}

    statistics = {}

    events = results[0].events.keys()
    for event in events:
        event_statistics = {
                res.run.strategy: denoised_average(res.events[event])
                for res in results
        }
        average = float(np.average(list(event_statistics.values())))
        if average != 0:
            for key, value in event_statistics.items():
                event_statistics[key] = value / average
        statistics[event] = event_statistics

    return statistics


def dsp_compiler_arch(result: run.RunResult):
    run = result.run
    return (
        os.path.join(run.directory, f'{run.program_name}.dsp'),
        result.run.compiler,
        result.run.arch
    )


def show_statistics(results: list[run.RunResult]):
    if len(results) == 0:
        return

    statistics = [events_statistics(list(group)) 
                  for _, group in itertools.groupby(results, dsp_compiler_arch)]

    for strategy in common.strategies:
        print(f'\033[1mPerformance of strategy {strategy}:\033[0m')
        for event in results[0].events.keys():
            perf = np.average([s[event][strategy] for s in statistics])
            print(f'{event}: {perf}')
        print()
