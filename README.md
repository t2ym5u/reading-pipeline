# reading-pipeline

> ⚠️ **Not stable — tested on Kobo only.** The KOReader side relies on [opdsdir](https://github.com/t2ym5u/koreader-plugins/tree/master/opdsdir.koplugin), an experimental monkey-patch plugin. The pipeline itself (GitHub Actions) is stable for general use.

A personal reading pipeline: save articles or EPUBs from anywhere, read them on your e-reader.

```
[Mobile / Desktop]
  Share URL or upload EPUB
       ↓
[GitHub Issues / Contents API]
       ↓
[GitHub Actions]
  fetch article → EPUB (trafilatura + pandoc)
  rename to UUID
  encrypt (AES-256-CBC)
  update encrypted catalog (OPDS)
       ↓
[GitHub Pages]
  serves catalog.xml.enc + library/*.epub (encrypted)
       ↓
[KOReader — OPDS browser + opdsdir plugin]
  decrypts catalog in memory
  downloads + decrypts EPUB
  opens normally
```

---

## Features

- **Save articles** from any browser or app (iOS Share Sheet, bookmarklet, web page)
- **Upload EPUBs** directly from mobile or desktop
- **AES-256 encryption** — filenames (UUID), content, index and catalog are all encrypted
- **OPDS catalog** — transparent integration with KOReader's built-in browser
- **Zero infrastructure** — runs entirely on GitHub Actions + GitHub Pages (free tier)

---

## Quick start

See [SETUP.md](SETUP.md) for the full installation guide.

**Summary:**
1. Fork or clone this repo → enable GitHub Pages (main branch)
2. Create a `EPUB_ENCRYPT_KEY` repository secret (your encryption passphrase)
3. Create a GitHub fine-grained token (`Issues: write` + `Contents: write`)
4. Open [save.html](https://t2ym5u.github.io/reading-pipeline/save.html), enter your token once
5. In KOReader: add OPDS catalog `https://t2ym5u.github.io/reading-pipeline/catalog.xml.enc`
6. Install [opdsdir](https://github.com/t2ym5u/koreader-plugins/tree/master/opdsdir.koplugin) on KOReader, set the encryption key

---

## Saving content

### Articles (URL → EPUB)

**Mobile (iOS):** Create a Shortcut that opens a GitHub Issue with the URL as title → the Action fetches the article, converts to EPUB, encrypts and publishes.

**Desktop:** Open [save.html](https://t2ym5u.github.io/reading-pipeline/save.html) → paste URL → Save.

**Bookmarklet:**
```javascript
javascript:location.href='https://t2ym5u.github.io/reading-pipeline/save.html?url='+encodeURIComponent(location.href)
```

### EPUBs

**Mobile / Desktop:** Open [save.html](https://t2ym5u.github.io/reading-pipeline/save.html) → Upload EPUB section → pick file.

**iOS Shortcut:** Receive file from Share Sheet → base64 encode → PUT to GitHub Contents API.

**Command line:**
```bash
cp mybook.epub library/
git add library/mybook.epub && git commit -m "add: mybook" && git push
# catalog.yml automatically renames to UUID and encrypts
```

---

## Encryption

When `EPUB_ENCRYPT_KEY` is set as a repository secret:

| File | Stored as |
|---|---|
| EPUB content | AES-256-CBC encrypted, UUID filename |
| `index.tsv` | `index.tsv.enc` (titles, URLs, dates) |
| `catalog.xml` | `catalog.xml.enc` |

The key never appears in the repo. It lives in GitHub Secrets (server) and in KOReader's OPDS settings (device).

**Threat model:** protects against casual browsing of the public repo. Does not protect against someone with physical access to the device (key is stored in plaintext in KOReader settings).

---

## Stack

| Component | Technology |
|---|---|
| Article extraction | [trafilatura](https://github.com/adbar/trafilatura) |
| EPUB generation | [pandoc](https://pandoc.org/) |
| Encryption | openssl AES-256-CBC (GitHub runner + device) |
| Catalog format | [OPDS](https://specs.opds.io/) (Atom XML) |
| Hosting | GitHub Actions + GitHub Pages |
| E-reader integration | KOReader + [opdsdir plugin](https://github.com/t2ym5u/koreader-plugins/tree/master/opdsdir.koplugin) |

---

## Tested on

| Component | Status |
|---|---|
| GitHub Actions pipeline | ✅ |
| KOReader on Kobo | ✅ (via opdsdir plugin) |
| iOS Share Sheet (Shortcut) | ✅ |
| save.html (desktop) | ✅ |
| Android | ❓ Untested |
| Other e-readers | ❓ Untested |

---

## Limitations

- Articles behind paywalls or requiring JavaScript won't be extracted
- GitHub Contents API upload limit: ~75 MB (base64 overhead)
- Git history may contain unencrypted files from before the secret was set
- The opdsdir KOReader plugin is not stable and only tested on Kobo
