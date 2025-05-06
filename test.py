#!/usr/bin/env python

import csv
import multiprocessing
import subprocess

import numpy as np

import build
import common


atol = 1e-8
rtol = 1e-5


class Test:
    def __init__(self, directory, program_name, strategy):
        self.directory = directory
        self.program_name = program_name
        self.strategy = strategy
        self.path = build.test_binary(directory, program_name, strategy)
        self.impulse_response = None

    def get_impulse_response(self) -> np.typing.NDArray:
        if self.impulse_response is not None:
            return self.impulse_response

        proc = subprocess.Popen([self.path], stdout=subprocess.PIPE, text=True)
        reader = csv.reader(proc.stdout, delimiter=';')
        ir = []
        for line in reader:
            ir.append(line)
        self.impulse_response = np.array(ir, dtype=np.float32).T
        return self.impulse_response


def build_binaries(tests):
    binaries = [t.path for t in tests]
    nproc = multiprocessing.cpu_count()
    subprocess.run(["make", "-s", f"-j{nproc}"] + binaries).check_returncode()


def success(**kwargs):
    print("\033[32msuccess\033[0m", **kwargs)


def warning(msg, **kwargs):
    print(f"\033[33mwarning: {msg}\033[0m", **kwargs)


def failure(msg, **kwargs):
    print(f"\033[31mfailure: {msg}\033[0m", **kwargs)


def check_strategies(dsp):
    directory, program_name = build.split_prog_name(dsp)
    tests = [Test(directory, program_name, s) for s in common.strategies]

    print(f"  TEST   {program_name}... ", end="", flush=True)
    if len(tests) < 2:
        failure(f"need at least 2 strategies to compare between each other, "
                f"but only {len(tests)} were found.")
        return

    groups = []
    for t in tests:
        ir = t.get_impulse_response()
        try:
            group = next(g for g in groups
                         if np.allclose(g[0].get_impulse_response(), ir,
                                        atol=atol, rtol=rtol))
            group.append(t)
        except StopIteration:
            groups.append([t])

    if len(groups) == 1:
        if np.allclose(groups[0][0].get_impulse_response(), 0):
            success(end=' ')
            warning("impulse response is 0")
        else:
            success()
        return

    groups = sorted(groups, key=len, reverse=True)
    if len(groups) == 2 and len(groups[1]) == 1:
        failure(f"strategy {groups[1][0].strategy} gave a different "
                f"impulse response")
    else:
        failure(f"obtained {len(groups)} different impulse responses "
                f"from {len(tests)} strategies")

    print("\033[2mNon-matching samples from each channel:")

    ref = groups[0][0].get_impulse_response()
    for g in groups[1:]:
        other = g[0].get_impulse_response()
        diff = np.isclose(ref, other, atol=atol, rtol=rtol)
        diff = np.logical_not(diff)
        print(f"{ref[diff][:5]} [{' '.join([t.strategy for t in groups[0]])}]")
        print(f"{other[diff][:5]} [{' '.join([t.strategy for t in g])}]")

    print("\033[22m", end="")


def run_tests(files: list[str]):
    build.build_tests(files)

    for file in files:
        check_strategies(file)
