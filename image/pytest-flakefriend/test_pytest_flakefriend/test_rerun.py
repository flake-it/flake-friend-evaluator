import time
import sqlite3

from pytest_flakefriend.rerun import Rerun
from test_pytest_flakefriend.test_dynamic import TESTS
from test_pytest_flakefriend.test_base import FILES, FUNCS


def test_save(db_file):
    rerun = Rerun(db_file, 1, 1)
    rerun.files = FILES
    rerun.funcs = FUNCS
    rerun.tests = TESTS

    rerun.test_runs = [
        ("test_foo1", "error1", [0] * 7), ("test_foo2", None, [1] * 7)
    ]

    with sqlite3.connect(db_file) as con: rerun.save(con.cursor())
    rerun.machine_id = 2

    rerun.test_runs = [
        ("test_foo1", "error1", [2] * 7), 
        ("test_foo2", "error2", [3] * 7)
    ]

    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        rerun.save(cur)
        cur.execute("select exception, id from exception")
        exception_to_id = dict(cur.fetchall())
        assert set(exception_to_id) == {"error1", "error2"}
        cur.execute("select * from test_run")

        assert set(cur.fetchall()) == {
            (
                rerun.test_to_id["test_foo1"], 1, exception_to_id["error1"], 
                *[0] * 7
            ),
            (
                rerun.test_to_id["test_foo2"], 1, None, *[1] * 7
            ),
            (
                rerun.test_to_id["test_foo1"],  2, exception_to_id["error1"], 
                *[2] * 7
            ),
            (
                rerun.test_to_id["test_foo2"], 2, exception_to_id["error2"], 
                *[3] * 7
            )
        }