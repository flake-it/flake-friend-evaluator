import os
import sys
import shutil
import sqlite3
import numpy as np
import scipy.stats as ss
import scipy.sparse as sp
import coverage.numbits as nb

experiment_dir, = sys.argv[1:]
results_dir = os.path.join(experiment_dir, "results")
db_file = os.path.join(results_dir, "database.db")
training_dir = os.path.join(results_dir, "training")
labels_file = os.path.join(training_dir, "labels.npy")
labels_mask_file = os.path.join(training_dir, "labels_mask.npy")
labels_cost_file = os.path.join(training_dir, "labels_cost.npy")
function_tests = {}
lines = {}

with sqlite3.connect(db_file) as con:
    cur = con.cursor()
    cur.execute("select count(*) from test")
    n_tests, = cur.fetchone()
    labels = np.zeros((n_tests, 3), dtype=np.int32)
    cur.execute("select repository_id from test order by id asc")
    labels[:, 0, None] = cur.fetchall()
    labels_mask = np.zeros(n_tests, dtype=np.bool8)
    labels_cost = np.zeros(n_tests, dtype=np.float32)

    cur.execute(
        "select cpus, read_kbps, write_kbps from machine order by id asc"
    )

    machines = np.array(cur.fetchall()[1:])

    for i in range(n_tests):
        test_runs = []

        cur.execute(
            "select machine_id, exception_id, elapsed_time "
            "from test_run where test_id = ?",
            (i + 1,)
        )

        for machine_id, exception_id, elapsed_time in cur.fetchall():
            # A few tests have impossible elapsed_time values for some reason.
            # (Maybe they mess with the system time or something.)
            if not 0 < elapsed_time < 10000: continue
            test_runs.append([machine_id - 2, exception_id is None])
            labels_cost[i] += elapsed_time

        test_runs = np.array(test_runs)
        n_runs = test_runs.shape[0]
        if n_runs < 200: continue
        labels_mask[i] = True
        pass_mask = test_runs[:, 1] == 1
        n_pass = pass_mask.sum()
        if n_pass == 0 or n_pass == n_runs: continue
        labels[i, 1] = 1
        if n_pass < 8 or n_runs - n_pass < 8: continue
        machines_pass = machines[test_runs[pass_mask, 0]]
        machines_fail = machines[test_runs[~pass_mask, 0]]

        for j in range(3):
            p = ss.mannwhitneyu(machines_pass[:, j], machines_fail[:, j])[1]
            if p > 0.05: continue 
            labels[i, 2] = 1
            break

    cur.execute("select count(*) from token")
    n_tokens, = cur.fetchone()
    cur.execute("select count(*) from function")
    n_functions, = cur.fetchone()

    cur.execute(
        "select caller_id, callee_id from function_call order by id asc"
    )

    calls = cur.fetchall()

    cur.execute(
        "select file_id, line_from, line_to from line_arc order by id asc"
    )

    arcs = cur.fetchall()

    for file_id, line_from, line_to in arcs:
        lines.setdefault((file_id, abs(line_from)), len(lines))
        lines.setdefault((file_id, abs(line_to)), len(lines))

    cur.execute("select * from static_metrics")
    static_metrics = cur.fetchall()
    cur.execute("select id, function_id from test")

    for test_id, function_id in cur.fetchall():
        function_tests.setdefault(function_id, []).append(test_id - 1)

    cur.execute("select * from dynamic_metrics")
    dynamic_metrics = cur.fetchall()
    cur.execute("select * from function_call_set")
    call_sets = cur.fetchall()
    cur.execute("select * from line_arc_set")
    arc_sets = cur.fetchall()
    cur.execute("select * from static_token_set")
    static_sets = cur.fetchall()
    cur.execute("select * from dynamic_token_set")
    dynamic_sets = cur.fetchall()

metrics = [
    np.zeros((n_tests, n), dtype=np.float32) for n in (7, 10, 10, 11, 11)
]

metrics_mask = [np.zeros(n_tests, dtype=np.bool8) for _ in range(5)]

sparse = [
    sp.dok_array((n_tests, n), dtype=np.bool8) for n in (
        n_tokens, n_functions + len(calls), len(lines) + len(arcs), n_tokens, 
        n_functions + len(calls), len(lines) + len(arcs), n_tokens
    )
]

sparse_mask = [np.zeros(n_tests, dtype=np.bool8) for _ in range(7)]

def save_sparse(i):
    sparse[i] = sparse[i].tocsr()
    sparse_file = os.path.join(training_dir, f"sparse_{i}.npz")
    sp.save_npz(sparse_file, sparse[i])
    sparse[i] = None
    sparse_mask_file = os.path.join(training_dir, f"sparse_mask_{i}.npy")
    np.save(sparse_mask_file, sparse_mask[i])
    sparse_mask[i] = None

try:
    os.mkdir(training_dir)
except FileExistsError:
    shutil.rmtree(training_dir)
    os.mkdir(training_dir)

np.save(labels_file, labels)
np.save(labels_mask_file, labels_mask)
np.save(labels_cost_file, labels_cost)

for function_id, *rest in static_metrics:
    try: test_idxs = function_tests[function_id]
    except KeyError: continue
    metrics[0][test_idxs] = rest
    metrics_mask[0][test_idxs] = True

for test_id, _, mode, *rest in dynamic_metrics:
    rest = (rest[:7] + rest[8:]) if mode < 4 else rest
    metrics[mode - 1][test_id - 1] = rest
    metrics_mask[mode - 1][test_id - 1] = True

for i in range(5):
    metrics_file = os.path.join(training_dir, f"metrics_{i}.npy")
    np.save(metrics_file, metrics[i])
    metrics[i] = None
    metrics_mask_file = os.path.join(training_dir, f"metrics_mask_{i}.npy")
    np.save(metrics_mask_file, metrics_mask[i])
    metrics_mask[i] = None

for test_id, _, mode, function_calls in call_sets:
    i = {3: 1, 5: 4}[mode]
    sparse_mask[i][test_id - 1] = True

    for call_id in nb.numbits_to_nums(function_calls):
        caller_id, callee_id = calls[call_id - 1]
        if caller_id is not None: sparse[i][test_id - 1, caller_id - 1] = True
        if callee_id is not None: sparse[i][test_id - 1, callee_id - 1] = True
        sparse[i][test_id - 1, n_functions + call_id - 1] = True

save_sparse(1)
save_sparse(4)

for test_id, _, mode, line_arcs in arc_sets:
    i = {4: 2, 5: 5}[mode]
    sparse_mask[i][test_id - 1] = True

    for arc_id in nb.numbits_to_nums(line_arcs):
        file_id, line_from, line_to = arcs[arc_id - 1]
        sparse[i][test_id - 1, lines[(file_id, abs(line_from))]] = True
        sparse[i][test_id - 1, lines[(file_id, abs(line_to))]] = True
        sparse[i][test_id - 1, len(lines) + arc_id - 1] = True

save_sparse(2)
save_sparse(5)

for function_id, tokens in static_sets:
    try: test_idxs = function_tests[function_id]
    except KeyError: continue
    tokens = nb.numbits_to_nums(tokens)
    sparse_mask[0][test_idxs] = True

    for i in test_idxs:
        for token_id in tokens: sparse[0][i, token_id - 1] = True
    
save_sparse(0)

for test_id, _, mode, tokens in dynamic_sets:
    i = {4: 3, 5: 6}[mode]
    sparse_mask[i][test_id - 1] = True

    for token_id in nb.numbits_to_nums(tokens):
        sparse[i][test_id - 1, token_id - 1] = True
    
save_sparse(3)
save_sparse(6)
shutil.make_archive(training_dir, "gztar", training_dir)