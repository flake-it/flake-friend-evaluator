import io
import re
import ast
import inspect
import importlib.util as util
import distutils.sysconfig as sysconfig

import pytest
import radon.metrics as metrics
import coverage.numbits as numbits

from pytest_flakefriend.base import get_code_info
from pytest_flakefriend.get_tokens import GetTokens


WHITESPACE_RE = re.compile("(^[ \t]*)(?:[^ \t\n])")
EXTERNAL_DIR = sysconfig.get_python_lib(standard_lib=False)


def get_numbit_ids(data_to_id, data):
    return numbits.nums_to_numbits([data_to_id[d] for d in data])


def get_func_node_body_source(source_lines, body):
    source_lines = source_lines[body[0].lineno - 1:body[-1].end_lineno]
    indent = WHITESPACE_RE.findall(source_lines[0])[0]
    source_lines[0] = source_lines[0][body[0].col_offset:]
    return re.sub(fr"(?m)^{indent}", "", "".join(source_lines))


def get_func_node_bodies(source_lines):
    return {
        node.decorator_list[0].lineno if node.decorator_list else node.lineno: 
        (node.body, get_func_node_body_source(source_lines, node.body))
        for node in ast.walk(ast.parse("".join(source_lines)))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def get_statement_depth(tree):
    if not isinstance(tree, ast.stmt): return 0
    depths = [get_statement_depth(node) for node in ast.iter_child_nodes(tree)]
    return 1 + max(depths, default=0)


def is_external_module(module_name):
    try: return util.find_spec(module_name).origin.startswith(EXTERNAL_DIR)
    except (AttributeError, ModuleNotFoundError, ValueError): return False


def get_module_names_import(node):
    for node in node.names:
        module_name = node.name.split(".")[0]
        if is_external_module(module_name): yield module_name


def get_module_names_import_from(node):
    if node.module is None: return
    module_name = node.module.split(".")[0]
    if is_external_module(module_name): yield module_name


def get_module_names_name(node, module, varnames):
    if node.id in varnames: return
    obj = getattr(module, node.id, None)
    if obj is None: return
    obj_module = obj if inspect.ismodule(obj) else inspect.getmodule(obj)
    if obj_module is None: return
    module_name = getattr(obj_module, "__name__", None)
    if module_name is None: return
    if is_external_module(module_name): yield module_name


def get_external_modules(tree, module, varnames):
    module_names = set()

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node):
            module_names.update(get_module_names_import(node))

        def visit_ImportFrom(self, node):
            module_names.update(get_module_names_import_from(node))

        def visit_Name(self, node):
            module_names.update(get_module_names_name(node, module, varnames))

        def visit_Attribute(self, node):
            while isinstance(node, ast.Attribute): node = node.value
            self.visit(node)

    Visitor().visit(tree)        
    return [name for name in module_names if "pytest" not in name]


def get_static_metrics(module, varnames, body, source):
    ast_dep = ext_mod = asserts = 0

    for tree in body:
        ast_dep = max(ast_dep, get_statement_depth(tree))
        ext_mod += len(get_external_modules(tree, module, varnames))
        asserts += sum(isinstance(node, ast.Assert) for node in ast.walk(tree))

    hal_vol, cyc_cmp, tst_loc, per_com = metrics.mi_parameters(source)
    mnt_idx = metrics.mi_compute(hal_vol, cyc_cmp, tst_loc, per_com)
    return ast_dep, ext_mod, asserts, hal_vol, cyc_cmp, tst_loc, mnt_idx


class Static(GetTokens):
    def __init__(self, db_file, repo_id, machine_id):
        super().__init__(db_file, repo_id, machine_id)
        self.mode = 1
        self.static_token_sets = []
        self.static_metrics = []

    def save(self, cur):
        super().save(cur)

        cur.executemany(
            "insert or replace into static_token_set values (?, ?)",
            [
                (
                    self.get_func_id(file, line), 
                    get_numbit_ids(self.token_to_id, tokens)
                )
                for file, line, tokens in self.static_token_sets
            ]
        )

        cur.executemany(
            "insert or replace into static_metrics values "
            "(?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (self.get_func_id(file, line), *st_metrics)
                for file, line, st_metrics in self.static_metrics
            ]
        )

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, session, config, items):
        test_funcs = {}

        for item in self.filter_items(items):
            obj = item.obj
            module = inspect.getmodule(obj)
            if module is None: continue
            code = obj.__code__
            file, line = get_code_info(code)[:2]
            test_funcs_file = test_funcs.setdefault(file, {})
            test_funcs_file[line] = module, code.co_varnames

        for file, test_funcs_file in test_funcs.items():
            with open(file, "r") as f: source_lines = f.readlines()
            func_node_bodies = get_func_node_bodies(source_lines)

            for line, (module, varnames) in test_funcs_file.items():
                try: body, source = func_node_bodies[line]
                except KeyError: continue
                readline = io.BytesIO(source.encode("utf-8")).readline
                tokens = self.get_tokens(readline)
                st_metrics = get_static_metrics(module, varnames, body, source)
                if tokens: self.static_token_sets.append((file, line, tokens))
                self.static_metrics.append((file, line, st_metrics))

        self.finish()