import os
import sys
import subprocess as sp
import multiprocessing as mp

experiment_dir, image_name, task_name, processes = sys.argv[1:]
stdout_dir = os.path.join(experiment_dir, "stdout", task_name)
task_dir = os.path.join(experiment_dir, "tasks", task_name)
script_file = os.path.join(task_dir, "run.py")
args_file = os.path.join(task_dir, "args.csv")

def run_task(args):
    stdout_file = os.path.join(stdout_dir, "_".join(args))

    with open(stdout_file, "a") as f:
        proc = sp.run(
            [sys.executable, script_file, experiment_dir, image_name, *args],
            stdout=f, stderr=f
        )

    return ",".join(args) + f" ({proc.returncode})"

def get_args():
    with open(args_file, "r") as f:
        for i, line in enumerate(f): 
            if i: yield line.strip().split(",")
            else: print(f"{line.strip()} (returncode)")

os.makedirs(stdout_dir, exist_ok=True)

with mp.Pool(processes=int(processes)) as p:
    for message in p.imap_unordered(run_task, get_args()): print(message)