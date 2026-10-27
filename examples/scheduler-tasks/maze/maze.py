"""Generate a perfect ASCII maze using iterative randomized depth-first search."""
import argparse
import random


def generate(width=10, height=6, seed=None):
    """Return rows of a maze with one route between every pair of cells.

    width/height count cells; rendered dimensions are 2*width+1 by 2*height+1.
    S is the top entrance, G the bottom exit, and # a wall.
    """
    if any(type(value) is not int or not 1 <= value <= 200 for value in (width, height)):
        raise ValueError('width and height must be integers from 1 to 200')
    rng = random.Random(seed)
    grid = [['#'] * (2*width+1) for _ in range(2*height+1)]
    visited, stack = {(0, 0)}, [(0, 0)]
    grid[1][1] = ' '
    while stack:
        x, y = stack[-1]
        neighbors = [(nx, ny) for nx, ny in ((x+1,y), (x-1,y), (x,y+1), (x,y-1))
                     if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited]
        if not neighbors:
            stack.pop()
            continue
        nx, ny = rng.choice(neighbors)
        grid[y+ny+1][x+nx+1] = ' '
        grid[2*ny+1][2*nx+1] = ' '
        visited.add((nx, ny))
        stack.append((nx, ny))
    grid[0][1], grid[-1][-2] = 'S', 'G'
    return [''.join(row) for row in grid]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=10)
    parser.add_argument('--height', type=int, default=6)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args(argv)
    try:
        grid = generate(args.width, args.height, args.seed)
    except ValueError as error:
        parser.error(str(error))
    print('\n'.join(grid))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
