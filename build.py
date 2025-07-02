from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional, List, Dict

import csv
import hashlib
import multiprocessing
import os
import subprocess
import threading

from numpy.typing import NDArray
import numpy

from perf import PerfEvent


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FAUST_ARCH = os.path.join(ROOT_DIR, 'arch/mydsp.cpp')

BENCH_BINARY = 'schedrun'
TEST_BINARY = 'schedprint'


class Scheduling(StrEnum):
    DEEP_FIRST = '0'
    BREADTH_FIRST = '1'
    INTERLEAVED = '2'
    REVERSE_BREADTH_FIRST = '3'
    LIST_SCHEDULING = '4'

    @staticmethod
    def default() -> Scheduling:
        return Scheduling.DEEP_FIRST

    @staticmethod
    def all() -> List[Scheduling]:
        return list(Scheduling)


class Compiler(StrEnum):
    CLANG = 'clang++'
    GCC = 'g++'

    @staticmethod
    def default() -> Compiler:
        return Compiler.CLANG

    @staticmethod
    def all() -> List[Compiler]:
        return list(Compiler)


class Architecture(StrEnum):
    NATIVE = 'native'
    X86_64 = 'x86-64'

    @staticmethod
    def default() -> Architecture:
        return Architecture.NATIVE

    @staticmethod
    def all() -> List[Architecture]:
        return list(Architecture)


class BenchType(StrEnum):
    BASIC = 'basic'
    ALSA = 'alsa'
    JACK = 'jack'

    @staticmethod
    def default() -> BenchType:
        return BenchType.BASIC

    @staticmethod
    def all() -> List[BenchType]:
        return list(BenchType)

    def run_opt(self) -> str:
        return f'--{self.value}'


@dataclass(frozen=True)
class FaustProgram:
    src: str
    directory: str
    name: str

    def __init__(self, src: str):
        directory, filename = os.path.split(src)
        name, _ = os.path.splitext(filename)

        object.__setattr__(self, 'src', src)
        object.__setattr__(self, 'directory', directory)
        object.__setattr__(self, 'name', name)

    def build_directory(self) -> str:
        return os.path.join(self.directory, f'{self.name}.fcsched')

    def make_build_directory(self):
        os.makedirs(self.build_directory(), mode=0o755, exist_ok=True)

    def cpp_path(self, faust_strategy: FaustStrategy) -> str:
        return os.path.join(self.build_directory(),
                            f'{self.name}_{faust_strategy.suffix()}.cpp')

    def test_path(self, faust_strategy: FaustStrategy) -> str:
        return os.path.join(self.build_directory(),
                            f'{self.name}_{faust_strategy.suffix()}_test.so')

    def benchmark_path(self,
                       faust_strategy: FaustStrategy,
                       compilation_strategy: CompilationStrategy) -> str:
        return os.path.join(self.build_directory(),
                            f'{self.name}_{faust_strategy.suffix()}'
                            f'_bench_{compilation_strategy.suffix()}.so')

    def benchmark_output_path(self,
                              faust_strategy: FaustStrategy,
                              compilation_strategy: CompilationStrategy,
                              run_hash: str) -> str:
        return os.path.join(self.build_directory(),
                            f'{self.name}_{faust_strategy.suffix()}'
                            f'_bench_{compilation_strategy.suffix()}'
                            f'.{run_hash}.csv')


@dataclass(frozen=True)
class FaustStrategy:
    scheduling: Scheduling

    @staticmethod
    def all() -> List[FaustStrategy]:
        return [FaustStrategy(scheduling)
                for scheduling in Scheduling.all()]

    def suffix(self) -> str:
        return f'ss{self.scheduling.value}'

    def __str__(self):
        return f'strategy {self.scheduling.value}'


@dataclass(frozen=True)
class CompilationStrategy:
    compiler: Compiler
    architecture: Architecture

    @staticmethod
    def all() -> List[CompilationStrategy]:
        return [CompilationStrategy(compiler, architecture)
                for compiler in Compiler.all()
                for architecture in Architecture.all()]

    def suffix(self) -> str:
        return f'{self.compiler.value}_{self.architecture.value}'

    def __str__(self):
        return f'{self.compiler.value}, {self.architecture.value}'


@dataclass
class RunException(BaseException):
    cmd: List[str]
    process: subprocess.CompletedProcess

    def __str__(self):
        return (
            f'Execution failed with return code '
            f'{self.process.returncode}:\n'
            f'{" ".join(self.cmd)}\n'
            f'{self.process.stderr}'
        )


@dataclass
class FaustTest:
    program: FaustProgram
    faust_strategies: List[FaustStrategy] = field(default_factory=FaustStrategy.all)

    def path(self, faust_strategy: FaustStrategy) -> str:
        return self.program.test_path(faust_strategy)


@dataclass
class FaustTestRun:
    test: FaustTest

    def run(self) -> FaustTestResult:
        outputs = {c: self.get_output(c) for c in self.test.faust_strategies}
        return FaustTestResult(self.test, outputs)

    def get_output(self, codegen: FaustStrategy) -> NDArray:
        cmd = [os.path.join(ROOT_DIR, TEST_BINARY), self.test.path(codegen)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        if proc.stdout is None:
            raise BaseException(f'Unexpected null stdout while calling f{" ".join(cmd)}')

        reader = csv.reader(proc.stdout, delimiter=';')
        response = []
        for line in reader:
            response.append(line)
        return numpy.array(response, dtype=numpy.float32).T


@dataclass
class FaustTestResult:
    test: FaustTest
    outputs: Dict[FaustStrategy, NDArray]


@dataclass
class FaustBenchmark:
    program: FaustProgram

    faust_strategies: List[FaustStrategy] = \
            field(default_factory=FaustStrategy.all)

    compilation_strategies: List[CompilationStrategy] = \
            field(default_factory=CompilationStrategy.all)    

    loops: int = 100
    events: List[PerfEvent] = field(default_factory=list)
    bench_type: BenchType = field(default_factory=BenchType.default)

    override: bool = False

    def path(self,
             faust_strategy: FaustStrategy,
             compilation_strategy: CompilationStrategy) -> str:
        return self.program.benchmark_path(faust_strategy, compilation_strategy)

    def run(self) -> List[FaustBenchmarkResult]:
        runs = [FaustBenchmarkRun(self, f, c, self.loops, self.events, self.bench_type)
                for f in self.faust_strategies
                for c in self.compilation_strategies]
        return [r.run(override=self.override) for r in runs]


@dataclass
class FaustBenchmarkRun:
    benchmark: FaustBenchmark
    faust_strategy: FaustStrategy
    compilation_strategy: CompilationStrategy

    loops: int
    events: List[PerfEvent]
    bench_type: BenchType = BenchType.BASIC

    def csv_path(self) -> str:
        measures = f'events: {sorted(self.events)}, nloops: {self.loops}, ' \
                   f'type: {self.bench_type.value}'
        run_hash = hashlib.sha1(measures.encode('utf-8')).hexdigest()[:8]
        return self.benchmark.program.benchmark_output_path(
                self.faust_strategy,
                self.compilation_strategy,
                run_hash)

    def shared_object_path(self) -> str:
        return self.benchmark.program.benchmark_path(
                self.faust_strategy,
                self.compilation_strategy)

    def run(self, *, override=False) -> FaustBenchmarkResult:
        output = self.csv_path()
        binary_path = os.path.join(ROOT_DIR, BENCH_BINARY)
        shared_object_path = self.shared_object_path()
        if not override \
                and os.path.exists(output) \
                and os.path.getmtime(output) > os.path.getmtime(shared_object_path):
            return self.parse_output()

        print(f'RUN    {self.benchmark.program.src} '
              f'[{self.faust_strategy}, {self.compilation_strategy}]')

        cmd = [binary_path,
               shared_object_path,
               self.bench_type.run_opt(),
               '-r',
               '-o', output,
               '-n', str(self.loops)]

        if len(self.events) > 0:
            cmd += ['-e', ','.join(self.events)]

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise RunException(cmd, proc)

        return self.parse_output()

    def parse_output(self) -> FaustBenchmarkResult:
        with open(self.csv_path()) as output:
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

            times = numpy.array(events[0])
            events_dict = {PerfEvent(k): numpy.array(events[i+1]) 
                           for i, k in enumerate(header[1:])}

            return FaustBenchmarkResult(self, loops, events_dict, times)


@dataclass
class FaustBenchmarkResult:
    run: FaustBenchmarkRun
    loops: int
    events: dict[PerfEvent, NDArray]
    times: NDArray


class FaustTestingPlan:
    programs: List[FaustProgram]
    scheduling_strategies: List[Scheduling]

    def __init__(self,
                 programs: List[FaustProgram],
                 scheduling_strategies: List[Scheduling] = Scheduling.all()):
        self.programs = programs
        self.scheduling_strategies = scheduling_strategies

    def build(self) -> List[FaustTest]:
        tests: List[FaustTest] = []
        tasks: List[Task] = []

        make(TEST_BINARY)

        for program in self.programs:
            program.make_build_directory()

            faust_strategies = [FaustStrategy(s) for s in self.scheduling_strategies]
            test = FaustTest(program, faust_strategies)
            tests.append(test)

            for faust_strategy in faust_strategies:
                faust_task = FaustTask(program, faust_strategy)
                tasks.append(faust_task)
                tasks.append(FaustTestTask(test, faust_task))

        scheduler = BuildScheduler(tasks)
        scheduler.run()

        # Remove failed tasks from the test so the plan can still go on with the others
        for task in tasks:
            if task.failed:
                if isinstance(task, FaustTask):
                    for t in tests:
                        if t.program != task.program:
                            continue
                        t.faust_strategies = [s for s in t.faust_strategies
                                              if s != task.strategy]
                elif isinstance(task, FaustTestTask):
                    for t in tests:
                        if t.program != task.test.program:
                            continue
                        t.faust_strategies = [s for s in t.faust_strategies 
                                              if s != task.faust_strategy]

        return tests

    def run(self) -> List[FaustTestResult]:
        tests = self.build()
        runs = [FaustTestRun(t) for t in tests]
        return [r.run() for r in runs]


class FaustBenchmarkingPlan:
    programs: List[FaustProgram]
    scheduling_strategies: List[Scheduling]

    compilers: List[Compiler]
    architectures: List[Architecture]

    loops: int
    events: List[PerfEvent]
    bench_type: BenchType

    override: bool

    def __init__(self,
                 programs: List[FaustProgram],
                 scheduling_strategies: List[Scheduling] = Scheduling.all(),
                 compilers: List[Compiler] = [Compiler.default()],
                 architectures: List[Architecture] = [Architecture.default()],
                 loops: int = 100,
                 events: List[PerfEvent] = [],
                 bench_type: BenchType = BenchType.default(),
                 override: bool = False):
        self.programs = programs
        self.scheduling_strategies = scheduling_strategies
        self.compilers = compilers
        self.architectures = architectures
        self.loops = loops
        self.events = events
        self.bench_type = bench_type
        self.override = override

    def build(self) -> List[FaustBenchmark]:
        benchmarks: List[FaustBenchmark] = []
        tasks: List[Task] = []

        make(BENCH_BINARY)

        for program in self.programs:
            program.make_build_directory()

            faust_strategies = [FaustStrategy(s) for s in self.scheduling_strategies]
            compilation_strategies = [CompilationStrategy(compiler, architecture)
                                      for compiler in self.compilers
                                      for architecture in self.architectures]

            benchmark = FaustBenchmark(program, faust_strategies, compilation_strategies,
                                       self.loops, self.events, self.bench_type, self.override)
            benchmarks.append(benchmark)

            for faust_strategy in faust_strategies:
                faust_task = FaustTask(program, faust_strategy)
                tasks.append(faust_task)

                for compilation_strategy in compilation_strategies:
                    tasks.append(FaustBenchmarkTask(benchmark, faust_task, compilation_strategy))

        scheduler = BuildScheduler(tasks)
        scheduler.run()

        # Remove failed tasks from the test so the plan can still go on with the others
        for task in tasks:
            if task.failed:
                if isinstance(task, FaustTask):
                    for b in benchmarks:
                        if b.program != task.program:
                            continue
                        b.faust_strategies = [s for s in b.faust_strategies
                                              if s != task.strategy]
                elif isinstance(task, FaustBenchmarkTask):
                    for b in benchmarks:
                        if b.program != task.benchmark.program:
                            continue
                        b.faust_strategies = [s for s in b.faust_strategies 
                                              if s != task.faust_strategy]

        benchmarks = [b for b in benchmarks if len(b.faust_strategies) > 0]

        return benchmarks

    def run(self) -> List[FaustBenchmarkResult]:
        benchmarks = self.build()
        runs = [FaustBenchmarkRun(b, f, c, self.loops, self.events, self.bench_type) 
                for b in benchmarks
                for f in b.faust_strategies
                for c in b.compilation_strategies]
        return [r.run(override=self.override) for r in runs]


def faust_executable():
    try:
        prefix = os.environ['FAUST_PREFIX']
        return os.path.join(prefix, 'build/bin/faust')
    except KeyError:
        return 'faust'


def make(target: str):
    subprocess.call(['make',
                     f'-C{ROOT_DIR}',
                     '--silent',
                     f'-j{multiprocessing.cpu_count()}',
                     target])


@dataclass
class TaskException(BaseException):
    task: Task


@dataclass
class RecordedTaskException(TaskException):
    def __str__(self):
        return f'Not rebuilding {self.task.product} due to recorded previous error.'


@dataclass
class TaskRunException(TaskException):
    task: Task
    process: subprocess.CompletedProcess

    def __str__(self):
        command = ' '.join(self.task.command())
        return f'Error building {self.task.product}:\n{command}\n{self.process.stderr}'


@dataclass
class TaskDependencyException(TaskException):
    dependency: Task

    def __str__(self):
        return f'{self.task.product} could not be built because it depends on ' \
               f'{self.dependency}, which failed to build.'


class Task:
    """Base class for any build task

    Attributes:
        deps -- list of tasks this task depends on
        sources -- list of source files for this tasks that are not produced by
                   the dependencies
        product -- product file for this task
    """
    sources: List[str]
    product: str
    dependencies: List[Task]

    complete: bool = False
    running: bool = False
    failed: bool = False

    def __init__(self, sources: List[str], product: str, dependencies: List[Task] = []):
        self.sources = sources
        self.product = product
        self.dependencies = dependencies

    def is_ready(self) -> bool:
        return all(d.complete for d in self.dependencies)

    def is_up_to_date(self) -> bool:
        """
        Returns True iff this tasks's product exists and is newer than all its
        sources, and all the dependencies have been completed
        """
        if not os.path.exists(self.product):
            return False
        for s in self.sources + self.extra_dependencies():
            if not os.path.exists(s):
                return False
            if os.path.getmtime(s) > os.path.getmtime(self.product):
                return False
        return True

    def run(self):
        if self.is_up_to_date():
            return

        for d in self.dependencies:
            if d.failed:
                raise TaskDependencyException(self, d)

        recorded_error = f'{self.product}.failure'
        if os.path.exists(recorded_error) and \
                all(os.path.exists(s) and 
                    os.path.getmtime(s) < os.path.getmtime(recorded_error)
                    for s in self.sources + self.extra_dependencies()):
            raise RecordedTaskException(self)

        """Run the task"""
        self.print_info()
        # print(f'\033[2m{" ".join(self.command())}\033[22m')
        process = subprocess.run(self.command(), capture_output=True, text=True)
        if process.returncode:
            with open(recorded_error, 'w') as f:
                f.write(process.stderr)
            raise TaskRunException(self, process)
        elif os.path.exists(recorded_error):
            # Remove previously recorded error in case of success
            os.remove(recorded_error)

    def extra_dependencies(self) -> List[str]:
        return []

    def command(self) -> List[str]:
        raise Exception('Not implemented')

    def print_info(self):
        pass


class FaustTask(Task):
    """A task that compiles a FAUST program into C++ generated code

    Attributes:
    code -- The FAUST code generation to process
    """

    program: FaustProgram
    strategy: FaustStrategy

    def __init__(self, program: FaustProgram, strategy: FaustStrategy):
        self.program = program
        self.strategy = strategy

        super(FaustTask, self).__init__([program.src], program.cpp_path(strategy))

    def extra_dependencies(self):
        return [FAUST_ARCH, faust_executable()]

    def command(self):
        return [faust_executable(),
                '-a', FAUST_ARCH,
                '-lang', 'ocpp',
                # '-sg', # Print signal graph
                '-ss', self.strategy.scheduling,
                '-o', self.product,
                self.sources[0]]

    def print_info(self):
        print(f'FAUST  {self.program.src} [strategy {self.strategy.scheduling}]')

    def run(self):
        # Faust sometimes outputs an empty C++ file upon failure. It's better
        # to delete it, otherwise the next run will consider this file as
        # valid and try to compile it.
        try:
            super(FaustTask, self).run()
        except TaskRunException as err:
            if os.path.exists(self.product):
                os.remove(self.product)
            raise err


class FaustTestTask(Task):
    """Compile a C++ dsp into a C++ object file for testing"""

    test: FaustTest
    faust_strategy: FaustStrategy

    def __init__(self, test: FaustTest, faust_task: FaustTask):
        self.test = test
        self.faust_strategy = faust_task.strategy

        super(FaustTestTask, self).__init__(
                [test.program.cpp_path(self.faust_strategy)],
                test.path(self.faust_strategy),
                [faust_task])

    def command(self):
        return [Compiler.default(),
                f'-march=native', '-O0',
                f'-I{self.test.program.directory}', f'-I{ROOT_DIR}/arch',
                self.sources[0],
                '-shared', '-fPIC', '-o', self.product]

    def print_info(self):
        print(f'CXX    {self.test.program.src} '
              f'[strategy {self.faust_strategy.scheduling}]')


class FaustBenchmarkTask(Task):
    """Compile a C++ dsp into a C++ object file for benchmarking"""

    benchmark: FaustBenchmark
    faust_strategy: FaustStrategy
    compilation_strategy: CompilationStrategy

    def __init__(self, benchmark: FaustBenchmark, faust_task: FaustTask,
                 compilation_strategy: CompilationStrategy):
        self.benchmark = benchmark
        self.faust_strategy = faust_task.strategy
        self.compilation_strategy = compilation_strategy

        super(FaustBenchmarkTask, self).__init__(
            [benchmark.program.cpp_path(self.faust_strategy)],
            benchmark.path(self.faust_strategy, compilation_strategy),
            [faust_task])

    def command(self):
        return [self.compilation_strategy.compiler,
                f'-march={self.compilation_strategy.architecture}',
                '-O3', '-ffast-math', '--std=c++20',
                f'-I{self.benchmark.program.directory}', f'-I{ROOT_DIR}/arch',
                self.sources[0],
                '-shared', '-fPIC', '-o', self.product]

    def print_info(self):
        print(f'CXX    {self.benchmark.program.src} '
              f'[{self.faust_strategy}, {self.compilation_strategy}]')


class BuildScheduler:
    """Schedule a list of tasks to be executed in a thread pool"""

    tasks: List[Task]
    cv: threading.Condition
    error: Optional[BaseException]

    def __init__(self, tasks):
        self.tasks = tasks
        self.cv = threading.Condition()
        self.error = None

    def run(self, *, poolsize=multiprocessing.cpu_count()):
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
