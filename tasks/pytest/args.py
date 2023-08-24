import os
import sys
import random
import sqlite3

experiment_dir, = sys.argv[1:]
db_file = os.path.join(experiment_dir, "database.db")
args_file = os.path.join(experiment_dir, "tasks", "pytest", "args.csv")

with sqlite3.connect(db_file) as con:
    cur = con.cursor()
    cur.execute("select count(*) from repository")
    n_repos, = cur.fetchone()
    cur.execute("select count(*) from machine")
    n_machines, = cur.fetchone()

lines_head = []
lines_tail = []

for repo_id in range(n_repos):
    for machine_id in range(n_machines):
        if machine_id == 0:
            for mode in range(5):
                lines_head.append(f"{repo_id + 1},{machine_id + 1},{mode + 1}")
        else:
            lines_tail.append(f"{repo_id + 1},{machine_id + 1},0")

random.shuffle(lines_head)
random.shuffle(lines_tail)
lines = "repo_id,machine_id,mode", *lines_head, *lines_tail
with open(args_file, "w") as f: f.write("\n".join(lines))