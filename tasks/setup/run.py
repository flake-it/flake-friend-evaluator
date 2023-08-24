import os
import sys
import shutil
import sqlite3
import tempfile
import subprocess as sp

experiment_dir, image_name, repo_id = sys.argv[1:]
db_file = os.path.join(experiment_dir, "database.db")

with sqlite3.connect(db_file) as con:
    cur = con.cursor()

    cur.execute(
        "select name, sha, setup_commands from repository where id = ?",
        (repo_id,)
    )

    repo_name_long, sha, setup_commands = cur.fetchone()

repo_name_short = repo_name_long.split("/", 1)[1]
temp_dir = tempfile.mkdtemp()
repo_dir_host = os.path.join(temp_dir, repo_name_short)
root_dir = os.path.join("/", "root")
repo_dir_cont = os.path.join(root_dir, repo_name_short)
script_file = os.path.join(root_dir, "tasks", "setup.py")
data_dir = os.path.join(experiment_dir, "tasks", "setup", "data")
data_file = os.path.join(data_dir, f"{repo_id}.tar.gz")

sp.run(
    [
        "docker", "run", "--rm", "--init", 
        f"-v={repo_dir_host}:{repo_dir_cont}:rw", 
        image_name, script_file, repo_name_long, sha, setup_commands
    ],
    check=True
)

shutil.make_archive(repo_dir_host, "gztar", repo_dir_host)
shutil.copyfile(f"{repo_dir_host}.tar.gz", data_file)
shutil.rmtree(temp_dir)