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
    """Threshold on the same linspace grid that maximises F1.

    Counts every threshold in one binning pass instead of re-scanning the
    arrays once per candidate. Scoring a validation split of 13 million pixels
    over 101 thresholds is otherwise 101 full passes per epoch, which dominated
    training time. A probability falls in bin `j` when `thresholds[j]` is the
    largest grid value not exceeding it, so `prob >= thresholds[k]` is exactly
    `j >= k` and the reverse cumulative sums give the confusion counts at every
    threshold. The returned threshold and metrics match the per-threshold scan.
    """
    thresholds = np.linspace(0, 1, steps)
    true = np.asarray(y_true).astype(bool).ravel()
    probability = np.asarray(y_prob, dtype="float64").ravel()
    if true.size == 0:
        return float(thresholds[0]), segmentation_metrics(y_true, y_prob, float(thresholds[0]))

    index = np.clip(np.searchsorted(thresholds, probability, side="right") - 1, 0, steps - 1)
    positives = np.bincount(index[true], minlength=steps)
    negatives = np.bincount(index[~true], minlength=steps)
    # at threshold k: predicted positive == bins k..end
    tp = positives[::-1].cumsum()[::-1].astype("float64")
    fp = negatives[::-1].cumsum()[::-1].astype("float64")
    total_positive = float(true.sum())
    fn = total_positive - tp

    denominator = 2 * tp + fp + fn
    f1 = np.divide(2 * tp, denominator, out=np.zeros(steps), where=denominator > 0)
    best = int(np.argmax(f1))
    threshold = float(thresholds[best])
    return threshold, segmentation_metrics(y_true, y_prob, threshold)
