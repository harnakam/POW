"""標準ライブラリだけで遊べる、1回勝負のジャンケン。"""
import argparse
import random
import sys

HANDS = ('グー', 'チョキ', 'パー')
ALIASES = dict(zip(('rock', 'scissors', 'paper'), HANDS))


def normalize(value):
    value = value.strip().casefold()
    hand = ALIASES.get(value, value)
    if hand not in HANDS:
        raise ValueError('グー・チョキ・パー、または rock・scissors・paper を入力してください。')
    return hand


def judge(player, computer):
    if player not in HANDS or computer not in HANDS:
        raise ValueError('判定する手が不正です。')
    if player == computer:
        return 'あいこ'
    return 'あなたの勝ち' if (HANDS.index(player) + 1) % 3 == HANDS.index(computer) else 'あなたの負け'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hand', nargs='?', help='グー / チョキ / パー（英語も可）')
    args = parser.parse_args(argv)
    try:
        player = normalize(args.hand if args.hand is not None else input('あなたの手（グー・チョキ・パー）: '))
    except (EOFError, KeyboardInterrupt):
        print('\n終了しました。', file=sys.stderr)
        return 1
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    computer = random.choice(HANDS)
    print(f'あなた: {player} / コンピューター: {computer}')
    print(judge(player, computer))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
