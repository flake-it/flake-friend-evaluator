import os
import sys
import random
import shutil
import sqlite3
import tempfile
import coverage.numbits as nb

experiment_dir, = sys.argv[1:]
data_dir = os.path.join(experiment_dir, "tasks", "pytest", "data")
temp_dir = tempfile.mkdtemp()
schema_file = os.path.join(experiment_dir, "schemas", "main.sql")
with open(schema_file, "r") as f: schema = f.read()

table_info = (
    (
        "file", (0, 1, 2, 3, 4, 5), (), ("file",), 1
    ),
    (
        "exception", (0,), (), ("exception",), 1
    ),
    (
        "token", (1, 4, 5), (), ("token",), 1
    ),
    (
        "record", (0, 1, 2, 3, 4, 5), (), (), 4
    ),
    (
        "function", (0, 1, 2, 3, 4, 5), ((False, "file", 1),), 
        ("file_id", "line"), 3
    ),
    (
        "line_arc", (4, 5), ((False, "file", 1),), 
        ("file_id", "line_from", "line_to"), 3
    ),
    (
        "test", (0, 2, 3, 4, 5), ((False, "function", 3),), 
        ("repository_id", "name"), 3
    ),
    (
        "function_call", (3, 5), 
        ((False, "function", 1), (False, "function", 2)), 
        ("caller_id", "callee_id"), 2
    ),
    (
        "static_metrics", (1,), ((False, "function", 0),), (), 8
    ),
    (
        "test_run", (0,), ((False, "test", 0), (False, "exception", 2)), (), 10
    ),
    (
        "function_call_set", (3, 5), 
        ((False, "test", 0), (True, "function_call", 3)), (), 4
    ),
    (
        "line_arc_set", (4, 5), ((False, "test", 0), (True, "line_arc", 3)), 
        (), 4
    ),
    (
        "static_token_set", (1,), ((False, "function", 0), (True, "token", 1)), 
        (), 2
    ),
    (
        "dynamic_token_set", (4, 5,), ((False, "test", 0), (True, "token", 3)), 
        (), 4
    ),
    (
        "dynamic_metrics", (2, 3, 4, 5), ((False, "test", 0),), (), 14
    )
)

def load(cur, mode=None):
    data = {}

    for table_name, table_modes, *_ in table_info:
        if mode is not None and mode not in table_modes: continue
        cur.execute(f"select * from {table_name}")
        data[table_name] = [list(values) for values in cur.fetchall()]

    return data

def save(cur, data, mode=None):
    id_map = {}

    for table_name, table_modes, foreign_keys, lookup, n_qmark in table_info:
        if mode is not None and mode not in table_modes: continue
        data_table = data[table_name]

        for is_numbits, foreign_table, col_i in foreign_keys:
            for values in data_table:
                if is_numbits:
                    old_ids = nb.numbits_to_nums(values[col_i])
                    new_ids = [id_map[foreign_table][oid] for oid in old_ids]
                    values[col_i] = nb.nums_to_numbits(new_ids)
                elif values[col_i] is not None:
                    values[col_i] = id_map[foreign_table][values[col_i]] 

        action = "ignore" if lookup else "replace"
        params = ",".join((["null"] if lookup else []) + ["?"] * n_qmark)
        statement = f"insert or {action} into {table_name} values ({params})"
        args = [values[1:] for values in data_table] if lookup else data_table
        cur.executemany(statement, args)
        if not lookup: continue
        lookup_str = ",".join(lookup)
        cur.execute(f"select {lookup_str},id from {table_name}")
        new_ids = {tuple(values): nid for *values, nid in cur.fetchall()}

        id_map[table_name] = {
            oid: new_ids[tuple(values[:len(lookup)])] 
            for oid, *values in data_table
        }

def update(data_file, db_file, mode=None):
    print(data_file, "->", db_file)
    with sqlite3.connect(data_file) as con: data = load(con.cursor(), mode)
    with sqlite3.connect(db_file) as con: save(con.cursor(), data, mode)

data_dir_list = os.listdir(data_dir)
n_db_files = int(len(data_dir_list) ** 0.5)

for i in range(n_db_files):
    db_file = os.path.join(temp_dir, f"{i}.db")
    with sqlite3.connect(db_file) as con: con.executescript(schema)

random.shuffle(data_dir_list)

for i, data_file in enumerate(data_dir_list):
    mode = int(os.path.splitext(data_file)[0].split("_", 2)[2])
    data_file = os.path.join(data_dir, data_file)
    db_file = os.path.join(temp_dir, f"{i % n_db_files}.db")
    update(data_file, db_file, mode)

db_file = os.path.join(experiment_dir, "results", "database.db")

if not os.path.exists(db_file):
    db_file_init = os.path.join(experiment_dir, "database.db")
    shutil.copyfile(db_file_init, db_file)

for data_file in os.listdir(temp_dir):
    data_file = os.path.join(temp_dir, data_file)
    update(data_file, db_file)

shutil.rmtree(temp_dir)