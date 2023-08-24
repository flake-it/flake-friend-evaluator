from pytest_flakefriend.line_arcs import LineArcs
from pytest_flakefriend.func_calls import FuncCalls


class FullDynamic(FuncCalls, LineArcs):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 5