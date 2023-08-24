import os
import sys
import shutil
import sqlite3
import numpy as np

experiment_dir, = sys.argv[1:]
results_dir = os.path.join(experiment_dir, "results")
tables_dir = os.path.join(results_dir, "tables")

class Table:
    def __init__(self, table_data):
        self.table_data = table_data

    def format_cell(self, n_rows, row_i, col_i, cell): 
        return str(cell)

    def make(self, table_file):
        table_file = os.path.join(tables_dir, table_file)
        n_rows = len(self.table_data)

        with open(table_file, "w") as f:
            f.write(
                "\n".join([
                    self.before_row(n_rows, row_i) + 
                    " & ".join([
                        self.format_cell(n_rows, row_i, col_i, cell) 
                        for col_i, cell in enumerate(row)
                    ]) + 
                    " \\\\" 
                    for row_i, row in enumerate(self.table_data)
                ])
            )

def get_sci_notation(cell):
    base, expo = ("%.2e" % cell).split("e")
    return f"${base} \\times 10 ^ {{{int(expo)}}}$"

db_file = os.path.join(results_dir, "database.db")

with sqlite3.connect(db_file) as con:
    cur = con.cursor()
    cur.execute("select id, name from repository")

    repositories = dict(
        sorted(
            [(x[0], x[1].split("/", 1)[1]) for x in cur.fetchall()], 
            key=lambda x: x[1]
        )
    )

    n_repos = len(repositories)
    features_cost = np.full((n_repos, 5), np.nan)

    cur.execute(
        "select repository_id, mode, elapsed_time from record where "
        "machine_id = 1 and mode != 0"
    )

    for repo_id, mode, elapsed_time in cur.fetchall():
        features_cost[repo_id - 1, mode - 1] = elapsed_time

class SubjectsTable(Table):
    def before_row(self, n_rows, row_i):
        if row_i == n_rows - 1: return "\\midrule\n"
        if row_i % 2 == 1: return "\\rowcolor{gray!20}\n"
        return ""

    def format_cell(self, n_rows, row_i, col_i, cell):
        if col_i == 0:
            if row_i == n_rows - 1: return "{\\bf Total}"
            return repositories[int(cell)]
        
        if cell == 0: return "-"
        if col_i in (1, 2, 3): return "%.0f" % cell
        if np.isnan(cell): return "$\\bot$"
        return get_sci_notation(cell)

subjects_table = np.zeros((n_repos + 1, 9))
training_dir = os.path.join(results_dir, "training")
labels_mask_file = os.path.join(training_dir, "labels_mask.npy")
labels_mask = np.load(labels_mask_file)
labels_file = os.path.join(training_dir, "labels.npy")
labels = np.load(labels_file)

for i, repo_id in enumerate(repositories):
    repo_mask = labels_mask & (labels[:, 0] == repo_id)

    subjects_table[i] = (
        repo_id, repo_mask.sum(), *labels[repo_mask, 1:].sum(axis=0), 
        *features_cost[repo_id - 1]
    )

subjects_table[-1] = np.nansum(subjects_table[:-1], axis=0)
configs = ["ET", "KNN", "ET+KNN"]
modes = ["Rerun", "Static", "Dynamic", "DFunc", "DLine", "DFL"]

class ConfigTable(Table):
    def before_row(self, n_rows, row_i):
        if row_i % 2 == 1: return "\\rowcolor{gray!20}\n"
        return ""

    def format_cell(self, n_rows, row_i, col_i, cell):
        if col_i == 0: return repositories[int(cell)]
        if col_i in (1, 2, 6, 7, 11): return configs[int(cell)]
        if col_i in (3, 8, 12): return modes[int(cell)]
        return "%.2f" % (0.01 * cell)

class AgnosticTable(ConfigTable):
    def format_cell(self, n_rows, row_i, col_i, cell):
        if col_i == 0: return repositories[int(cell)]
        if np.isnan(cell): return "$\\bot$"
        if col_i in (5, 10, 15, 20): return "%.2f" % cell
        if cell == 0: return "-"
        if col_i in (21, 22, 23): return get_sci_notation(cell)
        return "%.0f" % cell

class CostTable(ConfigTable):
    def format_cell(self, n_rows, row_i, col_i, cell):
        if col_i == 0: return repositories[int(cell)]
        return get_sci_notation(cell)

class SpecificTable(ConfigTable):
    def format_cell(self, n_rows, row_i, col_i, cell):
        if col_i == 0: return repositories[int(cell)]
        if np.isnan(cell): return "$\\bot$"
        if col_i in (5, 10, 15, 20, 25, 30): return "%.2f" % cell
        if cell == 0: return "-"
        return "%.0f" % cell

config_table = []
agnostic_table = []
cost_table = []
nod_table = []
spec_table = []
cumulative_table = []
data_dir = os.path.join(experiment_dir, "tasks", "preds", "data")
labels_cost_file = os.path.join(training_dir, "labels_cost.npy")
labels_cost = np.load(labels_cost_file)

def eval_preds(repo_mask, preds, i, j):
    if (preds[:, j] == -1).any(): return np.full(5, np.nan)
    labels_true = labels[repo_mask, i] == 1
    labels_pred = np.zeros(labels.shape[0], dtype=np.bool8)
    labels_pred[preds[:, 0]] = preds[:, j] == 1
    labels_pred = labels_pred[repo_mask]
    tp = (labels_true & labels_pred).sum()
    tn = (~labels_true & ~labels_pred).sum()
    fp = (~labels_true & labels_pred).sum()
    fn = (labels_true & ~labels_pred).sum()
    mcc = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = np.nan if mcc == 0 else np.abs((tp * tn - fp * fn) / mcc)
    return np.array([tp, tn, fp, fn, mcc])

params = [[[], np.full(7, np.nan)] for _ in range(n_repos)]

for data_file in os.listdir(data_dir):
    parts = os.path.splitext(data_file)[0].split("_", 4)
    repo_id, mode, neg_t, pos_t, config_1 = [int(x) for x in parts]
    cost = features_cost[repo_id - 1, mode - 1]
    if np.isnan(cost): continue
    data_file = os.path.join(data_dir, data_file)
    preds = np.load(data_file)
    if preds.shape[0] == 0: continue
    cost += labels_cost[preds[preds[:, 1] == 1, 0]].sum()
    repo_mask = labels_mask & (labels[:, 0] == repo_id)

    for config_2 in range(3):
        mcc = eval_preds(repo_mask, preds, 1, config_2 + 3)[4] 
        if np.isnan(mcc): continue

        params[repo_id - 1][0].append([
            mode, neg_t, pos_t, config_1, config_2, cost, mcc
        ])

    if neg_t == pos_t:
        mcc = eval_preds(repo_mask, preds, 1, 2)[4] 
        if np.isnan(mcc) or mcc <= params[repo_id - 1][1][6]: continue
        params[repo_id - 1][1][:] = mode, neg_t, -1, config_1, -1, -1, mcc

for repo_id in repositories:
    params_repo = params[repo_id - 1]
    if not params_repo[0] or np.isnan(params_repo[1]).any(): continue
    params_repo[0] = np.array(params_repo[0])
    params_repo[0][:, 5:] -= params_repo[0][:, 5:].min(axis=0)
    params_repo[0][:, 5:] /= params_repo[0][:, 5:].max(axis=0)
    params_repo[0][:, 6] = 1 - params_repo[0][:, 6]

    params_repo[0] = params_repo[0][[
        np.linalg.norm(params_repo[0][:, 5:], axis=1).argmin(),
        (params_repo[0][:, 5] - 100 * (params_repo[0][:, 6] == 0)).argmin()
    ]]

    config_table.append(
        np.array([
            repo_id, *params_repo[0][:, [3, 4, 0, 1, 2]].flatten(), 
            *params_repo[1][[3, 0, 1]]
        ])
    )

    agnostic_table_repo = np.zeros(21)
    agnostic_table_repo[0] = repo_id
    agnostic_table.append(agnostic_table_repo)
    cost_table_repo = np.zeros(4)
    cost_table_repo[0] = repo_id
    repo_mask = labels_mask & (labels[:, 0] == repo_id)
    cost_table_repo[3] = labels_cost[repo_mask].sum()
    cost_table.append(cost_table_repo)
    nod_table_repo = np.zeros(16)
    nod_table_repo[0] = repo_id
    nod_table.append(nod_table_repo)
    spec_table_repo = np.zeros(16)
    spec_table_repo[0] = repo_id
    spec_table.append(spec_table_repo)
    cumulative_table_repo = np.zeros(9)
    cumulative_table_repo[0] = repo_id
    cumulative_table.append(cumulative_table_repo)

    for i, params_i in enumerate(np.vstack(params_repo)):
        mode, neg_t, pos_t, config_1, config_2, *_ = params_i.astype(int)
        if i == 2: pos_t = neg_t

        data_file = os.path.join(
            data_dir, f"{repo_id}_{mode}_{neg_t}_{pos_t}_{config_1}.npy"
        )
    
        preds = np.load(data_file)
        _features_cost = features_cost[repo_id - 1, mode - 1]
        cost = _features_cost + labels_cost[preds[preds[:, 1] == 1, 0]].sum()

        if i < 2:
            agnostic_table_repo[1 + 5 * i:6 + 5 * i] = eval_preds(
                repo_mask, preds, 1, 2
            )

            agnostic_table_repo[11 + 5 * i:16 + 5 * i] = eval_preds(
                repo_mask, preds, 2, 6
            )

            cost_table_repo[1 + i] = cost

            nod_table_repo[1 + 5 * i:6 + 5 * i] = eval_preds(
                repo_mask, preds, 1, 3 + config_2
            ) 

            spec_table_repo[1 + 5 * i:6 + 5 * i] = eval_preds(
                repo_mask, preds, 2, 7 + config_2
            )

            delta = np.array([1000, preds.shape[0]])

            cumulative_table_repo[1 + 4 * i:5 + 4 * i] = (
                *(cost + (_features_cost / preds.shape[0]) * delta),
                *(cost + (cost / preds.shape[0]) * delta),
            )
        else:
            nod_table_repo[11:] = eval_preds(repo_mask, preds, 1, 2)
            spec_table_repo[11:] = eval_preds(repo_mask, preds, 2, 6)

try:
    os.mkdir(tables_dir)
except FileExistsError: 
    shutil.rmtree(tables_dir)
    os.mkdir(tables_dir)

SubjectsTable(subjects_table).make("subjects.tex")
ConfigTable(config_table).make("config.tex")
AgnosticTable(agnostic_table).make("agnostic.tex")
CostTable(cost_table).make("cost.tex")
SpecificTable(nod_table).make("nod.tex")
SpecificTable(spec_table).make("spec.tex")
CostTable(cumulative_table).make("cumulative.tex")