#!/usr/bin/env python

from typing import List

import numpy

from build import FaustTest, FaustTestRun, FaustTestResult


atol = 1e-8
rtol = 1e-5


def success(**kwargs):
    print('\033[32msuccess\033[0m', **kwargs)


def warning(msg, **kwargs):
    print(f'\033[33mwarning: {msg}\033[0m', **kwargs)


def failure(msg, **kwargs):
    print(f'\033[31mfailure: {msg}\033[0m', **kwargs)


def compare_outputs(test_result: FaustTestResult):
    codegens = test_result.test.faust_strategies
    if len(codegens) < 2:
        failure(f'need at least 2 strategies to compare between each other, '
                f'but only {len(codegens)} were found.')
        return

    groups = []
    for codegen in codegens:
        output = test_result.outputs[codegen]
        try:
            group = next(g for g in groups
                         if numpy.allclose(test_result.outputs[g[0]], output,
                                        atol=atol, rtol=rtol))
            group.append(codegen)
        except StopIteration:
            groups.append([codegen])

    if len(groups) == 1:
        if numpy.allclose(test_result.outputs[groups[0][0]], 0):
            success(end=' ')
            warning('impulse response is 0')
        else:
            success()
        return

    groups = sorted(groups, key=len, reverse=True)
    if len(groups) == 2 and len(groups[1]) == 1:
        failure(f'strategy {groups[1][0].strategy} gave a different '
                f'impulse response')
    else:
        failure(f'obtained {len(groups)} different impulse responses '
                f'from {len(codegens)} strategies')

    print('\033[2mNon-matching samples from each channel:')

    ref = test_result.outputs[groups[0][0]]
    for g in groups[1:]:
        other = test_result.outputs[g[0]]
        diff = numpy.isclose(ref, other, atol=atol, rtol=rtol)
        diff = numpy.logical_not(diff)
        print(f'{ref[diff][:5]} [{' '.join([t.strategy for t in groups[0]])}]')
        print(f'{other[diff][:5]} [{' '.join([t.strategy for t in g])}]')

    print('\033[22m', end='')


def run_tests(tests: List[FaustTest]):
    runs = [FaustTestRun(t) for t in tests]
    for test_run in runs:
        print(f'TEST   {test_run.test.program.src}... ', end='', flush=True)
        test_result = test_run.run()
        compare_outputs(test_result)
