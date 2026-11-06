#!/usr/bin/env python3
"""Snapshot public App copy and preset names; never import credentials or review contacts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {'en-US': 'en', 'zh-Hans': 'zh-Hans', 'zh-Hant': 'zh-Hant',
           'ja': 'ja', 'ko': 'ko', 'de-DE': 'de', 'fr-FR': 'fr', 'es-ES': 'es'}
FIELDS = {'name': 30, 'subtitle': 30, 'description': 4000, 'promotional_text': 170}
PRESETS = ['Balanced Mix', 'Deep Bass', 'Beat Focus', 'Crisp Detail', 'Texture Feel', 'Voice & Melody']
LABELS = {'feelCheck': 'Feel Check', 'testHaptic': 'Test Haptic', 'pocketMode': 'Pocket Mode'}


def snapshot(app_root):
    catalog_path = app_root / 'HapticMusic/Localizable.xcstrings'
    catalog = json.loads(catalog_path.read_text())['strings']
    result = {'schema_version': 1, 'app_id': '6769032242', 'bundle_id': 'com.luopeike.HapticMusic',
              'source': 'Local App metadata and localization catalog; not proof of App Store publication',
              'source_sha256': {}, 'locales': {}}
    sources = [catalog_path]
    for locale, language in LOCALES.items():
        values = {}
        for field, limit in FIELDS.items():
            path = app_root / 'fastlane/metadata_ios' / locale / f'{field}.txt'
            value = path.read_text().strip()
            if not value or len(value) > limit:
                raise ValueError(f'{locale}/{field}: {len(value)} characters, limit {limit}')
            values[field] = value
            sources.append(path)
        values['presets'] = [catalog[key]['localizations'][language]['stringUnit']['value'] for key in PRESETS]
        values['labels'] = {name: catalog[key]['localizations'][language]['stringUnit']['value'] for name, key in LABELS.items()}
        result['locales'][locale] = values
    for path in sources:
        result['source_sha256'][str(path.relative_to(app_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, default=ROOT.parent)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content = json.dumps(snapshot(args.app_root), ensure_ascii=False, indent=2) + '\n'
    destination = ROOT / 'content/store-metadata.json'
    if args.check:
        if not destination.exists() or destination.read_text() != content:
            raise SystemExit('Website metadata snapshot is stale; run scripts/sync_metadata.py')
        print('PASS: 8 locale snapshots match App metadata and preset names')
    else:
        destination.write_text(content)
        print('Synced public copy and six preset names for 8 locales; no keywords, contacts or credentials exported')


if __name__ == '__main__':
    main()
