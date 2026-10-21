import numpy as np

from deforestwatch.detect.metrics import best_f1_threshold, segmentation_metrics


def test_segmentation_metrics_and_best_threshold():
    truth = np.array([[0, 1], [1, 0]])
    probability = np.array([[0.1, 0.9], [0.8, 0.2]])
    metrics = segmentation_metrics(truth, probability)
    assert metrics["iou"] == 1.0
    threshold, best = best_f1_threshold(truth, probability)
    assert 0 <= threshold <= 1
    assert best["f1"] == 1.0
