import os
import sys
import sqlite3

experiment_dir, = sys.argv[1:]
db_file = os.path.join(experiment_dir, "database.db")
args_file = os.path.join(experiment_dir, "tasks", "probs", "args.csv")

with sqlite3.connect(db_file) as con:
    cur = con.cursor()
    cur.execute("select count(*) from repository")
    n_repos, = cur.fetchone()

lines = [
    f"{repo_id + 1},{mode + 1}" 
    for repo_id in range(n_repos)
    for mode in range(5)
]

lines = "repo_id,mode", *lines
with open(args_file, "w") as f: f.write("\n".join(lines))