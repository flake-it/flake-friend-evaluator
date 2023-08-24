import time
import multiprocessing as mp

import psutil

from pytest_flakefriend.dynamic import Dynamic


def get_noncumulative_metrics(proc, nc_metrics_prev):
    threads = proc.num_threads()
    children = len(proc.children())
    memory = proc.memory_full_info().uss
    nc_metrics = threads, children, memory
    if nc_metrics_prev is None: return nc_metrics
    return [max(x, y) for x, y in zip(nc_metrics, nc_metrics_prev)]


class DynamicMetrics(Dynamic):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 2
        self.test_start = mp.Event()
        self.test_stop = mp.Event()
        self.dynamic_metrics = []

    def manage_child(self, item, proc):
        waited = False
        nc_metrics = None

        while not self.test_start.wait(5):
            try: proc.wait(0)
            except psutil.TimeoutExpired: continue
            waited = True
            break

        if not waited:
            timeout = 0

            while not self.test_stop.wait(timeout):
                try: nc_metrics = get_noncumulative_metrics(proc, nc_metrics)
                except psutil.NoSuchProcess: break
                timeout = 0.025

            self.receive_data(proc)

        self.test_start.clear()
        self.test_stop.clear()
        if nc_metrics is None: return False

        try:
            cu_metrics = self.data["cu_metrics"]
            covered_lines = self.data["covered_lines"]
        except KeyError:
            return False

        dy_metrics = cu_metrics, covered_lines, nc_metrics
        self.dynamic_metrics.append((item.nodeid, *dy_metrics))
        return True

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or replace into dynamic_metrics values "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    self.test_to_id[test_name], self.machine_id, self.mode,
                    *cu_metrics, covered_lines, *nc_metrics
                )
                for test_name, cu_metrics, covered_lines, nc_metrics 
                in self.dynamic_metrics
            ]
        )

    def pre_call(self):
        super().pre_call()
        self.test_start.set()

    def get_covered_lines(self):
        return None

    def post_call(self):
        super().post_call()
        self.test_stop.set()
        self.data["covered_lines"] = self.get_covered_lines()

    def child_finish(self):
        super().child_finish()
        if not self.test_stop.is_set(): self.test_stop.set()
        if not self.test_start.is_set(): self.test_start.set()