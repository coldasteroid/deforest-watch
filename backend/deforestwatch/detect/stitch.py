import numpy as np


def stitch(probabilities: list[np.ndarray], grid: list[tuple[int, int, tuple[int, int, int, int]]], shape: tuple[int, int]) -> np.ndarray:
    total = np.zeros(shape, dtype="float32")
    weights = np.zeros(shape, dtype="float32")
    for probability, (_, _, (y0, x0, y1, x1)) in zip(probabilities, grid):
        height = min(y1, shape[0]) - y0
        width = min(x1, shape[1]) - x0
        if height <= 0 or width <= 0:
            continue
        total[y0:y0 + height, x0:x0 + width] += probability[:height, :width]
        weights[y0:y0 + height, x0:x0 + width] += 1
    return np.divide(total, weights, out=np.zeros_like(total), where=weights > 0)
