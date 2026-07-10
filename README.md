# reading-pipeline

> ⚠️ **Not stable — tested on Kobo only.** The KOReader side relies on [opdsdir](https://github.com/t2ym5u/koreader-plugins/tree/master/opdsdir.koplugin), an experimental monkey-patch plugin. The pipeline itself (GitHub Actions) is stable for general use.

A personal reading pipeline: save articles or EPUBs from anywhere, read them on your e-reader.

```
[Mobile / Desktop]
  save.html / manage.html (GitHub Pages PWA)
       ↓
[GitHub API]
  repository_dispatch (articles)
  Contents API        (EPUBs)
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
- **Manage library** — list and delete files from the web interface
- **AES-256 encryption** — filenames (UUID), content, index and catalog are all encrypted
- **OPDS catalog** — transparent integration with KOReader's built-in browser
- **Zero infrastructure** — runs entirely on GitHub Actions + GitHub Pages (free tier)

---

## Quick start

See [SETUP.md](SETUP.md) for the full installation guide.

**Summary:**
1. Fork or clone this repo → enable GitHub Pages (main branch, root `/`)
2. Create a `EPUB_ENCRYPT_KEY` repository secret (your encryption passphrase)
3. Create a GitHub fine-grained token (see permissions below)
4. Open `https://<you>.github.io/reading-pipeline/` and enter your token
5. In KOReader: add OPDS catalog `https://<you>.github.io/reading-pipeline/catalog.xml.enc`
6. Install [opdsdir](https://github.com/t2ym5u/koreader-plugins/tree/master/opdsdir.koplugin) on KOReader, set the encryption key

---

## Web interface

Three pages are served as a PWA from GitHub Pages:

| Page | URL | Purpose |
|---|---|---|
| `index.html` | `/reading-pipeline/` | Home — links to the two tools + shows last update date |
| `save.html` | `/reading-pipeline/save.html` | Save an article URL or upload an EPUB |
| `manage.html` | `/reading-pipeline/manage.html` | List and delete files from the library |

**`index.html`** fetches the date of the last commit to `main` from the GitHub API and displays it as a version indicator ("Mis à jour le…").

**`manage.html`** decrypts `index.tsv.enc` client-side (WebCrypto, AES-256-CBC-PBKDF2) using the key you enter in the browser, so titles are displayed instead of raw UUIDs.

---

## Token permissions

Create a **fine-grained personal access token** scoped to the `reading-pipeline` repo:

| Permission | Value | Used by |
|---|---|---|
| Actions | Read and write | `save.html` (article dispatch) |
| Contents | Read and write | `save.html` (EPUB upload) · `manage.html` (list + delete) |

> Issues permission is **not** required. Articles are sent via `repository_dispatch`, whose payload is never publicly visible even on a public repository.

---

## Saving content

### Articles (URL → EPUB)

**Desktop / Mobile:** Open `save.html` → paste URL → Sauvegarder.

**Bookmarklet:**
```javascript
javascript:location.href='https://t2ym5u.github.io/reading-pipeline/save.html?url='+encodeURIComponent(location.href)
```

**iOS Shortcut:** Use a *Get Contents of URL* action:
```
POST https://api.github.com/repos/<owner>/reading-pipeline/dispatches
Headers: Authorization: Bearer <token>
         Content-Type: application/json
Body:    {"event_type":"fetch-article","client_payload":{"url":"<URL>"}}
```

**Command line:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"fetch-article","client_payload":{"url":"https://example.com/article"}}' \
  https://api.github.com/repos/<owner>/reading-pipeline/dispatches
```

### EPUBs

**Mobile / Desktop:** Open `save.html` → EPUB section → pick file.
The filename is replaced by a UUID before upload; the commit message is generic (`add: new epub`).

**Command line:**
```bash
cp mybook.epub library/
git add library/mybook.epub && git commit -m "add: new epub" && git push
# catalog.yml automatically renames to UUID and encrypts
```

### Managing the library

Open `manage.html` → enter token + encryption key → Charger.
Select one or more files and click Supprimer. Each deletion commits a removal to `main`,
which triggers `catalog.yml` to rebuild the encrypted catalog automatically (~1 min).

---

## Encryption

When `EPUB_ENCRYPT_KEY` is set as a repository secret:

| File | Stored as |
|---|---|
| EPUB content | AES-256-CBC encrypted, UUID filename |
| `index.tsv` | `index.tsv.enc` (titles, URLs, dates) |
| `catalog.xml` | `catalog.xml.enc` |

The key never appears in the repo or in git history. It lives in GitHub Secrets (server-side) and in KOReader's OPDS settings (device).

**What is NOT exposed publicly** (even on a public repo):
- EPUB content (encrypted)
- Article URLs (in encrypted `index.tsv.enc` and in `repository_dispatch` payload)
- Titles (in encrypted `catalog.xml.enc` and `index.tsv.enc`)
- EPUB filenames (UUID)
- Git commit messages (`add: new article` / `add: new epub` / `remove: epub`)

**Threat model:** protects against casual browsing of the public repo. Does not protect against someone with physical access to the device (key is stored in plaintext in KOReader settings).

---

## Stack

| Component | Technology |
|---|---|
| Article extraction | [trafilatura](https://github.com/adbar/trafilatura) |
| EPUB generation | [pandoc](https://pandoc.org/) |
| Encryption | openssl AES-256-CBC (GitHub runner + device) |
| Client-side decryption | WebCrypto API (PBKDF2-SHA256 + AES-CBC) |
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
| save.html / manage.html (desktop) | ✅ |
| Android | ❓ Untested |
| Other e-readers | ❓ Untested |

---

## Limitations

- Articles behind paywalls or requiring JavaScript won't be extracted
- GitHub Contents API upload limit: ~75 MB (base64 overhead)
- Git history may contain unencrypted files from before the secret was set
- The opdsdir KOReader plugin is not stable and only tested on Kobo
