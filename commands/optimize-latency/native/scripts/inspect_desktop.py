"""Read Desktop version/ASAR entry points without extracting or modifying them."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

KEYS = ('CODEX_CLI_PATH', 'CODEX_TPP_LOCAL_EXECUTOR_CLI_PATH')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def scan_asar(path):
    size = path.stat().st_size
    with path.open('rb') as stream:
        prefix = stream.read(16)
        if len(prefix) != 16:
            raise ValueError('truncated ASAR prefix')
        marker, header_size, payload_size, json_size = struct.unpack('<4I', prefix)
        if (marker != 4 or not 0 < json_size <= 16 * 1024 * 1024
                or payload_size != ((json_size + 7) // 4) * 4
                or header_size != payload_size + 4 or 8 + header_size > size):
            raise ValueError('unsupported ASAR header')
        header = json.loads(stream.read(json_size).decode('utf-8'))
        content_offset = 8 + header_size
        found = []

        def visit(node, prefix=''):
            if not isinstance(node, dict) or not isinstance(node.get('files'), dict):
                raise ValueError('invalid ASAR file index')
            for name, entry in node['files'].items():
                if not isinstance(entry, dict):
                    raise ValueError('invalid ASAR entry')
                logical = f'{prefix}/{name}' if prefix else name
                if 'files' in entry:
                    visit(entry, logical)
                elif (logical.startswith('.vite/build/') and logical.endswith('.js')
                      and name.startswith(('main-', 'bootstrap-', 'early-bootstrap'))
                      and not entry.get('unpacked')):
                    count = entry.get('size')
                    offset = entry.get('offset')
                    if (type(count) is not int or not 0 <= count <= 8 * 1024 * 1024
                            or not isinstance(offset, str) or not offset.isdecimal()):
                        raise ValueError('invalid ASAR script range')
                    start = content_offset + int(offset)
                    if start + count > size:
                        raise ValueError('ASAR script range exceeds archive')
                    stream.seek(start)
                    data = stream.read(count)
                    found.append({'entry': logical, 'sha256': hashlib.sha256(data).hexdigest(),
                                  'observed_keys': [key for key in KEYS if key.encode() in data]})
        visit(header)
    return {'content_offset': content_offset, 'scripts': found,
            'observed_keys': sorted({key for item in found for key in item['observed_keys']})}


def inspect(package, probe_version=False):
    package = Path(package).resolve(strict=True)
    manifest = ET.parse(package / 'AppxManifest.xml').getroot()
    identity = next((node for node in manifest if node.tag.endswith('}Identity')), None)
    if identity is None or identity.get('Name') not in {'OpenAI.Codex', 'OpenAI.CodexBeta'}:
        raise ValueError('expected an explicitly selected Codex Desktop package')
    resources = package / 'app/resources'
    binary = resources / 'codex.exe'
    result = {'package': identity.get('Name'), 'package_version': identity.get('Version'),
              'engine_sha256': digest(binary), 'archive': scan_asar(resources / 'app.asar'),
              'package_modified': False, 'probe_executed': probe_version, 'engine_version': None}
    if probe_version:
        completed = subprocess.run([str(binary), '--version'], capture_output=True,
                                   encoding='utf-8', timeout=10, check=True)
        result['engine_version'] = completed.stdout.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--probe-version', action='store_true', help='also execute the selected engine with --version')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.package, args.probe_version), indent=2))
        return 0
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as error:
        print(f'Desktop inspection: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
