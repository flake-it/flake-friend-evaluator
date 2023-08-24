import time
import sqlite3

import psutil
import pytest


def get_code_info(code): 
    return code.co_filename, code.co_firstlineno, code.co_name


class Base:
    def __init__(self, db_file, repo_id, machine_id):
        self.db_file = db_file
        self.repo_id = repo_id
        self.machine_id = machine_id
        self.files = set()
        self.funcs = set()
        self.start_time = time.perf_counter()

    def filter_items(self, items):
        for item in items:
            try: code = item.obj.__code__
            except AttributeError: continue
            info = get_code_info(code)
            if not all(info): continue
            self.files.add(info[0])
            self.funcs.add(info)
            yield item

    def get_func_id(self, file, line):
        return self.func_to_id[(self.file_to_id[file], line)]

    def save(self, cur):
        cur.executemany(
            "insert or ignore into file values (null, ?)", 
            [(file,) for file in self.files]
        )

        cur.execute("select file, id from file")
        self.file_to_id = dict(cur.fetchall())

        cur.executemany(
            "insert or ignore into function values (null, ?, ?, ?)",
            [
                (self.file_to_id[file], line, func_name) 
                for file, line, func_name in self.funcs
            ]
        )

        cur.execute("select file_id, line, id from function")

        self.func_to_id = {
            tuple(func): func_id for *func, func_id in cur.fetchall()
        }

        elapsed_time = time.perf_counter() - self.start_time

        cur.execute(
            "insert or replace into record values (?, ?, ?, ?)", 
            (self.repo_id, self.machine_id, self.mode, elapsed_time)
        )

    def finish(self):
        with sqlite3.connect(self.db_file, timeout=3600) as con:
            cur = con.cursor()
            cur.execute("begin exclusive")
            self.save(cur)

        pytest.exit("finished", 0)