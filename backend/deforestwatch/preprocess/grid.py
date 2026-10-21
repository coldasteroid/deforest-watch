from math import ceil


def chip_grid(shape: tuple[int, int], size: int = 256, overlap: int = 32):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chip size must be positive and overlap must be smaller than size")
    height, width = shape
    stride = size - overlap
    rows = max(1, ceil(max(0, height - size) / stride) + 1)
    cols = max(1, ceil(max(0, width - size) / stride) + 1)
    padded_shape = ((rows - 1) * stride + size, (cols - 1) * stride + size)
    return [(row, col, (row * stride, col * stride, row * stride + size, col * stride + size))
            for row in range(rows) for col in range(cols)], padded_shape
