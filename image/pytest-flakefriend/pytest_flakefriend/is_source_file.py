import os

from pytest_flakefriend.dynamic_metrics import DynamicMetrics


SOURCE_DIR = os.getcwd()


class IsSourceFile(DynamicMetrics):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.test_files = set()

    def filter_items(self, items):
        for item in super().filter_items(items):
            self.test_files.add(item.obj.__code__.co_filename)
            yield item

    def is_source_file(self, file):
        return file.startswith(SOURCE_DIR) and file not in self.test_files