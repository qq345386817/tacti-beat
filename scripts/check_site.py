#!/usr/bin/env python3
"""Dependency-free static contract checks for the published locale pages."""
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import xml.etree.ElementTree as ET
from build_site import VERSION

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://tactibeat.luopeike.com"
LOCALES = {"en-US", "zh-Hans", "zh-Hant", "de-DE", "fr-FR", "es-ES", "ja", "ko"}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids, self.targets, self.images, self.alternates, self.options = [], [], [], {}, []
        self.h1 = self.main = 0
        self.canonical = self.lang = self.description = self.label = ""
        self.structured_data = []
        self.script = False
        self.labels = {}
        self.active_label = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'h1': self.h1 += 1
        if tag == 'main': self.main += 1
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical = a['href']
        if tag == 'link' and a.get('rel') == 'alternate': self.alternates[a['hreflang']] = a['href']
        if tag == 'meta' and a.get('name') == 'description': self.description = a.get('content', '')
        if tag == 'meta' and a.get('name') == 'robots': assert 'noindex' not in a.get('content', '')
        if tag in ('a', 'link'): self.targets.append(a.get('href', ''))
        if tag in ('img', 'script') and 'src' in a: self.targets.append(a['src'])
        if tag == 'img':
            assert 'alt' in a, a
            self.images.append(a)
        if tag == 'option': self.options.append(a)
        if tag == 'label':
            self.active_label = a.get('for')
            self.labels[self.active_label] = ''
        if tag == 'script': self.script = a.get('type') == 'application/ld+json'

    def handle_data(self, data):
        if self.script: self.structured_data.append(json.loads(data))
        if self.active_label: self.labels[self.active_label] += data

    def handle_endtag(self, tag):
        if tag == 'script': self.script = False
        if tag == 'label': self.active_label = None


def file_for(url):
    path = unquote(urlsplit(url).path).lstrip('/')
    p = ROOT / path
    if p.is_dir(): return p / 'index.html'
    if not p.suffix: return p.with_suffix('.html')
    return p


def main():
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'h': 'http://www.w3.org/1999/xhtml'}
    entries = ET.parse(ROOT / 'sitemap.xml').findall('s:url', ns)
    urls = [e.find('s:loc', ns).text for e in entries]
    assert len(urls) == len(set(urls)) == 64
    assert {urlsplit(u).path.split('/')[1] for u in urls} == LOCALES
    parsed = {}
    for url, entry in zip(urls, entries):
        path = file_for(url)
        assert path.is_file(), path
        page = Page(path.read_text())
        assert page.h1 == page.main == 1, (path, 'one h1 and one main required')
        assert page.canonical == url, (path, page.canonical)
        assert page.lang and page.description and page.structured_data, path
        assert f'../style/base.css?v={VERSION}' in page.targets, (path, 'stale stylesheet version')
        assert not [i for i, n in Counter(page.ids).items() if n > 1], path
        assert page.labels.get('language-select', '').strip(), (path, 'language label')
        assert len(page.options) == 8 and sum('selected' in o for o in page.options) == 1, path
        assert page.alternates == {e.attrib['hreflang']: e.attrib['href'] for e in entry.findall('h:link', ns)}, path
        assert len(page.alternates) == 9 and url in page.alternates.values(), path
        for target in page.targets:
            full = urljoin(url, target)
            parts = urlsplit(full)
            if parts.netloc != urlsplit(ORIGIN).netloc: continue
            p = file_for(full)
            assert p.is_file(), (path, 'broken local target', target)
            if parts.fragment:
                target_page = page if p == path else Page(p.read_text())
                assert parts.fragment in target_page.ids, (path, 'missing anchor', target)
        assert any(t == 'https://apps.apple.com/app/id6769032242' for t in page.targets), path
        if path.name == 'index.html':
            assert 'HLS' in path.read_text(), path
            assert any(i.get('fetchpriority') == 'high' for i in page.images), path
            hero = [i for i in page.images if i.get('fetchpriority') == 'high']
            assert len(hero) == 1 and hero[0]['src'] == '../assets/illustrations/sound-to-touch-v1.webp', path
            assert hero[0]['width'] == '2172' and hero[0]['height'] == '724', path
        parsed[url] = page
    for url, page in parsed.items():
        for alternate in page.alternates.values():
            assert alternate in parsed and parsed[alternate].alternates == page.alternates, (url, 'non-reciprocal hreflang')
    print('PASS: 64 pages, 8 locales, canonical/hreflang reciprocity, structured data, local links/assets, anchors, download links, language labels and unique IDs.')


if __name__ == '__main__':
    main()
