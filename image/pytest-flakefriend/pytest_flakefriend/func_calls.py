import sys

from pytest_flakefriend.base import get_code_info
from pytest_flakefriend.static import get_numbit_ids
from pytest_flakefriend.is_source_file import IsSourceFile


class FuncCalls(IsSourceFile):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 3
        self.func_calls = set()
        self.func_call_sets = []

    def manage_child(self, item, proc):
        if not super().manage_child(item, proc): return False

        try:
            files = self.data["files"]
            funcs = self.data["funcs"]
            func_calls = self.data["func_calls"]
        except KeyError:
            return False

        if files: self.files.update(files)
        if funcs: self.funcs.update(funcs)

        if func_calls:
            self.func_calls.update(func_calls)
            self.func_call_sets.append((item.nodeid, func_calls))

        return True

    def get_func_ids_in_func_calls(self, func_calls):
        return [
            (
                None if caller is None else self.get_func_id(*caller), 
                None if callee is None else self.get_func_id(*callee)
            )
            for caller, callee in func_calls
        ]

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or ignore into function_call values (null, ?, ?)", 
            self.get_func_ids_in_func_calls(self.func_calls)
        )

        cur.execute("select caller_id, callee_id, id from function_call")

        func_call_to_id = {
            tuple(func_call): func_call_id 
            for *func_call, func_call_id in cur.fetchall()
        }

        cur.executemany(
            "insert or replace into function_call_set values (?, ?, ?, ?)",
            [
                (
                    self.test_to_id[test_name], self.machine_id, self.mode,
                    get_numbit_ids(
                        func_call_to_id, 
                        self.get_func_ids_in_func_calls(func_calls)
                    )
                )
                for test_name, func_calls in self.func_call_sets
            ]
        )

    def profilefunc(self, frame, event, arg):
        callee_func = get_code_info(frame.f_code)

        if event == "return" and callee_func == self.test_func:
            sys.setprofile(None)
            return

        if event != "call": return
        callee_file, callee_line = callee_func[:2]
        caller_func = get_code_info(frame.f_back.f_code)
        caller_file, caller_line = caller_func[:2]

        caller = (
            (caller_file, caller_line) 
            if self.is_source_file(caller_file) else None
        )

        callee = (
            (callee_file, callee_line) 
            if self.is_source_file(callee_file) else None
        )
        
        if caller is not None:
            self.files.add(caller_file)
            self.funcs.add(caller_func)

        if callee is not None:
            self.files.add(callee_file)
            self.funcs.add(callee_func)

        if caller is not None or callee is not None:
            self.func_calls.add((caller, callee))

    def profilefunc_setter(self, frame, event, arg):
        callee_func = get_code_info(frame.f_code)

        if event == "call" and callee_func == self.test_func:
            sys.setprofile(self.profilefunc)

    def pre_call(self):
        super().pre_call()
        sys.setprofile(self.profilefunc_setter)

    def post_call(self):
        super().post_call() 
        sys.setprofile(None)
        self.data["files"] = self.files
        self.data["funcs"] = self.funcs
        self.data["func_calls"] = self.func_calls

    def child_start(self, item):
        super().child_start(item)
        self.files = set()
        self.funcs = set()
        self.func_calls = set()
        self.test_func = get_code_info(item.obj.__code__)