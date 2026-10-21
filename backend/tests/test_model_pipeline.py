import numpy as np
import pytest

from deforestwatch.detect.gate import gate_mask, gated_in
from deforestwatch.detect.stitch import stitch


def test_gate_and_stitch():
    assert gated_in(50)
    assert not gated_in(49)
    assert gate_mask(np.array([10, 50, 80]), 50).tolist() == [False, True, True]
    grid = [(0, 0, (0, 0, 2, 2)), (0, 1, (0, 1, 2, 3))]
    result = stitch([np.ones((2, 2)), np.full((2, 2), 3)], grid, (2, 3))
    assert result.tolist() == [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]]


def test_missing_checkpoint_is_explicit():
    from deforestwatch.detect.runner import ModelRunner
    with pytest.raises(FileNotFoundError):
        ModelRunner("models/does-not-exist.pt")
