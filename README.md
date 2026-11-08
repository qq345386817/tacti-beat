# TactiBeat Website

Static, eight-locale website for TactiBeat. Production is served by the existing Cloudflare Pages project `tacti-beat`, connected to this repository's `main` branch.

## Editing

- Home copy: `content/home.json`.
- Product summaries, help steps, source boundaries and questions: `content/product.json`.
- Retained rhythm, material-selection and tuning advice: `content/help-reference.json`.
- Public App copy and exact localized preset names: `content/store-metadata.json`.
- Shared layout generator: `scripts/build_site.py`.
- Shared visual tokens, responsive layout and reference-page typography: `style/base.css`.
- Topic examples, support contact and privacy-policy sections: the localized HTML files.

When App metadata changes, run `python3 scripts/sync_metadata.py` from this website
checkout inside the App project. Only names, subtitles, descriptions, promotional
copy, six preset names and the referenced App control names are imported. Keywords, private review information and
credentials are never exported. Source hashes are for drift detection, not proof
that local metadata has been published in the App Store. A standalone checkout can
pass `--app-root /path/to/HapticMusic` explicitly.

Run `python3 scripts/build_site.py` after editing content. It refreshes localized
titles/descriptions, social previews, App/WebPage/FAQ/Breadcrumb entities and visible
product/help sections while preserving canonical routes, hreflang and legal-policy
sections. The generator is idempotent. Generated HTML remains committed, with no
client-side rendering or production build dependency.

Before publishing:

```sh
python3 scripts/sync_metadata.py --check  # when the parent App checkout is available
python3 scripts/build_site.py
python3 scripts/check_site.py
```

Update `UPDATED` in the generator only when publishing actual content changes; it
is used consistently for page `dateModified` and sitemap `lastmod`. Do not stamp
every build with the current time. The checks cover all 64 canonical pages and
require FAQ schema answers to match the visible localized answers exactly.

Search-only descriptions can be supplied in `content/product.json` via
`seoDescriptions` (the empty route is the homepage). These update the meta,
social and WebPage descriptions without lengthening the visible hero summary.
Use natural localized text rather than padding CJK copy to an English character target.

## Search And AI Retrieval

The site presents four bundled demos, six presets, separate file/microphone/direct
URL paths, saved-result settings and device requirements in crawlable HTML. Each
topic page answers a distinct intent and links to related pages. HLS is playback
only, protected music-service streams are unsupported, and Live Sound does not
capture other apps' internal audio. These limits remain visible, not only in JSON-LD.
Unreleased Duo layout changes are not marketed as publicly available features.

Stable App IDs and localized descriptions help disambiguate the product. No
unverified price, ratings, release version, "first/only" or medical benefit is
inserted into structured data. Square App icons use a square social-card format.
Existing privacy disclosures remain unchanged.

Google's [AI search guidance](https://developers.google.com/search/docs/appearance/ai-features)
does not require special AI markup or an AI text file. Clear answers, crawlability,
internal links and accurate structured data are the focus here; adding FAQ schema
does not promise FAQ rich results, indexing or AI citations. Track actual discovery
in Search Console rather than interpreting validator success as a ranking gain.

The App palette comes from `HapticMusic/BrandPalette.swift` in the parent App project. Local editable design-system and design-canvas artifacts are kept outside this deployable repository. The App's six identity colors are unchanged; website text and surface colors are adjusted for contrast. Use full-width bands and quiet reading layouts, not nested decorative cards.

## Images

`assets/illustrations/sound-to-touch-v1.webp` is a conceptual brand illustration generated with the built-in image-generation tool. It visualizes sound becoming tactile pulses, not measured audio or an actual App screen. It has a transparent background, no embedded text, and an explicitly localized concept-illustration caption in every locale. The prompt and provenance are recorded alongside the asset.

`assets/screens/` contains losslessly encoded WebP versions of actual App screenshots from the parent project's October 19 UI validation. They are intentionally versioned product website assets, not test reports. They show the Simplified Chinese App interface; this is stated in every locale. File analysis comes from a real bundled Demo; Live/Stream activity uses demonstration data, also explicitly labeled. These screenshots remain below the conceptual hero so visitors can inspect the real interface. No generated UI or invented device frame is used.

## Publishing

Commit and push `main` after checks pass. Confirm the matching Git commit reaches a successful **production** deployment in Cloudflare Pages, then check the custom domain, not only `pages.dev`. Keep all 64 canonical URLs and their reciprocal hreflang links. Update sitemap `lastmod` when page content changes; use the content change date, not an arbitrary fetch date.

No API tokens, environment files, build caches, design-editor blobs or browser-test artifacts belong in this repository.

## Bing And IndexNow

`2906b52713614eb9ac118b81f4e65b42.txt` is the public, domain-scoped IndexNow
verification file, not a Cloudflare or Microsoft account API credential. Keep it
deployed at the site root; do not add it to the sitemap or robots disallow rules.

Cloudflare Pages publishes directly from the linked GitHub repository. No GitHub
Actions deployment or notification workflow is required. After a content update,
the manual IndexNow script waits for the production key and exact sitemap to match
the checkout, then submits its 64 canonical URLs. It requires no account API token.
Failed checks or submissions exit with an error instead of reporting success.

For a local dry run, offline tests, or a manual post-deploy notification:

```sh
python3 scripts/submit_indexnow.py
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/submit_indexnow.py --submit --wait-seconds 900
```

HTTP 200 means received; HTTP 202 means received with key verification pending.
Neither guarantees indexing, rankings or immediate removal of cached Bing warnings.
Check the live URL inspection separately. Decorative icons retain empty alt with
`aria-hidden`, while the standalone download-area App icon has an informative alt.
The high-quality inbound-link recommendation needs genuine third-party mentions;
do not manufacture links or add hidden keyword content to silence it.
