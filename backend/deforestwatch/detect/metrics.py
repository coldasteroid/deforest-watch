import numpy as np


def segmentation_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    true = np.asarray(y_true).astype(bool)
    pred = np.asarray(y_prob) >= threshold
    tp = int(np.logical_and(true, pred).sum())
    fp = int(np.logical_and(~true, pred).sum())
    fn = int(np.logical_and(true, ~pred).sum())
    tn = int(np.logical_and(~true, ~pred).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {"iou": tp / max(tp + fp + fn, 1), "f1": 2 * precision * recall / max(precision + recall, 1e-12),
            "precision": precision, "recall": recall, "pixel_accuracy": (tp + tn) / max(tp + tn + fp + fn, 1)}


def best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray, steps: int = 101) -> tuple[float, dict]:
    thresholds = np.linspace(0, 1, steps)
    results = [(float(t), segmentation_metrics(y_true, y_prob, float(t))) for t in thresholds]
    return max(results, key=lambda item: item[1]["f1"])
