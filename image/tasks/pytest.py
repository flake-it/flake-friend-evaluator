import os
import sys
import shlex
import subprocess as sp

repo_id, repo_name, machine_id, mode, run_commands, environ = sys.argv[1:]
run_commands = run_commands.splitlines()
root_dir = os.path.join("/", "root")
repo_dir = os.path.join(root_dir, repo_name)
work_dir = os.path.join(repo_dir, "work")
environ = {k: v for e in environ.splitlines() for k, v in e.split("=", 2)}
env = {**os.environ, **environ}
env["PATH"] = os.path.join(repo_dir, "venv", "bin") + ":" + env["PATH"]
db_file = os.path.join(root_dir, "database.db")

for command in run_commands[:-1]:
    sp.run(shlex.split(command), check=True, cwd=work_dir, env=env)

sp.run(
    [
        *shlex.split(run_commands[-1]), "-v", f"--mode={mode}", 
        f"--db-file={db_file}", f"--repo-id={repo_id}", 
        f"--machine-id={machine_id}"
    ],
    check=True, cwd=work_dir, env=env
)