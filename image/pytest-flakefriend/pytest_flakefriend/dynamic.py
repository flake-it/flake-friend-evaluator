import gc
import os
import time
import multiprocessing as mp

import psutil
import pytest

from pytest_flakefriend.base import Base, get_code_info


def get_cumulative_metrics(cu_metrics_prev=None):
    proc = psutil.Process()
    cpu_times = proc.cpu_times()
    io_counters = proc.io_counters()
    num_ctx_switches = proc.num_ctx_switches()

    cu_metrics = (
        time.perf_counter(), cpu_times.user, cpu_times.system, 
        cpu_times.iowait, io_counters.read_count, io_counters.write_count,
        num_ctx_switches.voluntary
    )

    if cu_metrics_prev is None: return cu_metrics
    return [x - y for x, y in zip(cu_metrics, cu_metrics_prev)]


class Dynamic(Base):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.data = {}
        self.tests = []
        gc.disable()

    def receive_data(self, proc):
        waited = False

        while not waited:
            try: 
                proc.wait(0)
            except psutil.TimeoutExpired: 
                if self.recv_conn.poll(5): break
                else: continue
                
            waited = True

        self.data = self.recv_conn.recv() if self.recv_conn.poll() else {}
        if not waited: proc.wait()

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or ignore into test values (null, ?, ?, ?)", 
            [
                (self.repo_id, test_name, self.get_func_id(file, line))
                for test_name, file, line  in self.tests
            ]
        )

        cur.execute(
            "select name, id from test where repository_id = ?", 
            (self.repo_id,)
        )

        self.test_to_id = dict(cur.fetchall())

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        self.recv_conn, self.send_conn = mp.Pipe(False)

        for item in self.filter_items(items):
            gc.freeze()
            pid = os.fork()

            if pid == 0:
                gc.enable()
                items[:] = [item]
                return

            if self.manage_child(item, psutil.Process(pid)):
                code = item.obj.__code__
                file = code.co_filename
                line = code.co_firstlineno
                self.tests.append((item.nodeid, file, line))

        self.finish()

    def pre_call(self):
        self.cu_metrics = get_cumulative_metrics()

    def on_exception(self, e): 
        pass

    def post_call(self):
        self.data["cu_metrics"] = get_cumulative_metrics(self.cu_metrics)

    def instrumented_obj(self, *args, **kwargs):
        self.pre_call()

        try:
            self.original_obj(*args, **kwargs)
        except Exception as e:
            self.on_exception(e)
            raise e
        finally:
            self.post_call()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_pyfunc_call(self, pyfuncitem):
        self.original_obj = pyfuncitem.obj
        pyfuncitem.obj = self.instrumented_obj

        try:
            outcome = yield
            outcome.get_result()
        finally:
            pyfuncitem.obj = self.original_obj

    def child_start(self, item):
        pass

    def child_finish(self):
        pass

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        self.data = {}
        self.child_start(item)
        yield
        self.child_finish()
        self.send_conn.send(self.data)
        os._exit(0)