import math


def fake_grid(rows, cols):
    """Test grid: blue on the left, red on the right, wavy undecided border."""
    grid = []
    for row in range(rows):
        border = cols / 2 + cols * 0.12 * math.sin(row / 4)
        grid.append([1 / (1 + math.exp(-(col - border) / (cols * 0.06)))
                     for col in range(cols)])
    return grid