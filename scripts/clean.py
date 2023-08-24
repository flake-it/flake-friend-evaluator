import os
import sys
import shutil

experiment_dir, = sys.argv[1:]
results_dir = os.path.join(experiment_dir, "results")
tasks_dir = os.path.join(experiment_dir, "tasks")
shutil.rmtree(results_dir)
os.mkdir(results_dir)

for task_dir in os.listdir(tasks_dir):
    data_dir = os.path.join(tasks_dir, task_dir, "data")
    shutil.rmtree(data_dir)
    os.mkdir(data_dir)