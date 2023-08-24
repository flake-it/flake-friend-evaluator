import os
import sys
import random
import numpy as np
import scipy.sparse as ss
import sklearn.ensemble as se
import sklearn.pipeline as sp
import sklearn.neighbors as sn
import imblearn.over_sampling as ios
import sklearn.model_selection as sms
import sklearn.random_projection as srp

repo_id, mode = sys.argv[1:]

metrics_idxs, sparse_idxs = (
    ((0,),   (0,)), 
    ((0, 1), (0,)), 
    ((0, 2), (0,)), 
    ((0, 3), (0, 3)), 
    ((0, 4), (0, 6))
)[int(mode) - 1]

root_dir = os.path.join("/", "root")
training_dir = os.path.join(root_dir, "training")
labels_mask_file = os.path.join(training_dir, "labels_mask.npy")
labels_mask = np.load(labels_mask_file)
n_tests = labels_mask.shape[0]
metrics = np.zeros((n_tests, 0), dtype=np.float32)
sparse = ss.csr_array((n_tests, 0), dtype=np.bool8)
labels_file = os.path.join(training_dir, "labels.npy")

for i in metrics_idxs:
    metrics_file = os.path.join(training_dir, f"metrics_{i}.npy")
    metrics = np.hstack((metrics, np.load(metrics_file)))
    metrics_mask_file = os.path.join(training_dir, f"metrics_mask_{i}.npy")
    labels_mask &= np.load(metrics_mask_file)

for i in sparse_idxs:
    sparse_file = os.path.join(training_dir, f"sparse_{i}.npz")
    sparse = ss.hstack((sparse, ss.load_npz(sparse_file)))
    sparse_mask_file = os.path.join(training_dir, f"sparse_mask_{i}.npy")
    labels_mask &= np.load(sparse_mask_file)

labels = np.load(labels_file)[labels_mask]
repo_mask = labels[:, 0] == int(repo_id)
n_tests_predict = repo_mask.sum()
probs_file = os.path.join(root_dir, "probs.npy")

if n_tests_predict == 0:
    np.save(probs_file, np.zeros((0, 7), dtype=np.int32))
    sys.exit(0)

metrics = metrics[labels_mask]
etc = se.ExtraTreesClassifier(random_state=0)
smote = ios.SMOTE(random_state=0)
probs = np.full((n_tests_predict, 7), -1, dtype=np.int32)
probs[:, 0] = np.arange(n_tests)[labels_mask][repo_mask]
sparse = sparse[labels_mask]

knc = sp.Pipeline(
    steps=[
        ("srp", srp.SparseRandomProjection(eps=0.33, random_state=0)),
        (
            "knc", 
            sn.KNeighborsClassifier(
                n_neighbors=7, weights="distance", metric="cosine"
            )
        )
    ]
)

skf = sms.StratifiedKFold(n_splits=10, shuffle=True, random_state=0)

for i in range(2):
    labels_fit = labels[~repo_mask, i + 1]

    if (labels_fit == 0).sum() < 10 or (labels_fit == 1).sum() < 10: 
        continue

    metrics_fit = metrics[~repo_mask]
    etc.fit(*smote.fit_resample(metrics_fit, labels_fit))
    metrics_predict = metrics[repo_mask]
    etc_predict = etc.predict_proba(metrics_predict)[:, 1]
    probs[:, 3 * i + 1] = np.rint(100 * etc_predict)
    sparse_fit = sparse[~repo_mask]
    knc.fit(sparse_fit, labels_fit)
    knc_predict = knc.predict_proba(sparse[repo_mask])[:, 1]
    probs[:, 3 * i + 2] = np.rint(100 * knc_predict)
    knc_fit = np.zeros(sparse_fit.shape[0], dtype=np.float32)

    for fit_idxs, predict_idxs in skf.split(sparse_fit, labels_fit):
        knc.fit(sparse_fit[fit_idxs], labels_fit[fit_idxs])
        _knc_predict = knc.predict_proba(sparse_fit[predict_idxs])[:, 1]
        knc_fit[predict_idxs] = _knc_predict

    metrics_fit = np.c_[metrics_fit, knc_fit]
    etc.fit(*smote.fit_resample(metrics_fit, labels_fit))
    metrics_predict = np.c_[metrics_predict, knc_predict]
    etc_predict = etc.predict_proba(metrics_predict)[:, 1]
    probs[:, 3 * i + 3] = np.rint(100 * etc_predict)

np.save(probs_file, probs)