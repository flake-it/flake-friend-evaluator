import os
import sys
import subprocess as sp

experiment_dir, = sys.argv[1:]
tasks_dir = os.path.join(experiment_dir, "tasks")

for task_dir in os.listdir(tasks_dir):
    task_dir = os.path.join(tasks_dir, task_dir)
    script_file = os.path.join(task_dir, "args.py")
    args_file = os.path.join(task_dir, "args.csv")
    data_dir = os.path.join(task_dir, "data")

    old_lines = {
        tuple(os.path.splitext(data_file)[0].split("_"))
        for data_file in os.listdir(data_dir)
    }

    new_lines = []
    sp.run([sys.executable, script_file, experiment_dir], check=True)

    with open(args_file, "r") as f:
        for line in f:
            line = tuple(line.strip().split(","))
            if line not in old_lines: new_lines.append(line)

    with open(args_file, "w") as f:
        f.write("\n".join([",".join(line) for line in new_lines]))