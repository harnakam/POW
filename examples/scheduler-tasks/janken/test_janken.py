from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import janken


class JankenTests(unittest.TestCase):
    def test_all_nine_outcomes(self):
        expected = {
            ('グー', 'グー'): 'あいこ', ('グー', 'チョキ'): 'あなたの勝ち',
            ('グー', 'パー'): 'あなたの負け', ('チョキ', 'グー'): 'あなたの負け',
            ('チョキ', 'チョキ'): 'あいこ', ('チョキ', 'パー'): 'あなたの勝ち',
            ('パー', 'グー'): 'あなたの勝ち', ('パー', 'チョキ'): 'あなたの負け',
            ('パー', 'パー'): 'あいこ',
        }
        for hands, result in expected.items():
            with self.subTest(hands=hands):
                self.assertEqual(janken.judge(*hands), result)

    def test_aliases_and_whitespace(self):
        for value, hand in [(' ROCK ', 'グー'), ('scissors', 'チョキ'), ('paper', 'パー'),
                            (' グー ', 'グー'), ('チョキ', 'チョキ'), ('パー', 'パー')]:
            with self.subTest(value=value):
                self.assertEqual(janken.normalize(value), hand)

    def test_invalid_hands_are_rejected(self):
        for invalid in ('', 'stone', 'じゃんけん'):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                janken.normalize(invalid)
        for hands in [('bad', 'グー'), ('グー', 'bad')]:
            with self.subTest(hands=hands), self.assertRaises(ValueError):
                janken.judge(*hands)

    def invoke(self, args, answer=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), \
                patch('builtins.input', return_value=answer), \
                patch('janken.random.choice', return_value='チョキ') as choice:
            code = janken.main(args)
        return code, stdout.getvalue(), stderr.getvalue(), choice

    def test_argument_round(self):
        code, output, error, choice = self.invoke(['rock'])
        self.assertEqual(code, 0)
        self.assertIn('あなた: グー / コンピューター: チョキ', output)
        self.assertIn('あなたの勝ち', output)
        self.assertEqual(error, '')
        choice.assert_called_once_with(janken.HANDS)

    def test_interactive_round(self):
        code, output, _, _ = self.invoke([], answer='パー')
        self.assertEqual(code, 0)
        self.assertIn('あなたの負け', output)

    def test_invalid_input_does_not_play(self):
        code, output, error, choice = self.invoke(['invalid'])
        self.assertEqual(code, 2)
        self.assertEqual(output, '')
        self.assertIn('グー', error)
        choice.assert_not_called()

    def test_eof_and_interrupt_exit_cleanly(self):
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error), patch('builtins.input', side_effect=error), \
                    redirect_stderr(io.StringIO()):
                self.assertEqual(janken.main([]), 1)

    def test_real_process_entrypoint(self):
        process = subprocess.run(
            [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).with_name('janken.py')), 'rock'],
            capture_output=True, text=True, encoding='utf-8', timeout=20,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('あなた: グー / コンピューター:', process.stdout)
        self.assertTrue(any(result in process.stdout for result in
                            ('あいこ', 'あなたの勝ち', 'あなたの負け')))


if __name__ == '__main__':
    unittest.main()
