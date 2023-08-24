import time
import sqlite3

from pytest_flakefriend.base import Base


FILES = {"foo.py", "bar.py"}

FUNCS = {
    ("foo.py", 1, "test_foo1"), ("foo.py", 2, "test_foo2"),
    ("bar.py", 3, "test_bar1")
}


class MockCode:
    def __init__(self, file, line, func_name):
        self.co_filename = file
        self.co_firstlineno = line
        self.co_name = func_name


class MockObj:
    def __init__(self, code):
        if code is not None: self.__code__ = code
        self.called = False

    def __call__(self, *args, **kwargs):
        self.called = True
        raise Exception


class MockItem:
    def __init__(self, obj, test_name):
        if obj is not None: self.obj = obj
        self.nodeid = test_name


def test_filter_items():
    items = [
        MockItem(None, "test1"), 
        MockItem(MockObj(None), "test2"), 
        MockItem(MockObj(MockCode(None, None, None)), "test3"), 
        MockItem(MockObj(MockCode("foo.py", 1, "test4")), "test4"),
        MockItem(MockObj(MockCode("foo.py", 2, "test5")), "test5[a]"),
        MockItem(MockObj(MockCode("foo.py", 2, "test5")), "test5[b]"),
    ]

    plugin = Base(None, None, None)
    assert list(plugin.filter_items(items)) == items[3:]
    assert plugin.files == {"foo.py"}
    assert plugin.funcs == {("foo.py", 1, "test4"), ("foo.py", 2, "test5")}


def test_save(db_file, monkeypatch):
    plugin = Base(db_file, 1, 1)
    plugin.files = FILES
    plugin.funcs = FUNCS
    plugin.mode = 0
    plugin.start_time = 0
    monkeypatch.setattr(time, "perf_counter", lambda: 10)

    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        plugin.save(cur)
        cur.execute("select * from file")

        assert set(cur.fetchall()) == {
            (plugin.file_to_id["foo.py"], "foo.py"),
            (plugin.file_to_id["bar.py"], "bar.py")
        }

        cur.execute("select * from function")

        assert set(cur.fetchall()) == {
            (
                plugin.get_func_id("foo.py", 1), plugin.file_to_id["foo.py"], 
                1, "test_foo1"
            ),
            (
                plugin.get_func_id("foo.py", 2), plugin.file_to_id["foo.py"], 
                2, "test_foo2"
            ),
            (
                plugin.get_func_id("bar.py", 3), plugin.file_to_id["bar.py"], 
                3, "test_bar1"
            )
        }

        cur.execute("select * from record")
        assert cur.fetchall() == [(1, 1, 0, 10)]