#!/usr/bin/env python3
"""Audit the public bundle and, when present, its own reachable Git history."""
from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    '.gitignore', 'AGENTS.md', 'ASSET_LICENSE.md', 'LICENSE', 'README.md',
    'SKILL.md', 'agents/openai.yaml', 'assets/base-baozi.jpg',
    'scripts/audit_public_release.py',
}
IMAGE = 'assets/base-baozi.jpg'
IMAGE_SHA256 = '7778245b5148aacd4883e792f643ab171ed0c2744283b6c6de0eab13a3ee0065'
FORBIDDEN_TEXT = (
    '/' + r'Users/[^\s]+', '/' + r'var/folders/[^\s]+', '/' + r'private/(?:tmp|var)/[^\s]+',
    'wx' + r'id_[A-Za-z0-9_]+', r'data:image/[^;]+;base64,',
    r'\bgh[pousr]_[A-Za-z0-9]{20,}', r'\bgithub_pat_[A-Za-z0-9_]{20,}',
    r'\bsk-[A-Za-z0-9_-]{24,}', r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
)


def check_data(name, data):
    if name not in ALLOWED:
        raise ValueError(f'File not allowed: {name}')
    if name == IMAGE:
        if hashlib.sha256(data).hexdigest() != IMAGE_SHA256:
            raise ValueError('Image A differs from the approved public image')
        if not data.startswith(b'\xff\xd8'):
            raise ValueError('Image A is not JPEG')
        i = 2
        while i < len(data):
            if data[i] != 255:
                raise ValueError('Invalid JPEG marker')
            while data[i] == 255:
                i += 1
            marker = data[i]
            i += 1
            if marker in (0xDA, 0xD9):
                break
            length = int.from_bytes(data[i:i + 2], 'big')
            if length < 2 or i + length > len(data):
                raise ValueError('Invalid JPEG segment')
            if marker in (0xE1, 0xED, 0xFE):
                raise ValueError('Image contains EXIF/XMP/IPTC/comment metadata')
            i += length
        return
    text = data.decode('utf-8')
    if any(re.search(pattern, text) for pattern in FORBIDDEN_TEXT):
        raise ValueError(f'Private path, embedded image or secret pattern: {name}')
    # Reject long inline encodings even without a data-URI prefix.
    if re.search(r'[A-Za-z0-9+/]{500,}={0,2}', text):
        raise ValueError(f'Unexpected encoded payload: {name}')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    found = set()
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if rel.parts[0] == '.git':
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink not allowed: {rel}')
        if path.is_file():
            name = rel.as_posix()
            check_data(name, path.read_bytes())
            found.add(name)
    if found != ALLOWED:
        raise ValueError(f'Missing files: {sorted(ALLOWED - found)}')
    commits = []
    if (ROOT / '.git').exists():
        commits = git('rev-list', '--all').decode().splitlines()
        checked = set()
        for commit in commits:
            for entry in git('ls-tree', '-r', '-z', commit).split(b'\0'):
                if not entry:
                    continue
                meta, name_bytes = entry.split(b'\t', 1)
                mode, kind, oid = meta.decode().split()
                name = name_bytes.decode()
                if mode != '100644' or kind != 'blob':
                    raise ValueError(f'Unexpected Git entry: {name}')
                key = (name, oid)
                if key not in checked:
                    check_data(name, git('cat-file', 'blob', oid))
                    checked.add(key)
            emails = git('show', '-s', '--format=%ae%n%ce', commit).decode().splitlines()
            if any(not email.endswith('@users.noreply.github.com')
                   and email != 'noreply@github.com' for email in emails):
                raise ValueError('Commit contains a non-noreply email')
    print(f'PASS: {len(found)} approved files; exactly one approved image A; '
          f'{len(commits)} Git commits checked.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, UnicodeError, IndexError, subprocess.CalledProcessError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
