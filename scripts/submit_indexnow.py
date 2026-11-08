#!/usr/bin/env python3
"""Notify IndexNow only after the matching sitemap is live on production."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://tactibeat.luopeike.com"
KEY_FILE = ROOT / "2906b52713614eb9ac118b81f4e65b42.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def payload():
    key = KEY_FILE.read_text().strip()
    if key != KEY_FILE.stem or len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
        raise ValueError('Invalid domain verification key')
    entries = ET.parse(ROOT / 'sitemap.xml').findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
    urls = [entry.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text for entry in entries]
    if not urls or len(urls) > 10000 or len(urls) != len(set(urls)):
        raise ValueError('Sitemap must contain 1-10000 unique URLs')
    for url in urls:
        p = urlsplit(url)
        if p.scheme != 'https' or p.netloc != urlsplit(ORIGIN).netloc or p.query or p.fragment:
            raise ValueError(f'Non-canonical or foreign URL: {url}')
    return {'host': urlsplit(ORIGIN).netloc, 'key': key,
            'keyLocation': ORIGIN + '/' + KEY_FILE.name, 'urlList': urls}


def request(url, data=None):
    # curl also honors the local SOCKS/proxy setup; no credentials are required.
    args = ['curl', '--silent', '--show-error', '--max-time', '40',
            '--write-out', '\n%{http_code}', url]
    if data is not None:
        args += ['--header', 'Content-Type: application/json; charset=utf-8', '--data-binary', '@-']
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode().strip())
    body, _, status = result.stdout.rpartition(b'\n')
    return int(status), body


def wait_for_production(data, wait_seconds):
    deadline = time.monotonic() + wait_seconds
    expected = (ROOT / 'sitemap.xml').read_bytes()
    while True:
        try:
            status, body = request(data['keyLocation'])
            if status != 200 or body.strip() != data['key'].encode():
                raise RuntimeError(f'Production verification key not ready (HTTP {status})')
            status, body = request(ORIGIN + '/sitemap.xml')
            if status != 200 or body != expected:
                raise RuntimeError(f'Production sitemap does not match this checkout (HTTP {status})')
            return
        except RuntimeError as error:
            if time.monotonic() >= deadline:
                raise RuntimeError(f'No URLs submitted: {error}') from error
            print(f'Waiting for production: {error}', flush=True)
            time.sleep(min(15, max(0, deadline - time.monotonic())))


def submit(data, wait_seconds=0):
    wait_for_production(data, wait_seconds)
    status, body = request(ENDPOINT, json.dumps(data).encode())
    if status not in (200, 202):
        raise RuntimeError(f'IndexNow HTTP {status}: {body.decode(errors="replace")[:500]}')
    detail = 'received' if status == 200 else 'received; key verification pending'
    print(f'IndexNow HTTP {status}: {len(data["urlList"])} canonical URLs {detail}.')
    print('Acceptance is not a guarantee of crawling, indexing or cleared Bing recommendations.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submit', action='store_true', help='Send URLs after checking production; default is a local dry run')
    parser.add_argument('--wait-seconds', type=int, default=0, help='Wait for the production key and matching sitemap')
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 1800:
        parser.error('--wait-seconds must be between 0 and 1800')
    data = payload()
    if args.submit:
        submit(data, args.wait_seconds)
    else:
        print(f'Dry run: {len(data["urlList"])} canonical URLs for {data["host"]}; nothing sent.')


if __name__ == '__main__':
    main()
