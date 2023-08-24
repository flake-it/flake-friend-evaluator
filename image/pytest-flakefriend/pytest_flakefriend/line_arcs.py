import sys

import coverage

from pytest_flakefriend.get_tokens import GetTokens
from pytest_flakefriend.static import get_numbit_ids
from pytest_flakefriend.is_source_file import IsSourceFile, SOURCE_DIR


class LineArcs(GetTokens, IsSourceFile):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 4
        self.line_arcs = set()
        self.line_arc_sets = []
        self.dynamic_token_sets = []

    def manage_child(self, item, proc):
        if not super().manage_child(item, proc): return False

        try:
            files = self.data["files"]
            tokens = self.data["tokens"]
            line_arcs = self.data["line_arcs"]
        except KeyError:
            return False

        if files: self.files.update(files)

        if tokens:
            self.tokens.update(tokens)
            self.dynamic_token_sets.append((item.nodeid, tokens))

        if line_arcs:
            self.line_arcs.update(line_arcs)
            self.line_arc_sets.append((item.nodeid, line_arcs))
        
        return True

    def get_file_ids_in_line_arcs(self, line_arcs):
        return [(self.file_to_id[file], *rest) for file, *rest in line_arcs]

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or ignore into line_arc values (null, ?, ?, ?)", 
            self.get_file_ids_in_line_arcs(self.line_arcs)
        )

        cur.execute("select file_id, line_from, line_to, id from line_arc")

        line_arc_to_id = {
            tuple(line_arc): line_arc_id 
            for *line_arc, line_arc_id in cur.fetchall()
        }

        cur.executemany(
            "insert or replace into line_arc_set values (?, ?, ?, ?)",
            [
                (
                    self.test_to_id[test_name], self.machine_id, self.mode,
                    get_numbit_ids(
                        line_arc_to_id, 
                        self.get_file_ids_in_line_arcs(line_arcs)
                    )
                )
                for test_name, line_arcs in self.line_arc_sets
            ]
        )

        cur.executemany(
            "insert or replace into dynamic_token_set values (?, ?, ?, ?)",
            [
                (
                    self.test_to_id[test_name], self.machine_id, self.mode,
                    get_numbit_ids(self.token_to_id, tokens)
                )
                for test_name, tokens in self.dynamic_token_sets
            ]
        )

    def pre_call(self):
        super().pre_call()

        self.coverage = coverage.Coverage(
            data_file=None, branch=True, config_file=False, 
            source=[SOURCE_DIR], omit=self.test_files
        )

        self.coverage.start()

    def get_covered_lines(self):
        covered_lines = 0
        try: coverage_data = self.coverage.get_data()
        except coverage.exceptions.CoverageException: return covered_lines

        for file in coverage_data.measured_files():
            if not self.is_source_file(file): continue
            self.files.add(file)

            for line_from, line_to in coverage_data.arcs(file):
                self.line_arcs.add((file, line_from, line_to))

            lines = coverage_data.lines(file)
            with open(file, "rb") as f: self.get_tokens(f.readline, set(lines))
            covered_lines += len(lines)

        return covered_lines

    def post_call(self):
        super().post_call()
        self.coverage.stop()
        self.data["files"] = self.files
        self.data["tokens"] = self.tokens
        self.data["line_arcs"] = self.line_arcs

    def child_start(self, item):
        super().child_start(item)
        self.files = set()
        self.tokens = set()
        self.line_arcs = set()