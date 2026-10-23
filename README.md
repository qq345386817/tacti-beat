# TactiBeat Website

Static, eight-locale website for TactiBeat. Production is served by the existing Cloudflare Pages project `tacti-beat`, connected to this repository's `main` branch.

## Editing

- Home copy: `content/home.json`.
- Shared layout generator: `scripts/build_site.py`.
- Shared visual tokens, responsive layout and reference-page typography: `style/base.css`.
- Reference page content and SEO metadata: the localized HTML files.

Run `python3 scripts/build_site.py` after editing home copy or the shared layout generator. It preserves existing page heads, canonical routes, hreflang and all reference-page sections. Generated HTML remains committed so production needs no JavaScript framework or build step. Run `python3 scripts/check_site.py` before publishing.

The App palette comes from `HapticMusic/BrandPalette.swift` in the parent App project. Local editable design-system and design-canvas artifacts are kept outside this deployable repository. The App's six identity colors are unchanged; website text and surface colors are adjusted for contrast. Use full-width bands and quiet reading layouts, not nested decorative cards.

## Images

`assets/screens/` contains losslessly encoded WebP versions of actual App screenshots from the parent project's October 19 UI validation. They are intentionally versioned product website assets, not test reports. They show the Simplified Chinese App interface; this is stated in every locale. Live/stream activity is demonstration data, also explicitly labeled. The hero shows only a waveform detail; the mode section links to the complete source screenshot. No generated UI or invented device frame is used.

## Publishing

Commit and push `main` after checks pass. Confirm the matching Git commit reaches a successful **production** deployment in Cloudflare Pages, then check the custom domain, not only `pages.dev`. Keep all 64 canonical URLs and their reciprocal hreflang links. Update sitemap `lastmod` when page content changes; use the content change date, not an arbitrary fetch date.

No API tokens, environment files, build caches, design-editor blobs or browser-test artifacts belong in this repository.
