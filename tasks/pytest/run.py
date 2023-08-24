import os
import sys
import json
import time
import random
import shutil
import sqlite3
import tempfile
import subprocess as sp

experiment_dir, image_name, repo_id, machine_id, mode = sys.argv[1:]
time.sleep(100 * random.random())
tasks_dir = os.path.join(experiment_dir, "tasks")
data_dir = os.path.join(tasks_dir, "setup", "data")
db_file_main = os.path.join(experiment_dir, "database.db")

with sqlite3.connect(db_file_main) as con:
    cur = con.cursor()

    cur.execute(
        "select name, run_commands, environ from repository where id = ?",
        (repo_id,)
    )

    repo_name, run_commands, environ = cur.fetchone()

    cur.execute(
        "select cpus, read_kbps, write_kbps from machine where id = ?",
        (machine_id,)
    )

    cpus, read_kbps, write_kbps = cur.fetchone()

repo_name = repo_name.split("/", 1)[1]
data_file_setup = os.path.join(data_dir, f"{repo_id}.tar.gz")
temp_dir = tempfile.mkdtemp()
repo_dir_host = os.path.join(temp_dir, repo_name)
db_file_host = os.path.join(temp_dir, "database.db")
schema_file = os.path.join(experiment_dir, "schemas", f"{mode}.sql")
with open(schema_file, "r") as f: schema = f.read()
cont_name = f"{repo_id}_{machine_id}_{mode}"

device_files = [
    os.path.join("/", "dev", dev["name"])
    for dev in json.loads(sp.check_output(["lsblk", "--json"]))["blockdevices"]
    if dev["type"] == "disk"
]

root_dir = os.path.join("/", "root")
repo_dir_cont = os.path.join(root_dir, repo_name)
db_file_cont = os.path.join(root_dir, "database.db")
script_file = os.path.join(root_dir, "tasks", "pytest.py")
data_file_run = os.path.join(tasks_dir, "pytest", "data", f"{cont_name}.db")
shutil.copyfile(data_file_setup, f"{repo_dir_host}.tar.gz")
shutil.unpack_archive(f"{repo_dir_host}.tar.gz", repo_dir_host)
with sqlite3.connect(db_file_host) as con: con.executescript(schema)

sp.run(
    [
        "docker", "run", "--rm", "--init", 
        *([] if cpus is None else [f"--cpus={cpus}"]), 
        *(
            [] if read_kbps is None else 
            [f"--device-read-bps={df}:{read_kbps}kb" for df in device_files]
        ),
        *(
            [] if write_kbps is None else 
            [f"--device-write-bps={df}:{write_kbps}kb" for df in device_files]
        ),
        f"-v={repo_dir_host}:{repo_dir_cont}:rw", 
        f"-v={db_file_host}:{db_file_cont}:rw", 
        image_name, script_file, repo_id, repo_name, machine_id, mode, 
        run_commands, environ or ""
    ],
    check=True, timeout=259200
)

shutil.copyfile(db_file_host, data_file_run)
shutil.rmtree(temp_dir)