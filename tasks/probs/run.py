import os
import sys
import shutil
import tempfile
import subprocess as sp

experiment_dir, image_name, repo_id, mode = sys.argv[1:]
training_file = os.path.join(experiment_dir, "results", "training.tar.gz")
temp_dir = tempfile.mkdtemp()
training_dir_host = os.path.join(temp_dir, "training")
root_dir = os.path.join("/", "root")
training_dir_cont = os.path.join(root_dir, "training")
probs_file_host = os.path.join(temp_dir, "probs.npy")
probs_file_cont = os.path.join(root_dir, "probs.npy")
script_file = os.path.join(root_dir, "tasks", "probs.py")
data_dir = os.path.join(experiment_dir, "tasks", "probs", "data")
data_file = os.path.join(data_dir, f"{repo_id}_{mode}.npy")
shutil.copyfile(training_file, f"{training_dir_host}.tar.gz")
shutil.unpack_archive(f"{training_dir_host}.tar.gz", training_dir_host)
open(probs_file_host, "w").close()

sp.run(
    [
        "docker", "run", "--rm", "--init", 
        f"-v={training_dir_host}:{training_dir_cont}:rw",
        f"-v={probs_file_host}:{probs_file_cont}:rw", 
        image_name, script_file, repo_id, mode
    ],
    check=True
)

shutil.copyfile(probs_file_host, data_file)
shutil.rmtree(temp_dir)