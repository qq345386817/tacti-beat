#!/usr/bin/env python3
"""Dependency-free static contract checks for the published locale pages."""
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import xml.etree.ElementTree as ET
from build_site import VERSION, UPDATED, PRODUCT, METADATA, questions

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
        self.in_body = self.in_title = False
        self.title = ''
        self.text = []
        self.metadata = {}
        self.labels = {}
        self.active_label = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'body': self.in_body = True
        if tag == 'title': self.in_title = True
        if tag == 'meta': self.metadata[a.get('name') or a.get('property')] = a.get('content', '')
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
        if self.in_title: self.title += data
        if self.in_body and not self.script: self.text.append(data)
        if self.active_label: self.labels[self.active_label] += data

    def handle_endtag(self, tag):
        if tag == 'script': self.script = False
        if tag == 'title': self.in_title = False
        if tag == 'body': self.in_body = False
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
        locale = urlsplit(url).path.split('/')[1]
        route = '' if path.name == 'index.html' else path.stem
        assert page.h1 == page.main == 1, (path, 'one h1 and one main required')
        assert page.canonical == url, (path, page.canonical)
        assert page.lang and page.description and page.structured_data, path
        for name in ('og:title', 'twitter:title'):
            assert page.metadata[name] == page.title, (path, name)
        for name in ('og:description', 'twitter:description'):
            assert page.metadata[name] == page.description, (path, name)
        assert page.metadata['twitter:card'] == 'summary', (path, 'square icon preview')
        nodes = page.structured_data[0]['@graph']
        app = next(n for n in nodes if n['@type'] == 'SoftwareApplication')
        web = next(n for n in nodes if n['@type'] == 'WebPage')
        assert app['@id'] == ORIGIN + '/#app' and app['identifier'] == '6769032242', path
        assert app['alternateName'] == METADATA[locale]['name'], path
        assert app['description'] == PRODUCT[locale]['summary'], path
        assert len(app['featureList']) == len(set(app['featureList'])) == 6, path
        assert not {'offers', 'aggregateRating', 'review', 'softwareVersion'} & app.keys(), (path, 'unverified store claims')
        assert web['description'] == page.description and web['name'] == page.title and web['url'] == url, path
        assert web['dateModified'] == entry.find('s:lastmod', ns).text == UPDATED, path
        faqs = [n for n in nodes if n['@type'] == 'FAQPage']
        expected = questions(locale, route)
        assert len(faqs) == bool(expected), (path, 'FAQ coverage')
        if expected:
            assert [q['name'] for q in faqs[0]['mainEntity']] == [q['q'] for q in expected], path
            visible = ' '.join(' '.join(page.text).split())
            for item in expected:
                assert ' '.join(item['q'].split()) in visible and ' '.join(item['a'].split()) in visible, (path, 'schema must match visible FAQ', item['id'])
            assert [q['acceptedAnswer']['text'] for q in faqs[0]['mainEntity']] == [q['a'] for q in expected], path
        if route == 'help' or route in PRODUCT[locale]['routeLeads']:
            visible = ' '.join(' '.join(page.text).split())
            assert all(name in visible for name in METADATA[locale]['presets']), (path, 'preset names differ from App')
            assert all(name in visible for name in METADATA[locale]['labels'].values()), (path, 'control names differ from App')
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
    assert set(PRODUCT) == set(METADATA) == LOCALES
    assert len({PRODUCT[l]['summary'] for l in LOCALES}) == 8
    print('PASS: 64 pages, 8 locales, canonical/hreflang, sitemap dates, social metadata, stable App identity, visible FAQ/schema parity, local links/assets, anchors and downloads.')


if __name__ == '__main__':
    main()
