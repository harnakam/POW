from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import subprocess
import sys
import unittest

from maze import generate, main


class MazeTests(unittest.TestCase):
    def test_dimensions_entrances_and_walls(self):
        grid = generate(4, 3, seed=7)
        self.assertEqual(len(grid), 7)
        self.assertTrue(all(len(row) == 9 for row in grid))
        self.assertEqual(grid[0], '#S#######')
        self.assertEqual(grid[-1], '#######G#')
        self.assertTrue(all(row[0] == row[-1] == '#' for row in grid))
        self.assertTrue(all(grid[y][x] == ' ' for y in range(1, 6, 2) for x in range(1, 8, 2)))

    def test_connected_and_no_cycles_including_thin_mazes(self):
        for width, height in [(1, 1), (1, 8), (8, 1), (4, 5), (20, 20)]:
            for seed in range(4):
                with self.subTest(size=(width, height), seed=seed):
                    grid = generate(width, height, seed)
                    opened = {(x, y) for y, row in enumerate(grid) for x, c in enumerate(row) if c != '#'}
                    visited, stack = set(), [(1, 0)]
                    while stack:
                        point = stack.pop()
                        if point in visited:
                            continue
                        visited.add(point)
                        x, y = point
                        stack.extend(p for p in ((x+1, y), (x-1, y), (x, y+1), (x, y-1))
                                     if p in opened and p not in visited)
                    self.assertEqual(visited, opened)
                    edges = sum((x+1, y) in opened for x, y in opened) + sum((x, y+1) in opened for x, y in opened)
                    self.assertEqual(edges, len(opened)-1)

    def test_seed_is_reproducible(self):
        self.assertEqual(generate(8, 6, 42), generate(8, 6, 42))

    def test_invalid_sizes(self):
        for value in (0, -1, 201, True, 1.5, '3'):
            for dimensions in ((value, 2), (2, value)):
                with self.subTest(size=dimensions), self.assertRaises(ValueError):
                    generate(*dimensions)

    def test_cli_matches_library(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--width', '3', '--height', '2', '--seed', '4']), 0)
        self.assertEqual(output.getvalue(), '\n'.join(generate(3, 2, 4))+'\n')

    def test_cli_rejects_invalid_dimensions(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(['--width', '0'])
        self.assertEqual(error.exception.code, 2)

    def test_real_process_entrypoint(self):
        result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('maze.py')),
                                 '--width', '2', '--height', '2', '--seed', '9'],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '\n'.join(generate(2, 2, 9))+'\n')


if __name__ == '__main__':
    unittest.main()
