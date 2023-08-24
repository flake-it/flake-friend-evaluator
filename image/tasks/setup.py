import os
import sys
import shlex
import subprocess as sp

repo_name, sha, setup_commands = sys.argv[1:]
url = f"https://github.com/{repo_name}"
root_dir = os.path.join("/", "root")
repo_name = repo_name.split("/", 1)[1]
repo_dir = os.path.join(root_dir, repo_name)
work_dir = os.path.join(repo_dir, "work")
venv_dir = os.path.join(repo_dir, "venv")
pip_install = "pip", "install", "-I", "--no-deps"
env = os.environ.copy()
env["PATH"] = os.path.join(venv_dir, "bin") + ":" + env["PATH"]
req_file = os.path.join(root_dir, "requirements", f"{repo_name}.txt")
plugin_dir = os.path.join(root_dir, "pytest-flakefriend")
sp.run(["git", "clone", url, work_dir], check=True)
sp.run(["git", "reset", "--hard", sha], cwd=work_dir, check=True)
sp.run(["virtualenv", f"--python={sys.executable}", venv_dir], check=True)
sp.run([*pip_install, "pip==22.2.2"], check=True, env=env)
sp.run([*pip_install, "-r", req_file], check=True, env=env)
sp.run([*pip_install, plugin_dir], check=True, env=env)

for command in setup_commands.splitlines():
    sp.run(shlex.split(command), check=True, cwd=work_dir, env=env)