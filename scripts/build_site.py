#!/usr/bin/env python3
"""Refresh static page bodies while preserving canonical routes and reference content."""
import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
COPY = json.loads((ROOT / "content/home.json").read_text())
PRODUCT = json.loads((ROOT / "content/product.json").read_text())
REFERENCE = json.loads((ROOT / "content/help-reference.json").read_text())
METADATA = json.loads((ROOT / "content/store-metadata.json").read_text())["locales"]
LANGUAGES = {"en-US": "English", "zh-Hans": "简体中文", "zh-Hant": "繁體中文", "ja": "日本語", "ko": "한국어", "de-DE": "Deutsch", "fr-FR": "Français", "es-ES": "Español"}
LANGUAGE_LABELS = {"en-US": "Choose language", "zh-Hans": "选择语言", "zh-Hant": "選擇語言", "ja": "言語を選択", "ko": "언어 선택", "de-DE": "Sprache wählen", "fr-FR": "Choisir la langue", "es-ES": "Elegir idioma"}
BREADCRUMB_LABELS = {'en-US': 'Breadcrumb', 'zh-Hans': '当前位置', 'zh-Hant': '目前位置', 'ja': '現在の位置', 'ko': '현재 위치', 'de-DE': 'Brotkrümelnavigation', 'fr-FR': 'Fil d’Ariane', 'es-ES': 'Ruta de navegación'}
STORE = "https://apps.apple.com/app/id6769032242"
VERSION = "20261107"
UPDATED = "2026-11-06T18:27:39Z"
ORIGIN = "https://tactibeat.luopeike.com"
TOPIC_FAQS = {
    'haptic-music-app': ['demos', 'saved'],
    'music-vibration-app': ['device', 'saved'],
    'live-audio-haptics': ['sources', 'other-apps'],
    'tactile-audio-accessibility': ['device', 'limits'],
}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.nav, self.links, self.paragraphs, self.sections = [], [], [], []
        self.depth, self.in_nav = 0, False
        self.anchor, self.paragraph = None, None
        self.language_label = ""
        self.stylesheet_tags = []
        self.h1 = ""
        self.in_h1 = False
        self.title = self.description = self.lang = ''
        self.in_title = False
        self.feed(source)

    def source_offset(self):
        line, col = self.getpos()
        return sum(map(len, self.lines[:line - 1])) + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'title': self.in_title = True
        if tag == 'meta' and a.get('name') == 'description': self.description = a.get('content', '')
        if tag == "link" and a.get("rel") == "stylesheet" and urlsplit(a.get("href", "")).path == "../style/base.css":
            self.stylesheet_tags.append((self.get_starttag_text(), attrs))
        if tag == "nav" and a.get("class") == "nav":
            self.in_nav = True
        if tag == "a":
            self.anchor = {"href": a.get("href", ""), "text": "", "nav": self.in_nav}
        if tag == "p":
            self.paragraph = {"class": a.get("class", ""), "text": ""}
        if tag == "select":
            self.language_label = a.get("aria-label", "")
        if tag == "label":
            self.in_label = True
        if tag == "h1":
            self.in_h1 = True
        if tag == "section":
            if self.depth == 0:
                self.section_start = self.source_offset()
            self.depth += 1

    def handle_data(self, text):
        if self.anchor is not None:
            self.anchor["text"] += text
        if self.paragraph is not None:
            self.paragraph["text"] += text
        if getattr(self, "in_label", False):
            self.language_label = text
        if self.in_h1:
            self.h1 += text
        if self.in_title:
            self.title += text

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = False
        if tag == "label":
            self.in_label = False
        if tag == "h1":
            self.in_h1 = False
        if tag == 'title': self.in_title = False
        if tag == "a" and self.anchor is not None:
            self.links.append(self.anchor)
            if self.anchor["nav"] and len(self.nav) < 4:
                self.nav.append(self.anchor)
            self.anchor = None
        if tag == "p" and self.paragraph is not None:
            self.paragraphs.append(self.paragraph)
            self.paragraph = None
        if tag == "section":
            self.depth -= 1
            if self.depth == 0:
                self.sections.append(self.source[self.section_start:self.source_offset() + len("</section>")])


def link(href, label, cls=""):
    return f'<a href="{escape(href, quote=True)}" class="{cls}">{escape(label)}</a>'


def store_button(label):
    return f'<a class="button primary app-store-button" href="{STORE}" rel="noopener"><img class="store-icon" src="../assets/app-store-icon.svg" alt="" width="22" height="22">{escape(label)}</a>'


class PageHead(HTMLParser):
    def __init__(self, source, title, description, graph):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.title, self.description, self.graph = title, description, graph
        self.in_title = self.in_json = False
        self.feed(source)

    def handle_decl(self, decl):
        self.parts.append('<!' + decl + '>')

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.in_title = tag == 'title' or self.in_title
        self.in_json = (tag == 'script' and a.get('type') == 'application/ld+json') or self.in_json
        if tag == 'title':
            self.parts.append('<title>' + escape(self.title))
            return
        field = a.get('name') or a.get('property')
        if tag == 'meta' and field in ('description', 'og:description', 'twitter:description', 'og:title', 'twitter:title'):
            a['content'] = self.title if field.endswith('title') else self.description
            self.parts.append('<meta ' + ' '.join(k + '="' + escape(v, quote=True) + '"' for k, v in a.items()) + '>')
        elif tag == 'meta' and field in ('og:image', 'twitter:image', 'twitter:card'):
            a['content'] = 'summary' if field == 'twitter:card' else ORIGIN + '/assets/icon-512.png'
            self.parts.append('<meta ' + ' '.join(k + '="' + escape(v, quote=True) + '"' for k, v in a.items()) + '>')
        else:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')
        if tag == 'title': self.in_title = False
        if tag == 'script': self.in_json = False

    def handle_data(self, data):
        if self.in_title:
            return
        elif self.in_json:
            data = json.dumps(self.graph, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        self.parts.append(data)

    def handle_entityref(self, name):
        if not self.in_title: self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        if not self.in_title: self.parts.append('&#' + name + ';')


def header(page, locale, route):
    nav = "".join(f'<a href="{escape(a["href"])}"' + (' aria-current="page"' if a["href"] == (route or "./") else "") + f'>{escape(a["text"])}</a>' for a in page.nav)
    options = "".join(f'<option value="../{key}/{route}"' + (' selected' if key == locale else '') + f'>{name}</option>' for key, name in LANGUAGES.items())
    fallback = "".join(link(f"../{key}/{route}", name) for key, name in LANGUAGES.items())
    return f'''<a class="skip-link" href="#main-content">{escape(COPY[locale]["skip"])}</a>
<header class="site-header"><div class="container topbar">
<a class="brand" href="./"><img src="../assets/apple-touch-icon.png" alt="" width="36" height="36"><span>TactiBeat</span></a>
<nav class="nav" aria-label="TactiBeat">{nav}</nav>
<div class="language-picker topbar-language"><label class="sr-only" for="language-select">{escape(LANGUAGE_LABELS[locale])}</label>
<select id="language-select" class="language-select" onchange="if (this.value) window.location.href = this.value;">{options}</select>
<noscript><div class="language-noscript">{fallback}</div></noscript></div></div></header>'''


def footer(page):
    return '<footer class="site-footer"><div class="container footer-inner"><a class="brand" href="./">TactiBeat</a><nav aria-label="TactiBeat">' + "".join(link(a["href"], a["text"]) for a in page.nav[1:]) + '</nav><span class="small">© TactiBeat</span></div></footer>'


def questions(locale, route):
    items = PRODUCT[locale]['faq']
    if route in ('', 'help'): return items
    return [item for item in items if item['id'] in TOPIC_FAQS.get(route, [])]


def faq_section(locale, route, home_page=False):
    c = PRODUCT[locale]
    entries = ''.join(f'<details id="answer-{item["id"]}"><summary>{escape(item["q"])}</summary><p>{escape(item["a"])}</p></details>' for item in questions(locale, route))
    content = f'<h2>{escape(c["faqHeading"])}</h2><div class="faq-list">{entries}</div>'
    if home_page:
        return f'<section class="home-section"><div class="container reading">{content}</div></section>'
    return f'<section class="section">{content}</section>'


def presets_section(locale):
    c = PRODUCT[locale]
    presets = ''.join(f'<li>{escape(name)}</li>' for name in METADATA[locale]['presets'])
    settings = c['settingsBody'].format_map(METADATA[locale]['labels'])
    return f'<section class="section"><h2>{escape(c["presetsHeading"])}</h2><ul class="preset-list">{presets}</ul><p>{escape(settings)}</p></section>'


def reference_intro(page, locale, title, lead, include_help=True):
    download = next(a['text'] for a in page.links if a['href'] == STORE)
    help_link = link('help', page.nav[1]['text'], 'text-link') if include_help else ''
    return f'<section class="hero"><p class="kicker">TactiBeat</p><h1>{escape(title)}</h1><p class="lead">{escape(lead)}</p><div class="actions">{store_button(download)}{help_link}</div></section>'


def reference_content(page, locale, route):
    c = PRODUCT[locale]
    if route == 'privacy-policy': return '\n'.join(page.sections)
    if route == 'help':
        notice = next(p['text'] for p in page.paragraphs if p['class'] == 'notice')
        steps = ''.join(f'<li>{escape(step)}</li>' for step in c['steps'])
        modes = ''.join(f'<li><strong>{escape(title)}</strong> {escape(body)}</li>' for title, body in COPY[locale]['modes'])
        guidance = ''.join('<section class="section"><h2>' + escape(section['heading']) + '</h2><ul>'
                           + ''.join('<li>' + escape(item) + '</li>' for item in section['items']) + '</ul></section>'
                           for section in REFERENCE[locale])
        return (reference_intro(page, locale, page.h1, c['helpLead'], include_help=False)
                + f'<section class="section"><h2>{escape(c["stepsHeading"])}</h2><ol>{steps}</ol></section>'
                + f'<section class="section"><h2>{escape(COPY[locale]["modeHeading"])}</h2><ul>{modes}</ul></section>'
                + presets_section(locale) + guidance + faq_section(locale, route)
                + f'<section class="section"><p class="notice">{escape(notice)}</p></section>')
    if route == 'support':
        return reference_intro(page, locale, page.h1, c['supportLead']) + '\n'.join(page.sections[1:])
    # Preserve the topic-specific examples; replace stale generic hero and FAQ copy.
    notice = next(p['text'] for p in page.paragraphs if p['class'] == 'notice')
    return (reference_intro(page, locale, page.title.removesuffix(' | TactiBeat'), c['routeLeads'][route])
            + page.sections[1] + presets_section(locale) + faq_section(locale, route)
            + f'<section class="section"><h2>{escape(COPY[locale]["resourcesHeading"])}</h2><div class="resource-links">'
            + ''.join(link(other, Page((ROOT / locale / (other + '.html')).read_text()).title.removesuffix(' | TactiBeat')) for other in TOPIC_FAQS if other != route)
            + f'</div><p class="notice">{escape(notice)}</p></section>')


def structured_data(page, locale, route, title, description):
    canonical = f'{ORIGIN}/{locale}/{route}'
    graph = [
        {'@type': 'WebSite', '@id': ORIGIN + '/#website', 'url': ORIGIN + '/', 'name': 'TactiBeat', 'inLanguage': list(LANGUAGE_LABELS)},
        {'@type': 'SoftwareApplication', '@id': ORIGIN + '/#app', 'name': 'TactiBeat',
         'alternateName': METADATA[locale]['name'], 'operatingSystem': 'iOS', 'applicationCategory': 'MultimediaApplication',
         'identifier': '6769032242', 'url': STORE, 'downloadUrl': STORE,
         'image': ORIGIN + '/assets/icon-512.png', 'description': PRODUCT[locale]['summary'],
         'featureList': METADATA[locale]['presets'], 'inLanguage': list(LANGUAGE_LABELS)},
        {'@type': 'WebPage', '@id': canonical + '#webpage', 'url': canonical, 'name': title,
         'description': description, 'isPartOf': {'@id': ORIGIN + '/#website'},
         'about': {'@id': ORIGIN + '/#app'}, 'inLanguage': page.lang, 'dateModified': UPDATED},
    ]
    if route:
        graph.append({'@type': 'BreadcrumbList', '@id': canonical + '#breadcrumb', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': page.nav[0]['text'], 'item': f'{ORIGIN}/{locale}/'},
            {'@type': 'ListItem', 'position': 2, 'name': title, 'item': canonical}]})
    faqs = questions(locale, route)
    if faqs:
        graph.append({'@type': 'FAQPage', '@id': canonical + '#faq', 'inLanguage': page.lang,
                      'isPartOf': {'@id': canonical + '#webpage'}, 'mainEntity': [
                          {'@type': 'Question', 'name': item['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': item['a']}}
                          for item in faqs]})
    return {'@context': 'https://schema.org', '@graph': graph}


def breadcrumb(page, locale, title):
    return f'<nav class="breadcrumb" aria-label="{BREADCRUMB_LABELS[locale]}">{link("./", page.nav[0]["text"])}<span aria-hidden="true"> / </span><span aria-current="page">{escape(title)}</span></nav>'


def home(page, locale):
    c = COPY[locale]
    download = next(a["text"] for a in page.links if a["href"] == STORE)
    medical = next(p["text"] for p in page.paragraphs if p["class"] in ("notice", "medical-note"))
    compatibility = next(item['a'] for item in PRODUCT[locale]['faq'] if item['id'] == 'sources')
    assets = ["analysis", "live", "stream"]
    presets = ''.join(f'<li>{escape(name)}</li>' for name in METADATA[locale]['presets'])
    modes = "".join(f'''<article class="mode"><div class="mode-title"><span class="mode-number">0{i + 1}</span><h3>{escape(title)}</h3></div>
<p>{escape(description)}</p><a class="screen-link {assets[i]}" href="../assets/screens/{assets[i]}.webp" aria-label="{escape(c['imageLabel'])}: {escape(title)}"><img src="../assets/screens/{assets[i]}.webp" alt="{escape(title)}" width="1320" height="2868" loading="lazy" decoding="async"></a></article>''' for i, (title, description) in enumerate(c["modes"]))
    routes = ["haptic-music-app", "music-vibration-app", "live-audio-haptics", "tactile-audio-accessibility"]
    resources = ""
    for route in routes:
        label = next((a["text"] for a in page.links if a["href"] == route), None)
        if label is None:
            label = Page((ROOT / locale / (route + ".html")).read_text()).h1
        resources += link(route, label)
    return f'''{header(page, locale, '')}
<main id="main-content">
<section class="home-hero"><div class="container hero-copy"><h1>TactiBeat</h1>
<p class="tagline">{escape(c['tagline'])}</p><p class="lead">{escape(PRODUCT[locale]['summary'])}</p>
<div class="actions">{store_button(download)}{link('#modes', c['explore'], 'text-link')}</div>
<figure class="hero-art"><img src="../assets/illustrations/sound-to-touch-v1.webp" alt="{escape(c['heroAlt'])}" width="2172" height="724" fetchpriority="high" decoding="async"><figcaption class="hero-caption">{escape(c['heroLabel'])}</figcaption></figure>
</div></section>
<section class="home-section modes-section" id="modes"><div class="container"><div class="section-heading"><h2>{escape(c['modeHeading'])}</h2></div>
<div class="mode-grid">{modes}</div><p class="screen-note">{escape(c['screenNote'])}</p></div></section>
<section class="home-section tuning-section"><div class="container tuning-grid"><div><h2>{escape(c['tuneHeading'])}</h2><p class="lead">{escape(c['tuneBody'])}</p><ul class="preset-list">{presets}</ul>{link('help', c['tuneLink'], 'text-link')}</div>
<a class="tuning-image" href="../assets/screens/tuning.webp" aria-label="{escape(c['imageLabel'])}"><img src="../assets/screens/tuning.webp" alt="{escape(c['tuneAlt'])}" width="1320" height="2868" loading="lazy" decoding="async"></a></div></section>
<section class="home-section compatibility"><div class="container reading"><h2>{escape(c['compatHeading'])}</h2><p>{escape(c['compatDevice'])}</p><p>{escape(compatibility)}</p><p class="medical-note">{escape(medical)}</p></div></section>
{faq_section(locale, '', home_page=True)}
<section class="home-section resources"><div class="container"><h2>{escape(c['resourcesHeading'])}</h2><div class="resource-links">{resources}</div></div></section>
<section class="download-band"><div class="container"><img src="../assets/apple-touch-icon.png" alt="" width="64" height="64" loading="lazy"><h2>{escape(c['endHeading'])}</h2>{store_button(download)}</div></section>
</main>{footer(page)}'''


def main():
    for locale in LANGUAGES:
        files = sorted((ROOT / locale).glob("*.html"))
        parsed = {p.name: Page(p.read_text()) for p in files}
        for path in files:
            source = path.read_text()
            page = parsed[path.name]
            assert len(page.nav) == 4, path
            head, marker, _ = source.partition("<body")
            assert marker and "</head>" in head, path
            assert len(page.stylesheet_tags) == 1, path
            for original, attrs in page.stylesheet_tags:
                updated = [(key, f'../style/base.css?v={VERSION}' if key == 'href' else value) for key, value in attrs]
                tag = '<link ' + ' '.join(key + '="' + escape(value, quote=True) + '"' for key, value in updated) + '>'
                head = head.replace(original, tag)
            route = '' if path.name == 'index.html' else path.stem
            c = PRODUCT[locale]
            title = c['seoTitle'] if not route else c['helpTitle'] if route == 'help' else page.title
            description = c['summary'] if not route else c['helpLead'] if route == 'help' else c['supportLead'] if route == 'support' else c['routeLeads'].get(route, page.description)
            head = ''.join(PageHead(head, title, description, structured_data(page, locale, route, title, description)).parts)
            if path.name == "index.html":
                body = home(page, locale)
                css = ' class="home-page"'
            else:
                body = header(page, locale, path.stem) + '<main id="main-content" class="container document">' + breadcrumb(page, locale, title) + reference_content(page, locale, route) + '</main>' + footer(page)
                css = ''
            path.write_text(head + '<body' + css + '>\n' + body + '\n</body>\n</html>\n')
    ns, html_ns = 'http://www.sitemaps.org/schemas/sitemap/0.9', 'http://www.w3.org/1999/xhtml'
    ET.register_namespace('', ns)
    ET.register_namespace('xhtml', html_ns)
    sitemap = ET.parse(ROOT / 'sitemap.xml')
    for entry in sitemap.getroot().findall(f'{{{ns}}}url'):
        entry.find(f'{{{ns}}}lastmod').text = UPDATED
    sitemap.write(ROOT / 'sitemap.xml', encoding='UTF-8', xml_declaration=True)
    print('Updated 64 localized pages and sitemap; canonical routes and privacy-policy sections preserved.')


if __name__ == "__main__":
    main()
