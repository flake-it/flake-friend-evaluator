from pytest_flakefriend.rerun import Rerun
from pytest_flakefriend.static import Static
from pytest_flakefriend.line_arcs import LineArcs
from pytest_flakefriend.func_calls import FuncCalls
from pytest_flakefriend.full_dynamic import FullDynamic
from pytest_flakefriend.dynamic_metrics import DynamicMetrics


OPTIONS = Rerun, Static, DynamicMetrics, FuncCalls, LineArcs, FullDynamic


def pytest_addoption(parser):
    group = parser.getgroup("pytest-detection")
    group.addoption("--mode", dest="mode", type=int)
    group.addoption("--db-file", dest="db-file", type=str)
    group.addoption("--repo-id", dest="repo-id", type=int)
    group.addoption("--machine-id", dest="machine-id", type=int)


def pytest_configure(config):
    mode = config.getoption("mode")
    db_file = config.getoption("db-file")
    repo_id = config.getoption("repo-id")
    machine_id = config.getoption("machine-id")
    if None in (mode, db_file, repo_id, machine_id): return
    plugin = OPTIONS[mode](db_file, repo_id, machine_id)
    config.pluginmanager.register(plugin)