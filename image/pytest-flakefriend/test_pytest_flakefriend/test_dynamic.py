import sqlite3

import pytest
import psutil

from pytest_flakefriend.dynamic import Dynamic
from test_pytest_flakefriend.test_base import FILES, FUNCS, MockItem, MockObj


DATA = {"foo": "bar"}

TESTS = [
    ("test_foo1", "foo.py", 1), ("test_foo2", "foo.py", 2),
    ("test_bar1[a]", "bar.py", 3), ("test_bar1[b]", "bar.py", 3)
]


class MockConnection:
    def __init__(self, received, sent, data):
        self.received = received
        self.sent = sent
        self.data = data

    def poll(self, timeout=None):
        return self.sent

    def recv(self):
        self.received = True
        return self.data

    def send(self, data):
        self.sent = True
        self.data = data


class MockProcess:
    def __init__(self, finished):
        self.finished = finished
        self.waited = False
 
    def wait(self, timeout=None):
        if not self.finished and timeout is not None: 
            self.finished = True
            raise psutil.TimeoutExpired(timeout)

        self.waited = True
        return 0


@pytest.mark.parametrize(
    "recv_conn,proc,received,data",
    [
        (MockConnection(False, False, DATA), MockProcess(True), False, {}),
        (MockConnection(False, False, DATA), MockProcess(False), False, {}),
        (MockConnection(False, True, DATA), MockProcess(True), True, DATA),
        (MockConnection(False, True, DATA), MockProcess(False), True, DATA)
    ]
)
def test_receive_data(recv_conn, proc, received, data):
    plugin = Dynamic(None, None, None)
    plugin.recv_conn = recv_conn
    plugin.receive_data(proc)
    assert recv_conn.received == received
    assert proc.waited
    assert plugin.data == data


def test_save(db_file, monkeypatch):
    plugin = Dynamic(db_file, 1, 1)
    plugin.files = FILES
    plugin.funcs = FUNCS
    plugin.tests = TESTS
    plugin.mode = 0

    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        plugin.save(cur)
        cur.execute("select * from test")

        assert set(cur.fetchall()) == {
            (
                plugin.test_to_id["test_foo1"], 1, "test_foo1", 
                plugin.get_func_id("foo.py", 1)
            ),
            (
                plugin.test_to_id["test_foo2"], 1, "test_foo2", 
                plugin.get_func_id("foo.py", 2)
            ),
            (
                plugin.test_to_id["test_bar1[a]"], 1, "test_bar1[a]", 
                plugin.get_func_id("bar.py", 3)
            ),
            (
                plugin.test_to_id["test_bar1[b]"], 1, "test_bar1[b]", 
                plugin.get_func_id("bar.py", 3)
            )
        }


class MockDynamic(Dynamic):
    def __init__(self, db_file, repo_id, machine):
        super().__init__(db_file, repo_id, machine)
        self.pre_call_called = False
        self.on_exception_called = False
        self.post_call_called = False

    def pre_call(self):
        self.pre_call_called = True

    def on_exception(self, e):
        self.on_exception_called = True

    def post_call(self):
        self.post_call_called = True


class MockResult:
    def get_result(self): pass


def test_pytest_pyfunc_call():
    plugin = MockDynamic(None, None, None)
    item = MockItem(MockObj(None), None)
    coro = plugin.pytest_pyfunc_call(item)
    coro.send(None)
    with pytest.raises(Exception): item.obj()
    with pytest.raises(StopIteration): coro.send(MockResult())
    assert plugin.pre_call_called
    assert plugin.on_exception_called
    assert plugin.post_call_called
    assert item.obj.called