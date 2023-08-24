import os
import sys
import numpy as np
import scipy.sparse as ss
import sklearn.ensemble as se
import sklearn.pipeline as sp
import sklearn.neighbors as sn
import sklearn.exceptions as ske
import imblearn.over_sampling as ios
import sklearn.model_selection as sms
import sklearn.random_projection as srp

mode, neg_t, pos_t, config = sys.argv[1:]
root_dir = os.path.join("/", "root")
probs_file = os.path.join(root_dir, "probs.npy")
probs = np.load(probs_file)
config = int(config)
n_tests = probs.shape[0]
preds_file = os.path.join(root_dir, "preds.npy")

if (probs[:, 1 + config] == -1).any() or n_tests == 0:
    np.save(preds_file, np.zeros((0, 10), dtype=np.int32))
    sys.exit(0)

preds = np.full((n_tests, 10), -1, dtype=np.int32)
preds[:, 0] = probs[:, 0]
preds[:, 1] = probs[:, 1 + config] >= int(neg_t) 
preds[:, 2] = probs[:, 1 + config] >= int(pos_t)
preds[:, 1] &= preds[:, 2] == 0
training_dir = os.path.join(root_dir, "training")
labels_file = os.path.join(training_dir, "labels.npy")
labels = np.load(labels_file)[preds[:, 0]]
preds[:, 2] |= (preds[:, 1] == 1) & (labels[:, 1] == 1)

if (probs[:, 4 + config] != -1).all():
    preds[:, 6] = (
        (
            (probs[:, 4 + config] >= 50) & (preds[:, 1] == 0) & 
            (preds[:, 2] == 1)
        ) | (
            (preds[:, 1] == 1) & (labels[:, 2] == 1)
        )
    )

metrics_idxs, sparse_idxs = (
    ((0,),   (0,)), 
    ((0, 1), (0,)), 
    ((0, 2), (0, 1)), 
    ((0, 3), (0, 2, 3)), 
    ((0, 4), (0, 4, 5, 6))
)[int(mode) - 1]

metrics = np.zeros((n_tests, 0), dtype=np.float32)
sparse = ss.csr_array((n_tests, 0), dtype=np.bool8)

for i in metrics_idxs:
    metrics_file = os.path.join(training_dir, f"metrics_{i}.npy")
    metrics = np.hstack((metrics, np.load(metrics_file)[preds[:, 0]]))

for i in sparse_idxs:
    sparse_file = os.path.join(training_dir, f"sparse_{i}.npz")
    sparse = ss.hstack((sparse, ss.load_npz(sparse_file)[preds[:, 0]]))

skf = sms.StratifiedKFold(n_splits=10, shuffle=True, random_state=0)
etc = se.ExtraTreesClassifier(random_state=0)
smote = ios.SMOTE(random_state=0)

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

for i in range(2):
    if i and (preds[:, 3:7] == -1).any(): continue
    labels = preds[:, 4 * i + 2]

    for fit_idxs, predict_idxs in skf.split(metrics, labels):
        labels_fit = labels[fit_idxs]
        if (labels_fit == 0).sum() < 10 or (labels_fit == 1).sum() < 10: break

        config_mask = (preds[predict_idxs, 3:6] == 1) if i else np.ones(
            (predict_idxs.shape[0], 3), dtype=np.bool8
        )

        preds[predict_idxs, 4 * i + 3:4 * i + 6] = 0

        if config_mask[:, 0].any():
            etc.fit(*smote.fit_resample(metrics[fit_idxs], labels_fit))
            etc_predict = etc.predict(metrics[predict_idxs[config_mask[:, 0]]])
            preds[predict_idxs[config_mask[:, 0]], 4 * i + 3] = etc_predict

        if config_mask[:, 1].any():
            knc.fit(sparse[fit_idxs], labels_fit)
            knc_predict = knc.predict(sparse[predict_idxs[config_mask[:, 1]]])
            preds[predict_idxs[config_mask[:, 1]], 4 * i + 4] = knc_predict

        if config_mask[:, 2].any():
            sparse_fit = sparse[fit_idxs]
            knc_fit = np.zeros(fit_idxs.shape[0], dtype=np.float32)

            for _fit_idxs, _predict_idxs in skf.split(sparse_fit, labels_fit):
                knc.fit(sparse_fit[_fit_idxs], labels_fit[_fit_idxs])
                knc_predict = knc.predict_proba(sparse_fit[_predict_idxs])
                knc_fit[_predict_idxs] = knc_predict[:, 1]

            metrics_fit = np.c_[metrics[fit_idxs], knc_fit]
            etc.fit(*smote.fit_resample(metrics_fit, labels_fit))
            metrics_predict = metrics[predict_idxs[config_mask[:, 2]]]
            knc.fit(sparse[fit_idxs], labels_fit)
            knc_predict = knc.predict(sparse[predict_idxs[config_mask[:, 2]]])
            etc_predict = etc.predict(np.c_[metrics_predict, knc_predict])
            preds[predict_idxs[config_mask[:, 2]], 4 * i + 5] = etc_predict
        
np.save(preds_file, preds)