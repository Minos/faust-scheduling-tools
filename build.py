from __future__ import annotations

import multiprocessing
import os
import subprocess
import threading

import common


def build_benchmarks(
    dsp, *,
    strategies=common.strategies,
    compilers=common.compilers,
    archs=common.archs
):
    tasks: list[Task] = []

    for s in strategies:
        faust_task = FaustBenchTask(dsp, s)
        tasks += [faust_task]

        cpp_tasks = [CppBenchTask(dsp, s, c, a, deps=[faust_task])
                     for c in compilers for a in archs]
        tasks += cpp_tasks

    make_build_dir(dsp)
    scheduler = BuildScheduler(tasks)
    scheduler.run()


def build_tests(dsp_list, *, strategies=common.strategies):
    tasks: list[Task] = []

    for dsp in dsp_list:
        make_build_dir(dsp)
        for s in strategies:
            faust_task = FaustTestTask(dsp, s)
            tasks += [faust_task]

            cpp_task = CppTestTask(dsp, s, deps=[faust_task])
            tasks += [cpp_task]

    scheduler = BuildScheduler(tasks)
    scheduler.run()


def make_build_dir(dsp):
    os.makedirs(build_dir(*split_prog_name(dsp)), mode=0o755, exist_ok=True)


def split_prog_name(dsp):
    directory, file = os.path.split(dsp)
    prog, _ = os.path.splitext(file)
    return directory, prog


def build_dir(directory, prog_name):
    return os.path.join(directory, f"{prog_name}.{common.build_dir_ext}")


def bench_cpp_file(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name), f"{prog_name}_ss{strategy}_bench.cpp")


def bench_binary(directory, prog_name, strategy, compiler, arch):
    return os.path.join(build_dir(directory, prog_name), f"{prog_name}_ss{strategy}_bench_{compiler}_{arch}")


def test_cpp_file(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name), f"{prog_name}_ss{strategy}_test.cpp")


def test_binary(directory, prog_name, strategy):
    return os.path.join(build_dir(directory, prog_name), f"{prog_name}_ss{strategy}_test")


class TaskException(BaseException):
    def __init__(self, task, process):
        self.task = task
        self.process = process

    def __str__(self):
        command = " ".join(self.task.command())
        return f"Error building {self.task.product}:\n{command}\n{self.process.stderr}"


class Task:
    sources: list[str]
    product: str
    deps: list[Task]
    running: bool
    complete: bool

    def __init__(self, sources: list[str], product: str, deps: list[Task] = []):
        self.sources = sources
        self.product = product
        self.deps = deps
        self.running = False
        self.complete = self.is_up_to_date()

    def is_up_to_date(self) -> bool:
        if not os.path.exists(self.product):
            return False
        for s in self.sources:
            if not os.path.exists(s):
                return False
            if os.path.getmtime(s) > os.path.getmtime(self.product):
                return False
        return self.is_ready()

    def is_ready(self) -> bool:
        return all(d.complete for d in self.deps)

    def run(self):
        self.print_info()
        # debug = ' '.join(self.command())
        # print(f"\033[2m{debug}\033[22m")
        process = subprocess.run(self.command(), capture_output=True, text=True)
        if process.returncode:
            raise TaskException(self, process)

    def dependencies(self) -> list[str]:
        return self.sources

    def command(self) -> list[str]:
        raise Exception("Not implemented")

    def print_info(self):
        pass


class FaustTask(Task):
    arch: str
    prog: str
    strategy: str

    def __init__(self, src, arch, strategy, output):
        _, self.prog = split_prog_name(src)
        self.arch = arch
        self.strategy = strategy

        super(FaustTask, self).__init__([src], output)

    def dependencies(self):
        return super(FaustTask, self).dependencies() + [self.arch]

    def command(self):
        return [common.find_faust(),
                "-a", self.arch,
                "-lang", common.faust_lang,
                "-ss", self.strategy,
                "-o", self.product,
                self.sources[0]]

    def print_info(self):
        print(f"  FAUST  {self.prog} [strategy {self.strategy}]")


class FaustBenchTask(FaustTask):
    def __init__(self, src, strategy):
        super(FaustBenchTask, self).__init__(
                src, 
                common.faust_bencharch, 
                strategy, 
                bench_cpp_file(*split_prog_name(src), strategy)
        )


class FaustTestTask(FaustTask):
    def __init__(self, src, strategy):
        super(FaustTestTask, self).__init__(
                src, 
                common.faust_testarch, 
                strategy, 
                test_cpp_file(*split_prog_name(src), strategy)
        )


class CppBenchTask(Task):
    def __init__(self, dsp, strategy, compiler, arch, deps):
        directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy
        self.compiler = compiler
        self.arch = arch

        super(CppBenchTask, self).__init__(
            [bench_cpp_file(directory, self.prog, strategy)],
            bench_binary(directory, self.prog, strategy, compiler, arch),
            deps=deps
        )

    def command(self):
        return [self.compiler,
                f"-march={self.arch}",
                "-O3", "-ffast-math", "--std=c++20",
                "-lpfm",
                self.sources[0],
                "-o", self.product]

    def print_info(self):
        print(f"  CC     {self.prog} [strategy {self.strategy}, "
              f"{self.compiler}, {self.arch}]")


class CppTestTask(Task):
    def __init__(self, dsp, strategy, deps):
        directory, self.prog = split_prog_name(dsp)
        self.strategy = strategy

        super(CppTestTask, self).__init__(
            [test_cpp_file(directory, self.prog, strategy)],
            test_binary(directory, self.prog, strategy),
            deps=deps
        )

    def command(self):
        return [common.clang, "-march=native", "-O0", self.sources[0], "-o", self.product]

    def print_info(self):
        print(f"  CC     {self.prog} [strategy {self.strategy}]")



class BuildScheduler:
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
                task.complete = True
            except BaseException as e:
                self.error = e
            finally:
                with self.cv:
                    self.cv.notify_all()

    def acquire_next_task(self):
        with self.cv:
            while any(not t.complete for t in self.tasks):
                if self.error is not None:
                    break

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
