This replication package currently only contains the code of 
FlakeFriendEvaluator and pytest-FlakeFriend and none of the data from the 
evaluation. This is because the data is very large in size and we currently
have no good way of making it available anonymously for double-blind review.

To run the experiment, you must first build the Docker image (located in the
"image" directory). The experiment is split into four tasks, each 
corresponding to a subdirectory in the "tasks" directory. Each task must be
executed repeatedly over a range of arguments. The contents of each 
subdirectory is as follows:

    1. "data/" - This is where the data from each task is stored.
    2. "args.csv" - Contains the arguments for the task.
    3. "args.py" - Python script that generates "args.csv".
    4. "run.py" - Python script to execute the task. As arguments, it takes the
       absolute filepath to this directory and the name (tag) of the Docker 
       image. The remaining arguments correspond to the values in "args.csv".

Following is the order in which the tasks must be executed along with a brief
description:

    1. "setup" - Clone and setup each subject project.
    2. "pytest" - Execute pytest-FlakeFriend as to get feature vectors and 
       ground-truth labels described in Sections III-A and III-B of the paper.
    3. "probs" - Get predicted probabilities as described in Section III-B.
    4. "preds" - Get project-agnostic and project-specific labels as described
       in Sections III-C, III-D, and III-E.

There are additional Python scripts in the "scripts" directory. Any output data 
is stored in "results/". They are as follows:

    1. "args.py" - Executes the "args.py" script for each task.
    2. "clean.py" - Clears the contents of "results/" and "data/" for each
       task.
    3. "database.py" - Produces an SQLite3 database from the data of the 
       "pytest" task. This must be executed after the "pytest" task is 
       complete.
    4. "local.py" - Facilitates running the experiment on a local machine 
       rather than a cluster.
    5. "tables.py" - Generates data for the LaTeX tables. This must be executed
       after the "preds" task is complete.
    6. "training.py" - Generates model training data. This must be executed 
        after "database.py".
