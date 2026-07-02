# Setup

## 1. GitHub repo

```bash
git init && git add . && git commit -m "init: reading pipeline"
gh repo create reading-pipeline --public --source=. --push
```

## 2. GitHub Pages

Settings → Pages → Source : `main` branch, dossier `/`

## 3. Permissions Actions

Settings → Actions → General → Workflow permissions → **Read and write permissions**

## 4. Token GitHub (pour les clients mobiles)

Settings → Developer settings → Personal access tokens → Fine-grained tokens
- Repository : `reading-pipeline`
- Permission : **Issues → Read and write**

---

## 5. iOS — Raccourci (Share Sheet)

Crée un Raccourci dans l'app **Raccourcis** avec ces actions dans l'ordre :

```
1. [Recevoir] "Reçoit" → URLs → depuis la feuille de partage
2. [URL] "Obtenir les URL depuis l'entrée"
3. [Obtenir le contenu de l'URL]
      URL      : https://api.github.com/repos/t2ym5u/reading-pipeline/issues
      Méthode  : POST
      En-têtes :
        Authorization  → Bearer ghp_VOTRE_TOKEN
        Content-Type   → application/json
      Corps de la requête : JSON
        title → [Entrée du raccourci] (variable de l'étape 2)
4. [Afficher une notification] "✅ Article sauvegardé"
```

Nomme-le **"Save to Reading"** → apparaît dans la feuille de partage de Safari et Chrome.

---

## 6. Android — HTTP Shortcuts

Installe **HTTP Shortcuts** (Play Store, gratuit).

Nouvelle Raccourci :
- Type : **Regular shortcut**
- Méthode : POST
- URL : `https://api.github.com/repos/t2ym5u/reading-pipeline/issues`
- En-têtes :
  - `Authorization` : `Bearer ghp_VOTRE_TOKEN`
  - `Content-Type` : `application/json`
- Corps : `{"title": "{share_text}"}`
- Succès : notification "✅ Article sauvegardé"

Active **"Inclure dans le menu de partage"** → apparaît dans les apps Android.

---

## 7. Bookmarklet (navigateur desktop)

```javascript
javascript:location.href='https://t2ym5u.github.io/reading-pipeline/save.html?url='+encodeURIComponent(location.href)
```

Crée un favori avec ce code comme URL → un clic ouvre la page de sauvegarde avec l'URL déjà remplie.

---

## 8. KOReader

Menu → Navigateur OPDS → Ajouter un catalogue :
```
https://t2ym5u.github.io/reading-pipeline/catalog.xml
```
