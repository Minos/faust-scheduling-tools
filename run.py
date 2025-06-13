#!/usr/bin/env python

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import subprocess

import numpy as np

import common as co
import build


class RunException(BaseException):
    def __init__(self, cmd, process):
        self.cmd = cmd
        self.process = process

    def __str__(self):
        return (
            f'Execution failed with return code '
            f'{self.process.returncode}:\n'
            f'{' '.join(self.cmd)}\n'
            f'{self.process.stderr}'
        )


class RunResult:
    run: Run
    loops: int
    events: dict[str, np.typing.NDArray]
    times: np.typing.NDArray

    def __init__(self, run, loops, events, times):
        self.run = run
        self.loops = loops
        self.events = events
        self.times = times


class Run:
    def __init__(self, directory, program_name, compiler, arch, strategy, btype):
        self.directory = directory
        self.program_name = program_name
        self.compiler = compiler
        self.arch = arch
        self.strategy = strategy
        self.btype = btype
        self.path = build.bench_binary(directory, program_name, strategy,
                                       compiler, arch, btype)

    def print_run_info(self):
        print(f'  RUN    {self.directory}/{self.program_name}.dsp '
              f'[strategy {self.strategy}, {self.compiler}, {self.arch}]')

    def output(self, events, nloops):
        measures = f'events: {sorted(events)}, nloops: {nloops}'
        run_hash = hashlib.sha1(measures.encode('utf-8')).hexdigest()[:8]
        btype_suffix = f'_{self.btype}' if self.btype is not None else ''
        return f'{self.path}{btype_suffix}.{run_hash}.csv'

    def exec(self, *, events=[], nloops=1000, override=False):
        output = self.output(events, nloops)
        if not override \
                and os.path.exists(output) \
                and os.path.getmtime(output) > os.path.getmtime(self.path):
            with open(output) as f:
                return parse_run_output(self, f)

        self.print_run_info()

        cmd = [self.path,
               '-r',
               '-o', output,
               '-n', str(nloops),
               '-e', ','.join(events)]

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise RunException(cmd, proc)

        with open(output) as f:
            return parse_run_output(self, f)


def parse_run_output(run, output) -> RunResult:
    reader = csv.reader(output, delimiter=';')
    header = [col for col in next(reader) if len(col) > 0]
    events = [[] for h in header if len(h) > 0]
    loops = 0
    for row in reader:
        if len(row) > 0:
            for i, col in enumerate(row):
                if len(col) > 0:
                    events[i].append(int(col))
            loops += 1

    events_dict = {k: np.array(events[i]) for i, k in enumerate(header)}
    times = events_dict.pop(co.time, None)

    return RunResult(run, loops, events_dict, times)


def run_strategies(
    directory,
    program_name,
    *,
    compilers=co.compilers,
    archs=co.archs,
    btype=None,
    events=[],
    nloops=1000,
    override=False
):
    runs = [
        Run(directory, program_name, cc, a, s, btype)
        for cc in compilers
        for a in archs
        for s in co.strategies
    ]

    return [r.exec(events=events, nloops=nloops, override=override)
            for r in runs]


def merge_run_results(results: list[RunResult]) -> RunResult:
    base = results[0]
    merge = RunResult(base.run, base.loops, base.events, base.times)
    for r in results[1:]:
        merge.loops += r.loops
        merge.events.update(r.events)
        merge.times = np.concatenate((merge.times, r.times))
    return merge


def run_strategies_grouped(
    directory,
    program_name,
    *,
    compilers=co.compilers,
    archs=co.archs,
    btype=None,
    events=[],
    nloops=100,
    override=False
) -> list[RunResult]:
    runs = [
        Run(directory, program_name, cc, a, s, btype)
        for cc in compilers
        for a in archs
        for s in co.strategies
    ]

    number_of_runs = math.ceil(len(events) / co.max_events_by_run)
    results = []
    for r in runs:
        group = []
        for i in range(number_of_runs):
            e = events[i*co.max_events_by_run:(i+1)*co.max_events_by_run]
            group.append(r.exec(events=e, nloops=nloops, override=override))
        results.append(merge_run_results(group))
    return results
