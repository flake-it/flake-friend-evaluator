import os

from pytest_flakefriend.dynamic import Dynamic


class Rerun(Dynamic):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 0
        self.test_runs = []

    def manage_child(self, item, proc):
        self.receive_data(proc)
        
        try:
            exception = self.data["exception"]
            cu_metrics = self.data["cu_metrics"]
        except KeyError:
            return False

        self.test_runs.append((item.nodeid, exception, cu_metrics))
        return True

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or ignore into exception values (null, ?)", 
            [(exception,) for _, exception, _ in self.test_runs if exception]
        )

        cur.execute("select exception, id from exception")
        exception_to_id = dict(cur.fetchall())

        cur.executemany(
            "insert or replace into test_run values "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            [
                (
                    self.test_to_id[test_name], self.machine_id, 
                    exception_to_id[exception] if exception else None, 
                    *cu_metrics
                )
                for test_name, exception, cu_metrics in self.test_runs
            ]
        )

    def pre_call(self):
        super().pre_call()
        self.exception = None

    def on_exception(self, e):
        super().on_exception(e)
        self.exception = str(e)

    def post_call(self):
        super().post_call()
        self.data["exception"] = self.exception