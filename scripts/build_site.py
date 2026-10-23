#!/usr/bin/env python3
"""Refresh static page bodies while preserving canonical routes and reference content."""
import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = json.loads((ROOT / "content/home.json").read_text())
LANGUAGES = {"en-US": "English", "zh-Hans": "简体中文", "zh-Hant": "繁體中文", "ja": "日本語", "ko": "한국어", "de-DE": "Deutsch", "fr-FR": "Français", "es-ES": "Español"}
LANGUAGE_LABELS = {"en-US": "Choose language", "zh-Hans": "选择语言", "zh-Hant": "選擇語言", "ja": "言語を選択", "ko": "언어 선택", "de-DE": "Sprache wählen", "fr-FR": "Choisir la langue", "es-ES": "Elegir idioma"}
STORE = "https://apps.apple.com/app/id6769032242"
VERSION = "20261024"


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.nav, self.links, self.paragraphs, self.sections = [], [], [], []
        self.depth, self.in_nav = 0, False
        self.anchor, self.paragraph = None, None
        self.language_label = ""
        self.h1 = ""
        self.in_h1 = False
        self.feed(source)

    def source_offset(self):
        line, col = self.getpos()
        return sum(map(len, self.lines[:line - 1])) + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
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

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = False
        if tag == "label":
            self.in_label = False
        if tag == "h1":
            self.in_h1 = False
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


class HomeHead(HTMLParser):
    def __init__(self, source, copy):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.copy = copy
        self.in_title = self.in_json = False
        self.feed(source)

    def handle_decl(self, decl):
        self.parts.append('<!' + decl + '>')

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.in_title = tag == 'title' or self.in_title
        self.in_json = (tag == 'script' and a.get('type') == 'application/ld+json') or self.in_json
        field = a.get('name') or a.get('property')
        if tag == 'meta' and field in ('description', 'og:description', 'twitter:description', 'og:title', 'twitter:title'):
            a['content'] = ('TactiBeat | ' + self.copy['tagline']) if field.endswith('title') else self.copy['lead']
            self.parts.append('<meta ' + ' '.join(k + '="' + escape(v, quote=True) + '"' for k, v in a.items()) + '>')
        else:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')
        if tag == 'title': self.in_title = False
        if tag == 'script': self.in_json = False

    def handle_data(self, data):
        if self.in_title:
            data = escape('TactiBeat | ' + self.copy['tagline'])
        elif self.in_json:
            payload = json.loads(data)
            for node in payload.get('@graph', []):
                if node.get('@type') in ('WebPage', 'SoftwareApplication'):
                    node['description'] = self.copy['lead']
                if node.get('@type') == 'WebPage':
                    node['name'] = 'TactiBeat | ' + self.copy['tagline']
            data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')


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


def home(page, help_page, locale):
    c = COPY[locale]
    download = next(a["text"] for a in page.links if a["href"] == STORE)
    medical = next(p["text"] for p in page.paragraphs if p["class"] in ("notice", "medical-note"))
    compatibility = next(p["text"] for p in help_page.paragraphs if "HLS" in p["text"])
    assets = ["analysis", "live", "stream"]
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
<p class="tagline">{escape(c['tagline'])}</p><p class="lead">{escape(c['lead'])}</p>
<div class="actions">{store_button(download)}{link('#modes', c['explore'], 'text-link')}</div>
<figure class="waveform-preview"><img src="../assets/screens/analysis.webp" alt="{escape(c['waveAlt'])}" width="1320" height="2868" fetchpriority="high" decoding="async"></figure>
<p class="wave-caption">{escape(c['waveLabel'])}</p></div></section>
<section class="home-section modes-section" id="modes"><div class="container"><div class="section-heading"><h2>{escape(c['modeHeading'])}</h2></div>
<div class="mode-grid">{modes}</div><p class="screen-note">{escape(c['screenNote'])}</p></div></section>
<section class="home-section tuning-section"><div class="container tuning-grid"><div><h2>{escape(c['tuneHeading'])}</h2><p class="lead">{escape(c['tuneBody'])}</p>{link('help', c['tuneLink'], 'text-link')}</div>
<a class="tuning-image" href="../assets/screens/tuning.webp" aria-label="{escape(c['imageLabel'])}"><img src="../assets/screens/tuning.webp" alt="{escape(c['tuneAlt'])}" width="1320" height="2868" loading="lazy" decoding="async"></a></div></section>
<section class="home-section compatibility"><div class="container reading"><h2>{escape(c['compatHeading'])}</h2><p>{escape(c['compatDevice'])}</p><p>{escape(compatibility)}</p><p class="medical-note">{escape(medical)}</p></div></section>
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
            head = head.replace('../style/base.css"', f'../style/base.css?v={VERSION}"')
            if path.name == "index.html":
                head = ''.join(HomeHead(head, COPY[locale]).parts)
                body = home(page, parsed["help.html"], locale)
                css = ' class="home-page"'
            else:
                body = header(page, locale, path.stem) + '<main id="main-content" class="container document">' + '\n'.join(page.sections) + '</main>' + footer(page)
                css = ''
            path.write_text(head + '<body' + css + '>\n' + body + '\n</body>\n</html>\n')
    print("Updated 64 localized pages; canonical routes, structured data and reference paragraphs preserved.")


if __name__ == "__main__":
    main()
