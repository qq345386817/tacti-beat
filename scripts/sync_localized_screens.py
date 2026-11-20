#!/usr/bin/env python3
"""Export website WebPs from the app's native iPhone capture, not store mockups."""

import argparse
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = {'analysis': 'compare', 'tuning': 'feel-check', 'live': 'test-haptic', 'stream': 'stream'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-root', type=Path, default=ROOT.parent / 'maestro_screenshots')
    parser.add_argument('locales', nargs='+', choices=('ar', 'hi', 'ru'))
    args = parser.parse_args()
    paths = {
        ROOT / 'assets/screens' / locale / f'{scene}.webp':
            args.raw_root / f'iphone17promax_{locale}_light_{raw_scene}.png'
        for locale in args.locales for scene, raw_scene in SCENES.items()
    }
    for source in paths.values():
        with source.open('rb') as stream:
            header = stream.read(26)
        if (header[:8] != b'\x89PNG\r\n\x1a\n'
                or struct.unpack('>II', header[16:24]) != (1320, 2868)
                or header[25] != 2):
            raise ValueError(f'Expected native iPhone RGB capture: {source}')
    with tempfile.TemporaryDirectory(prefix='tactibeat-webp-') as tmp:
        staging = []
        for target, source in paths.items():
            output = Path(tmp) / f'{target.parent.name}-{target.name}'
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-frames:v', '1',
                            '-c:v', 'libwebp', '-quality', '88', str(output)], check=True)
            staging.append((target, output))
        for target, output in staging:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(output.read_bytes())
    print(f'Exported {len(paths)} localized website screenshots.')


if __name__ == '__main__':
    main()
