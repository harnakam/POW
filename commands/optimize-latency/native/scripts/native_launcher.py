"""Launch the receipt-verified custom Codex with process-local native admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def concurrency(value: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("concurrency must be an integer from 1 to 1024") from error
    if not 1 <= result <= 1024:
        raise argparse.ArgumentTypeError("concurrency must be an integer from 1 to 1024")
    return result


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=root / "package/bin/codex.exe")
    parser.add_argument("--receipt", type=Path, default=root / "build-receipt.json")
    parser.add_argument("--concurrency", type=concurrency, default=4, help="primary leaf slots (1..1024); Guardian reviews have one additional reserved slot")
    parser.add_argument("--verify-only", action="store_true", help="verify artifact identity and print JSON without launching")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="arguments after -- are passed unchanged to Codex")
    args = parser.parse_args(argv)
    try:
        binary = args.binary.resolve(strict=True)
        if not binary.is_file():
            raise ValueError("binary must name an existing executable file")
        receipt = json.loads(args.receipt.read_text(encoding="utf-8-sig"))
        expected = receipt["binary"]["sha256"]
        if receipt["scheduler"]["environment_variable"] != "CODEX_NATIVE_TOOL_CONCURRENCY":
            raise ValueError("receipt does not identify this native scheduler build")
        digest = hashlib.sha256()
        with binary.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if not isinstance(expected, str) or actual != expected.lower():
            raise ValueError("binary SHA-256 does not match the native build receipt")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(f"native build verification failed: {error}")
    if args.verify_only:
        print(json.dumps({"binary": str(binary), "sha256": actual, "concurrency": args.concurrency, "verification": "artifact identity; does not prove live tool dispatch"}))
        return 0
    child_environment = os.environ.copy()
    child_environment["CODEX_NATIVE_TOOL_CONCURRENCY"] = str(args.concurrency)
    forwarded = args.args[1:] if args.args[:1] == ["--"] else args.args
    try:
        result = subprocess.run([str(binary), *forwarded], env=child_environment, check=False)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        print(f"could not launch verified native Codex: {error}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    sys.exit(main())
