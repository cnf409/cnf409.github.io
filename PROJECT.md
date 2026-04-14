# PROJECT — Custom Static Site Generator (v2_blog)

Blog de cybersécurité statique, construit avec un générateur Python + Jinja2 custom.
Remplace Hugo (v1_blog) pour avoir un contrôle total sur le front-end et des features spécifiques au contexte cybersec.

---

## Stack technique

| Composant | Techno |
|---|---|
| Builder | Python 3 |
| Templates | Jinja2 |
| Styles | Tailwind CSS (CLI standalone, zéro npm) + `custom.css` pour les effets cyberpunk (glows, glitch, animations) |
| Markdown | `python-markdown` avec extensions |
| Dev server | `http.server` Python + `watchdog` (file watcher) + WebSocket (hot reload navigateur) |
| Déploiement | Manuel pour l'instant |

---

## Structure du projet

```
blog/
  build.py               ← point d'entrée du builder
  config.toml            ← config globale du site
  content/
    writeups/
      <challenge-slug>/
        writeup.md       ← front matter + contenu markdown
        sources/         ← fichiers donnés par le challenge (zip, binaire, code source appli...)
          app.zip
          binary
        solve/           ← tes propres scripts (exploit.py, solve.py, outil custom...)
          exploit.py
          rop_chain.py
        assets/          ← images utilisées dans le post (non listées en téléchargement)
          schema.png
    posts/
      <post-slug>/
        index.md
        assets/
  about.md               ← page about
  templates/
    base.html
    index.html
    post.html
    posts-list.html
    tag.html
    event.html
    about.html
  static/
    css/
      custom.css         ← effets cyberpunk custom
    js/
      main.js            ← filtres posts, hot reload dev...
    img/
      pfp.jpg
  public/                ← output du builder (gitignore)
  tailwind.config.js
  requirements.txt
```

---

## Types de contenu

Trois types de posts, différenciés par le champ `type` dans le front matter.
Tous les types sont mélangés sur la page `/posts/` et filtrables côté client.

### CTF Writeup (`type = "ctf"`)

```toml
type              = "ctf"
title             = "ret2win"
author            = "conflict"          # auteur du post (toi 99% du temps)
date              = "2022-12-31"
image             = "assets/banner.png" # optionnel — image/thumbnail du post
tags              = ["pwn", "rop"]
event             = "ROPEmporium"       # génère une page /events/<slug>/
category          = "pwn"              # web | crypto | rev | pwn | misc | forensics...
difficulty        = "easy"             # easy | medium | hard | insane  OU  stars = 2 (1-3)
solves            = 142
challenge_author  = "ROP Emporium"
challenge_author_url = "https://twitter.com/..."  # optionnel — rend le nom cliquable
rating            = 8                  # ta note /10
flag              = "FLAG{...}"        # optionnel — affiché automatiquement en bas du post
pinned            = false              # true → affiché en haut de la homepage
```

### Box Writeup (`type = "box"`)

```toml
type       = "box"
title      = "Shoppy"
author     = "conflict"
date       = "2023-01-14"
image      = "assets/shoppy.png"       # optionnel
tags       = ["linux", "nosqli", "docker"]
platform   = "hackthebox"             # hackthebox | tryhackme | vulnhub...
os         = "linux"                  # linux | windows | other
difficulty = "easy"
pinned     = false
```

### Post classique (`type = "post"`)

```toml
type   = "post"
title  = "PHP Type Juggling"
author = "conflict"
date   = "2023-01-07"
image  = "assets/cover.png"           # optionnel
tags   = ["php", "web", "educative"]
pinned = false
```

---

## Pages générées

| URL | Contenu |
|---|---|
| `/` | Homepage : posts épinglés + derniers posts |
| `/posts/` | Tous les posts mélangés, filtrables (CTF / Box / Post), paginés |
| `/posts/<slug>/` | Page d'un post |
| `/tags/<tag>/` | Tous les posts avec ce tag |
| `/events/<event-slug>/` | Tous les writeups d'un même CTF event (auto-généré depuis `event`) |
| `/about/` | Page about |

---

## Features par type de page

### Toutes les pages
- Design cyberpunk neon (cyan `#00f0ff` / magenta `#f700ff`) harmonisé et construit from scratch
- Header avec navigation
- Footer
- Responsive

### Page post (writeup CTF ou Box)

**Info card** en haut de page, générée depuis le front matter :
- CTF : event, catégorie, difficulté, solves, auteur du challenge (cliquable si URL fournie), ta note /10
- Box : plateforme, OS, difficulté

**Image de couverture** : si `image` présent dans le front matter, affichée en haut du post (sous l'info card)

**Contenu markdown** avec :
- Blocs de code avec syntaxe colorée par langage (` ```python `, ` ```c `...)
- Blocs terminal distincts (` ```terminal `) : style dark, police mono, prompt stylé
- Flag highlight : si `flag` présent → bloc stylé automatiquement ajouté en fin de post
- Inline code stylé
- Blockquotes, tables

**Section "Sources"** (auto-générée si dossiers non vides) :
- `sources/` → "Challenge files" : liste des fichiers avec bouton download
- `solve/` → "Solve scripts" : liste des fichiers avec bouton download
- Les fichiers `assets/` ne sont pas listés ici

**Tags** cliquables → `/tags/<tag>/`

### Page post classique
- Même rendu markdown
- Pas d'info card
- Image de couverture optionnelle
- Tags

### Homepage (`/`)
- Posts épinglés (`pinned = true`) en haut, dans une section dédiée
- Derniers posts en dessous (tous types confondus)

### Page posts (`/posts/`)
- Tous les posts mélangés
- Filtres côté client : Tous / CTF / Box / Post
- Pagination classique (N posts par page, précédent/suivant)

### Page tag (`/tags/<tag>/`)
- Liste de tous les posts ayant ce tag

### Page event (`/events/<event-slug>/`)
- Auto-générée depuis le champ `event` du front matter
- Liste tous les writeups de cet event
- Titre = nom de l'event

### Page about (`/about/`)
- Contenu depuis `about.md`
- Design soigné, pas juste du markdown brut

---

## Builder — fonctionnement

1. Lit `config.toml` (titre du site, baseURL, pagination size...)
2. Parse tous les fichiers markdown de `content/` (front matter TOML + corps Markdown)
3. Rend les templates Jinja2 avec les données extraites
4. Lance Tailwind CLI pour générer le CSS final (purgé)
5. Copie `static/` vers `public/`
6. Copie les `assets/` et fichiers `sources/` / `solve/` de chaque post vers `public/`
7. Génère toutes les pages HTML dans `public/`

```
python build.py          # build complet
python build.py --serve  # build + dev server avec hot reload
```

---

## Dev server

- Sert `public/` en local
- `watchdog` surveille `content/`, `templates/`, `static/`
- Rebuild automatique à chaque changement
- WebSocket injecté dans les pages pour recharger le navigateur

---

## Ce qui sera migré depuis v1_blog

Tous les posts existants seront portés manuellement dans la nouvelle structure.
Le front matter sera converti du format TOML Hugo vers le nouveau format.
