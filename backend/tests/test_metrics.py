import numpy as np

from deforestwatch.detect.metrics import best_f1_threshold, segmentation_metrics


def _scan_for_best_f1(truth, probability, steps=101):
    """The original per-threshold scan, kept as the reference implementation."""
    thresholds = np.linspace(0, 1, steps)
    scored = [(float(t), segmentation_metrics(truth, probability, float(t))) for t in thresholds]
    return max(scored, key=lambda item: item[1]["f1"])


def test_best_f1_threshold_matches_an_exhaustive_scan():
    """The binned search replaced 101 full passes over the array; it has to
    pick the same optimum, including at the extreme class imbalance this
    project runs at (positives are a fraction of a per cent of pixels)."""
    rng = np.random.default_rng(0)
    for positive_rate in (0.002, 0.05, 0.4):
        truth = rng.random(20000) < positive_rate
        probability = np.clip(rng.random(20000) * 0.6 + truth * rng.random(20000) * 0.8, 0, 1)
        _, fast = best_f1_threshold(truth, probability)
        _, reference = _scan_for_best_f1(truth, probability)
        assert fast["f1"] == reference["f1"]


def test_best_f1_threshold_handles_degenerate_inputs():
    rng = np.random.default_rng(1)
    for truth in (np.zeros(100, dtype=bool), np.ones(100, dtype=bool)):
        threshold, metrics = best_f1_threshold(truth, rng.random(100))
        assert 0.0 <= threshold <= 1.0
        assert 0.0 <= metrics["f1"] <= 1.0
    threshold, _ = best_f1_threshold(np.zeros(0, dtype=bool), np.zeros(0))
    assert 0.0 <= threshold <= 1.0


def test_segmentation_metrics_and_best_threshold():
    truth = np.array([[0, 1], [1, 0]])
    probability = np.array([[0.1, 0.9], [0.8, 0.2]])
    metrics = segmentation_metrics(truth, probability)
    assert metrics["iou"] == 1.0
    threshold, best = best_f1_threshold(truth, probability)
    assert 0 <= threshold <= 1
    assert best["f1"] == 1.0
