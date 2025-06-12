from __future__ import annotations
from typing import Optional

import multiprocessing
import os
import subprocess
import threading

import common


"""
This is a make-like utility to build benchmarking and testing binaries.
"""

def build_benchmarks(
    dsp_list, *,
    strategies=common.strategies,
    compilers=common.compilers,
    archs=common.archs
):
    """Build benchmarking binaries for each given faust program

    Keyword arguments:
    strategies -- scheduling strategies (default all)
    compilers -- C++ compilers to test (default: [clang++, g++])
    archs -- architectures to test (default: [native, x86-64])
    """
    tasks: list[Task] = []

    base_tasks = [CppGenericTask(src) for src in benchmarking_sources]
    tasks += base_tasks

    for dsp in dsp_list:
        make_build_dir(dsp)
        for s in strategies:
            faust_task = FaustTask(dsp, s)
            tasks += [faust_task]

            for c in compilers:
                for a in archs:
                    cpp_task = CppBenchTask(dsp, s, c, a, deps=[faust_task])
                    tasks.append(cpp_task)
                    ld_task = LdBenchTask(dsp, s, c, a, deps=[cpp_task, *base_tasks])
                    tasks.append(ld_task)

    scheduler = BuildScheduler(tasks)
    scheduler.run()


def build_tests(dsp_list, *, strategies=common.strategies):
    """Build testing binaries for each given faust program

    Keyword arguments:
    strategies -- scheduling strategies (default: all)
    """
    tasks: list[Task] = []

    base_tasks = [CppGenericTask(src) for src in testing_sources]
    tasks += base_tasks

    for dsp in dsp_list:
        make_build_dir(dsp)
        for s in strategies:
            faust_task = FaustTask(dsp, s)
            tasks.append(faust_task)

            cpp_task = CppTestTask(dsp, s, deps=[faust_task])
            tasks.append(cpp_task)

            ld_task = LdTestTask(dsp, s, deps=[cpp_task, *base_tasks])
            tasks.append(ld_task)

    scheduler = BuildScheduler(tasks)
    scheduler.run()


def make_build_dir(dsp):
    os.makedirs(build_dir(*split_prog_name(dsp)), mode=0o755, exist_ok=True)


def split_prog_name(dsp):
    directory, file = os.path.split(dsp)
    prog, _ = os.path.splitext(file)
    return directory, prog


def build_dir(directory, prog_name):
    return os.path.join(directory,
                        f'{prog_name}.{common.build_dir_ext}')


def base_cpp_file(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name),
                        f'{prog_name}_ss{strategy}.cpp')


def bench_obj_file(directory, prog_name, strategy, compiler, arch):
    return os.path.join(build_dir(directory, prog_name),
                        f'{prog_name}_ss{strategy}_{compiler}_{arch}_bench.o')


def bench_binary(directory, prog_name, strategy, compiler, arch):
    return os.path.join(build_dir(directory, prog_name),
                        f'{prog_name}_ss{strategy}_bench_{compiler}_{arch}')


def test_obj_file(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name),
                        f'{prog_name}_ss{strategy}_test.o')


def test_binary(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name),
                        f'{prog_name}_ss{strategy}_test')


def generic_obj_file(src):
    base, _ = os.path.splitext(src)
    return f'{base}.o'


faust_architecture_file = os.path.join(common.root_dir, 'arch/mydsp.cpp')

benchmarking_sources = list(map(lambda f: os.path.join(common.root_dir, f), [
    'arch/dsp_measuring.cpp',
    'arch/benchmark_quick.cpp',
    ]))
benchmarking_objects = list(map(generic_obj_file, benchmarking_sources))

testing_sources = list(map(lambda f: os.path.join(common.root_dir, f), [
    'arch/test.cpp',
    ]))
testing_objects = list(map(generic_obj_file, testing_sources))


class TaskException(BaseException):
    def __init__(self, task, process):
        self.task = task
        self.process = process

    def __str__(self):
        command = ' '.join(self.task.command())
        return f'Error building {self.task.product}:\n{command}\n{self.process.stderr}'


class TaskDependencyException(TaskException):
    def __init__(self, task, dependency):
        self.task = task
        self.dependency = dependency

    def __str__(self):
        return f'{self.task.product} could not be built because it depends on ' \
               f'{self.dependency}, which failed to build.'


class SchedulerException(BaseException):
    errors: list[TaskException]

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return '\n'.join([str(e) for e in self.errors])


class Task(object):
    """Base class for any build task

    Attributes:
        sources -- list of source files for this tasks
        product -- product file for this task
        deps -- list of tasks this task depends on
    """
    sources: list[str]
    product: str
    deps: list[Task]

    running: bool
    complete: bool
    failed: bool

    def __init__(self, sources: list[str], product: str, deps: list[Task] = []):
        self.sources = sources
        self.product = product
        self.deps = deps
        self.running = False
        self.failed = False
        self.complete = self.is_up_to_date()

    def is_up_to_date(self) -> bool:
        """
        Returns True iff this tasks's product exists and is newer than all its
        sources, and all the dependencies have been completed
        """
        if not os.path.exists(self.product):
            return False
        for s in self.dependencies():
            if not os.path.exists(s):
                return False
            if os.path.getmtime(s) > os.path.getmtime(self.product):
                return False
        return self.is_ready()

    def is_ready(self) -> bool:
        return all(d.complete for d in self.deps)

    def run(self):
        """Run the task"""
        for d in self.deps:
            if d.failed:
                raise TaskDependencyException(self, d)

        self.print_info()
        # print(f'\033[2m{" ".join(self.command())}\033[22m')
        process = subprocess.run(self.command(), capture_output=True, text=True)
        if process.returncode:
            raise TaskException(self, process)

    def dependencies(self) -> list[str]:
        return self.sources

    def command(self) -> list[str]:
        raise Exception('Not implemented')

    def print_info(self):
        pass


class FaustTask(Task):
    """A task that compiles a FAUST program into a C++ class

    Attributes:
    src -- a FAUST program
    strategy -- a scheduling strategy number
    """

    src: str
    strategy: str

    def __init__(self, src, strategy):
        self.src = src
        directory, prog = split_prog_name(src)
        self.strategy = strategy

        super(FaustTask, self).__init__([src], base_cpp_file(directory, prog, strategy))

    def dependencies(self):
        return super(FaustTask, self).dependencies() + benchmarking_sources + \
                [faust_architecture_file, common.find_faust()]

    def command(self):
        return [common.find_faust(),
                '-a', faust_architecture_file,
                '-lang', common.faust_lang,
                # '-sg', # Print signal graph
                '-ss', self.strategy,
                '-o', self.product,
                self.sources[0]]

    def print_info(self):
        print(f'  FAUST  {self.src} [strategy {self.strategy}]')

    def run(self):
        # Faust sometimes outputs an empty C++ file upon failure. It's better
        # to delete it, otherwise the next run will consider this file as
        # valid and try to compile it.
        try:
            super(FaustTask, self).run()
        except TaskException as err:
            if os.path.exists(self.product):
                os.remove(self.product)
            raise err


class CppGenericTask(Task):
    """Compile a C++ file into a C++ object file"""

    def __init__(self, src):
        super(CppGenericTask, self).__init__([src], generic_obj_file(src))

    def command(self):
        return [common.clang, '-march=native', '-O2', '--std=c++20', '-c',
                self.sources[0], '-o', self.product]

    def print_info(self):
        print(f'  CC     {self.sources[0]}')


class CppBenchTask(Task):
    """Compile a C++ dsp into a C++ object file for benchmarking"""

    directory: str
    dsp: str
    strategy: str
    compiler: str
    arch: str

    def __init__(self, dsp, strategy, compiler, arch, deps):
        self.dsp = dsp
        self.directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy
        self.compiler = compiler
        self.arch = arch

        super(CppBenchTask, self).__init__(
            [base_cpp_file(self.directory, self.prog, strategy)],
            bench_obj_file(self.directory, self.prog, strategy, compiler, arch),
            deps=deps
        )

    def command(self):
        return [self.compiler,
                f'-march={self.arch}',
                '-O3', '-ffast-math', '--std=c++20',
                f'-I{self.directory}', f'-I{common.root_dir}/arch',
                self.sources[0],
                '-c', '-o', self.product]

    def print_info(self):
        print(f'  CC     {self.dsp} [strategy {self.strategy}, '
              f'{self.compiler}, {self.arch}] (benchmarking)')


class LdBenchTask(Task):
    """Link a C++ object file compiled for benchmarking with the benchmarking program"""

    directory: str
    dsp: str
    strategy: str
    compiler: str
    arch: str

    def __init__(self, dsp, strategy, compiler, arch, deps):
        self.dsp = dsp
        self.directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy
        self.compiler = compiler
        self.arch = arch

        sources = benchmarking_objects + \
                [bench_obj_file(self.directory, self.prog, strategy, compiler, arch)]
        product = bench_binary(self.directory, self.prog, strategy, compiler, arch)

        super(LdBenchTask, self).__init__(sources, product, deps=deps)

    def command(self):
        return [self.compiler,
                '-lpfm',
                *self.sources,
                '-o', self.product]

    def print_info(self):
        print(f'  LD     {self.dsp} [strategy {self.strategy}, {self.compiler}, {self.arch}]')


class CppTestTask(Task):
    """Compile a C++ dsp into a C++ object file for testing"""

    directory: str
    dsp: str
    strategy: str

    def __init__(self, dsp, strategy, deps):
        self.dsp = dsp
        self.directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy

        super(CppTestTask, self).__init__(
            [base_cpp_file(self.directory, self.prog, strategy)],
            test_obj_file(self.directory, self.prog, strategy),
            deps=deps
        )

    def command(self):
        return [common.clang,
                f'-march=native', '-O0',
                f'-I{self.directory}', f'-I{common.root_dir}/arch',
                self.sources[0],
                '-c', '-o', self.product]

    def print_info(self):
        print(f'  CC     {self.dsp} [strategy {self.strategy}] (testing)')


class LdTestTask(Task):
    """Link a C++ object file compiled for testing with the testing program"""

    dsp: str
    strategy: str

    def __init__(self, dsp, strategy, deps):
        self.dsp = dsp
        directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy

        sources = testing_objects + \
                [test_obj_file(directory, self.prog, strategy)]
        product = test_binary(directory, self.prog, strategy)

        super(LdTestTask, self).__init__(sources, product, deps=deps)

    def command(self):
        return [common.clang, *self.sources, '-o', self.product]

    def print_info(self):
        print(f'  LD     {self.dsp} [strategy {self.strategy}] (testing)')


class BuildScheduler:
    """Schedule a list of tasks to be executed in a thread pool"""

    tasks: list[Task]
    cv: threading.Condition
    error: Optional[BaseException]

    def __init__(self, tasks):
        self.tasks = tasks
        self.cv = threading.Condition()
        self.error = None

    def run(self):
        poolsize = multiprocessing.cpu_count()
        threads = [threading.Thread(target=self.run_thread)
                   for _ in range(poolsize)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        if self.error is not None:
            raise self.error

    def run_thread(self):
        while (task := self.acquire_next_task()) is not None:
            try:
                task.run()
            except TaskException as e:
                task.failed = True
                print(f'\033[31m{e}\033[0m')
            finally:
                task.running = False
                task.complete = True
                with self.cv:
                    self.cv.notify_all()

    def acquire_next_task(self):
        with self.cv:
            while any(not t.complete for t in self.tasks):
                if self.error is not None:
                    return None

                task = self.next_task()
                if task is not None:
                    task.running = True
                    return task
                else:
                    self.cv.wait()
            return None

    def next_task(self):
        try:
            task = next(t for t in self.tasks
                        if not t.running and not t.complete and t.is_ready())
            return task
        except StopIteration:
            return None
