"""ctx PRESET is asynchronous; ctx -wait PRESET runs synchronously."""
import sys
from dispatch import main as dispatch


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {'-h', '--help'}:
        print('ctx PRESET [options]       start asynchronously\n'
              'ctx -wait PRESET [options] run synchronously\n'
              'ctx wait RUN_ID           wait for an existing run\n'
              'ctx result RUN_ID         read current state\n'
              'Codex bridge uses --attached --compact to retain its tool session.')
        return 0
    if args[0] == '-wait':
        if len(args) < 2:
            print('ctx: -wait requires a preset', file=sys.stderr)
            return 2
        return dispatch(args[1:])
    if args[0] in {'wait', 'result', 'plan'}:
        return dispatch(args)
    return dispatch(['start', *args])


if __name__ == '__main__':
    raise SystemExit(main())
