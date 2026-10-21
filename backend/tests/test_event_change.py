import numpy as np

from deforestwatch.detect.event_change import disaster_change_mask, disaster_change_probability


def test_disaster_change_is_separate_and_bounded():
    pre = np.ones((4, 4, 4), dtype="float32")
    post = pre.copy()
    pre[3, 1:3, 1:3] = 1.0
    pre[0, 1:3, 1:3] = 0.1
    post[3, 1:3, 1:3] = 0.2
    post[0, 1:3, 1:3] = 0.2
    probability = disaster_change_probability(pre, post)
    assert probability.min() >= 0.0
    assert probability.max() <= 1.0
    assert disaster_change_mask(pre, post, threshold=0.5)[1:3, 1:3].all()
