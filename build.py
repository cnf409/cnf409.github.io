from __future__ import annotations

import argparse
import http.server
import json
import re
import shutil
import subprocess
import sys
import threading
import tomllib
from datetime import date, datetime
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader
from pygments.formatters import HtmlFormatter
from slugify import slugify

ROOT          = Path(__file__).resolve().parent
CONTENT_DIR   = ROOT / "content"
EVENTS_DIR    = CONTENT_DIR / "events"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR    = ROOT / "static"
PUBLIC_DIR    = ROOT / "public"
CONFIG_FILE   = ROOT / "config.toml"

_TERMINAL_RE = re.compile(r'```terminal\n(.*?)\n```', re.DOTALL)
_LANGUAGE_META = {
    'en': {'label': 'English', 'flag': '/flags/us.svg'},
    'fr': {'label': 'French',  'flag': '/flags/fr.svg'},
}
_IMAGE_LINE_RE = re.compile(
    r'^(?P<indent>\s*)\[(?P<alt>[^\]]*)\]\((?P<src>images/[^)\s]+\.(?:png|jpe?g|gif|webp|svg))\)\s*$',
    re.IGNORECASE,
)


def load_config() -> dict:
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("+++"):
        return {}, text
    try:
        end = text.index("+++", 3)
    except ValueError:
        return {}, text
    return tomllib.loads(text[3:end].strip()), text[end + 3:].strip()


def _terminal_replace(m: re.Match) -> str:
    content = m.group(1).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f'\n<div class="terminal-block"><pre class="terminal-pre"><code>{content}</code></pre></div>\n'


def _coerce_datetime(raw: object) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day)
    if isinstance(raw, str) and raw.strip():
        return datetime.fromisoformat(raw.strip())
    return None


def _coerce_str_list(raw: object) -> list[str]:
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    if isinstance(raw, (list, tuple)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _format_date(value: datetime | None) -> str:
    return value.strftime('%b %d, %Y') if value else ''


def _format_date_range(start: datetime | None, end: datetime | None) -> str:
    if start and end:
        if start.date() == end.date():
            return _format_date(start)
        if start.year == end.year and start.month == end.month:
            return f"{start.strftime('%b %d')} - {end.strftime('%d, %Y')}"
        if start.year == end.year:
            return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
        return f"{_format_date(start)} - {_format_date(end)}"
    return _format_date(start or end)


def _normalize_markdown_images(body: str) -> str:
    lines: list[str] = []
    in_fence = False

    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            lines.append(line)
            continue

        if not in_fence and (match := _IMAGE_LINE_RE.match(line)):
            lines.append(f"{match.group('indent')}![{match.group('alt')}]({match.group('src')})")
            continue

        lines.append(line)

    return '\n'.join(lines)


def md_to_html(body: str) -> tuple[str, str]:
    body = _normalize_markdown_images(body)
    body = _TERMINAL_RE.sub(_terminal_replace, body)
    parser = markdown.Markdown(
        extensions=['fenced_code', 'tables', 'toc', 'codehilite', 'attr_list', 'md_in_html'],
        extension_configs={
            'codehilite': {'css_class': 'highlight', 'guess_lang': True, 'use_pygments': True},
            'toc': {},
        },
    )
    html = parser.convert(body)
    return html, parser.toc


class Post:
    def __init__(self, meta: dict, html: str, toc: str, dir_path: Path) -> None:
        self.meta  = meta
        self.html  = html
        self.toc   = toc
        self.dir   = dir_path
        self.slug  = dir_path.name

        self.title  = meta.get('title', self.slug.replace('-', ' ').title())
        self.type   = meta.get('type', 'post')
        self.author = meta.get('author', '')
        self.tags   = meta.get('tags', [])
        self.pinned = bool(meta.get('pinned', False))
        self.image  = meta.get('image')
        self.draft  = bool(meta.get('draft', False))
        self.language = str(meta.get('language', 'en')).strip().lower() or 'en'
        if self.language not in _LANGUAGE_META:
            self.language = 'en'
        self.language_code  = self.language.upper()
        self.language_label = _LANGUAGE_META[self.language]['label']
        self.language_flag  = _LANGUAGE_META[self.language]['flag']

        raw = meta.get('date')
        if isinstance(raw, datetime):
            self.date: datetime = raw
        elif isinstance(raw, date):
            self.date = datetime(raw.year, raw.month, raw.day)
        elif isinstance(raw, str):
            self.date = datetime.fromisoformat(raw)
        else:
            self.date = datetime.min

        self.event               = meta.get('event', '')
        self.event_slug          = slugify(self.event) if self.event else ''
        self.category            = meta.get('category', '')
        self.difficulty          = meta.get('difficulty', '')
        self.stars               = meta.get('stars')
        self.solves              = meta.get('solves')
        self.challenge_author    = meta.get('challenge_author', '')
        self.challenge_author_url = meta.get('challenge_author_url', '')
        self.rating              = meta.get('rating')
        self.flag                = meta.get('flag', '')

        self.platform    = meta.get('platform', '')
        self.os          = meta.get('os', '')
        self.description = meta.get('description', '')

        self.sources     = self._list_files('sources')
        self.solve_files = self._list_files('solve')

    def _list_files(self, subdir: str) -> list[str]:
        d = self.dir / subdir
        return sorted(f.name for f in d.iterdir() if f.is_file()) if d.exists() else []

    @property
    def url(self) -> str:
        return f"/posts/{self.slug}/"

    @property
    def date_str(self) -> str:
        return '' if self.date == datetime.min else self.date.strftime('%b %d, %Y')

    @property
    def date_iso(self) -> str:
        return '' if self.date == datetime.min else self.date.strftime('%Y-%m-%d')

    @property
    def keywords(self) -> str:
        """Auto-generate keywords from tags + contextual metadata."""
        kws: list[str] = list(self.tags)
        for extra in (self.event, self.category, self.platform, self.os):
            if extra and extra not in kws:
                kws.append(extra)
        return ', '.join(kws)

    def as_dict(self) -> dict:
        return {
            'title': self.title, 'type': self.type, 'author': self.author,
            'tags': self.tags, 'pinned': self.pinned, 'image': self.image,
            'date_str': self.date_str, 'date_iso': self.date_iso,
            'language': self.language, 'language_code': self.language_code, 'language_label': self.language_label,
            'language_flag': self.language_flag,
            'url': self.url, 'slug': self.slug,
            'event': self.event, 'event_slug': self.event_slug,
            'category': self.category, 'difficulty': self.difficulty, 'stars': self.stars,
            'solves': self.solves, 'challenge_author': self.challenge_author,
            'challenge_author_url': self.challenge_author_url,
            'rating': self.rating, 'flag': self.flag,
            'platform': self.platform, 'os': self.os,
            'description': self.description,
            'keywords': self.keywords,
            'html': self.html, 'toc': self.toc,
            'sources': self.sources, 'solve_files': self.solve_files,
        }


class Event:
    def __init__(self, slug: str, meta: dict, html: str, dir_path: Path | None = None) -> None:
        self.slug = slug
        self.dir = dir_path
        self.title = str(meta.get('title', slug.replace('-', ' ').title())).strip()
        self.organizers = _coerce_str_list(meta.get('organizers', meta.get('organizer', [])))
        self.organizer_countries = _coerce_str_list(
            meta.get('organizer_countries', meta.get('organizer_country', []))
        )
        self.start_date = _coerce_datetime(meta.get('start_date'))
        self.end_date = _coerce_datetime(meta.get('end_date'))
        self.date_range = _format_date_range(self.start_date, self.end_date)
        self.html = html

    @property
    def start_date_iso(self) -> str:
        return self.start_date.strftime('%Y-%m-%d') if self.start_date else ''

    @property
    def end_date_iso(self) -> str:
        return self.end_date.strftime('%Y-%m-%d') if self.end_date else ''

    def as_dict(self) -> dict:
        return {
            'slug': self.slug,
            'title': self.title,
            'organizers': self.organizers,
            'organizer_countries': self.organizer_countries,
            'date_range': self.date_range,
            'start_date_iso': self.start_date_iso,
            'end_date_iso': self.end_date_iso,
            'html': self.html,
        }


def _parse_post(md_file: Path, dir_path: Path) -> Post | None:
    try:
        meta, body = parse_frontmatter(md_file.read_text(encoding='utf-8'))
        html, toc  = md_to_html(body)
        return Post(meta, html, toc, dir_path)
    except Exception as exc:
        print(f'  [!] Skipping {md_file}: {exc}')
        return None


def discover_posts(include_drafts: bool = False) -> list[Post]:
    posts: list[Post] = []

    for slug_dir in sorted((CONTENT_DIR / 'writeups').glob('*')):
        if slug_dir.is_dir() and (md := slug_dir / 'writeup.md').exists():
            if (p := _parse_post(md, slug_dir)) and (include_drafts or not p.draft):
                posts.append(p)

    for slug_dir in sorted((CONTENT_DIR / 'posts').glob('*')):
        if slug_dir.is_dir() and (md := slug_dir / 'index.md').exists():
            if (p := _parse_post(md, slug_dir)) and (include_drafts or not p.draft):
                posts.append(p)

    return sorted(posts, key=lambda p: p.date, reverse=True)


def make_env(config: dict) -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    env.globals['config']  = config
    env.globals['now']     = datetime.now()
    env.globals['slugify'] = slugify
    env.filters['tojson']  = lambda v: json.dumps(v, ensure_ascii=False)
    return env


def write_page(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def render(env: Environment, template: str, **ctx) -> str:
    return env.get_template(template).render(**ctx)


def load_about() -> tuple[dict, str]:
    about_file = ROOT / 'about.md'
    if about_file.exists():
        meta, body = parse_frontmatter(about_file.read_text(encoding='utf-8'))
        html, _    = md_to_html(body)
        return meta, html
    return {}, '<p>Coming soon.</p>'


def load_events() -> dict[str, Event]:
    events: dict[str, Event] = {}
    if not EVENTS_DIR.exists():
        return events

    for item in sorted(EVENTS_DIR.iterdir()):
        md_file: Path | None = None
        slug: str | None = None
        dir_path: Path | None = None

        if item.is_dir() and (item / 'index.md').exists():
            md_file = item / 'index.md'
            slug = item.name
            dir_path = item
        elif item.is_file() and item.suffix == '.md':
            md_file = item
            slug = item.stem
            dir_path = item.parent

        if not md_file or not slug:
            continue

        try:
            meta, body = parse_frontmatter(md_file.read_text(encoding='utf-8'))
            html, _ = md_to_html(body)
            events[slug] = Event(slug, meta, html, dir_path)
        except Exception as exc:
            print(f'  [!] Skipping event {md_file}: {exc}')

    return events


def copy_static() -> None:
    if not STATIC_DIR.exists():
        return
    for item in STATIC_DIR.iterdir():
        dest = PUBLIC_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def copy_post_assets(posts: list[Post]) -> None:
    for post in posts:
        base = PUBLIC_DIR / 'posts' / post.slug
        for subdir in ('assets', 'images', 'sources', 'solve'):
            src = post.dir / subdir
            if src.exists():
                shutil.copytree(src, base / subdir, dirs_exist_ok=True)


def copy_event_assets(events: list[dict]) -> None:
    for event in events:
        dir_path = event.get('dir_path')
        if not dir_path:
            continue
        base = PUBLIC_DIR / 'events' / event['slug']
        for subdir in ('assets', 'images'):
            src = Path(dir_path) / subdir
            if src.exists():
                shutil.copytree(src, base / subdir, dirs_exist_ok=True)


def generate_syntax_css() -> None:
    css = HtmlFormatter(style='dracula').get_style_defs('.highlight')
    out = PUBLIC_DIR / 'css'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'syntax.css').write_text(css, encoding='utf-8')


def run_tailwind() -> None:
    binary = ROOT / 'tailwindcss'
    cmd    = str(binary) if binary.exists() else 'tailwindcss'
    out    = PUBLIC_DIR / 'css'
    out.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [cmd, '-i', str(STATIC_DIR / 'css' / 'input.css'),
             '-o', str(out / 'tailwind.css'), '--minify'],
            check=True, capture_output=True,
        )
        print('  [+] Tailwind built')
    except FileNotFoundError:
        print('  [!] tailwindcss not found — run debug.sh or download manually')
        shutil.copy2(STATIC_DIR / 'css' / 'input.css', out / 'tailwind.css')
    except subprocess.CalledProcessError as exc:
        print(f'  [!] Tailwind error: {exc.stderr.decode()[:200]}')
        shutil.copy2(STATIC_DIR / 'css' / 'input.css', out / 'tailwind.css')


def build_index(env: Environment, posts: list[Post]) -> None:
    about_meta, _ = load_about()
    pinned = [p.as_dict() for p in posts if p.pinned][:4]
    write_page(PUBLIC_DIR / 'index.html', render(env, 'index.html', about=about_meta, pinned=pinned))


def build_post_pages(env: Environment, posts: list[Post]) -> None:
    for post in posts:
        write_page(PUBLIC_DIR / 'posts' / post.slug / 'index.html',
                   render(env, 'post.html', post=post.as_dict()))


def build_posts_list(env: Environment, posts: list[Post], config: dict) -> None:
    per_page = config.get('build', {}).get('posts_per_page', 15)
    chunks   = [posts[i:i + per_page] for i in range(0, max(len(posts), 1), per_page)]
    total    = len(chunks)

    for i, chunk in enumerate(chunks):
        page_num     = i + 1
        prev_url     = None if i == 0 else ('/posts/' if i == 1 else f'/posts/page/{i}/')
        next_url     = f'/posts/page/{i + 2}/' if page_num < total else None
        canonical_url = '/posts/' if page_num == 1 else f'/posts/page/{page_num}/'
        ctx = dict(posts=[p.as_dict() for p in chunk],
                   page_num=page_num, total_pages=total,
                   prev_url=prev_url, next_url=next_url,
                   canonical_url=canonical_url)
        html = render(env, 'posts_list.html', **ctx)
        if i == 0:
            write_page(PUBLIC_DIR / 'posts' / 'index.html', html)
        write_page(PUBLIC_DIR / 'posts' / 'page' / str(page_num) / 'index.html', html)


def build_tag_pages(env: Environment, posts: list[Post]) -> None:
    tags: dict[str, list[Post]] = {}
    for post in posts:
        for tag in post.tags:
            tags.setdefault(tag, []).append(post)

    for tag, tposts in tags.items():
        tag_slug = slugify(tag)
        write_page(PUBLIC_DIR / 'tags' / tag_slug / 'index.html',
                   render(env, 'tag.html', tag=tag, tag_slug=tag_slug,
                          posts=[p.as_dict() for p in tposts]))

    all_tags = sorted(tags, key=str.lower)
    grouped_tags: dict[str, list[tuple[str, str, int]]] = {}
    for tag in all_tags:
        letter = tag[0].upper() if tag and tag[0].isalnum() else '#'
        grouped_tags.setdefault(letter, []).append((tag, slugify(tag), len(tags[tag])))

    write_page(PUBLIC_DIR / 'tags' / 'index.html',
               render(env, 'tags_list.html',
                      tag_total=len(all_tags),
                      grouped_tags=[(letter, grouped_tags[letter]) for letter in sorted(grouped_tags)]))


def collect_events(posts: list[Post], event_meta: dict[str, Event]) -> list[dict]:
    grouped: dict[str, list[Post]] = {}
    for post in posts:
        if post.event:
            grouped.setdefault(post.event_slug, []).append(post)

    slugs = sorted(set(grouped) | set(event_meta))
    events: list[dict] = []

    for slug in slugs:
        meta = event_meta.get(slug)
        posts_for_event = sorted(grouped.get(slug, []), key=lambda p: p.date, reverse=True)
        fallback_title = posts_for_event[0].event if posts_for_event else slug.replace('-', ' ').title()
        event = (meta.as_dict() if meta else {
            'slug': slug,
            'title': fallback_title,
            'organizers': [],
            'organizer_countries': [],
            'date_range': '',
            'start_date_iso': '',
            'end_date_iso': '',
            'html': '',
        })
        event['title'] = event.get('title') or fallback_title
        event['posts'] = [p.as_dict() for p in posts_for_event]
        event['writeup_count'] = len(posts_for_event)
        event['dir_path'] = str(meta.dir) if meta and meta.dir else ''
        latest_post = max((p.date for p in posts_for_event), default=datetime.min)
        event['sort_date'] = meta.end_date or meta.start_date or latest_post
        events.append(event)

    return sorted(events, key=lambda e: e['sort_date'], reverse=True)


def build_event_pages(env: Environment, events: list[dict]) -> None:
    for event in events:
        write_page(
            PUBLIC_DIR / 'events' / event['slug'] / 'index.html',
            render(env, 'event.html', event=event),
        )


def build_events_index(env: Environment, events: list[dict]) -> None:
    write_page(
        PUBLIC_DIR / 'events' / 'index.html',
        render(env, 'events_list.html', events=events, event_total=len(events)),
    )


def build_about(env: Environment) -> None:
    meta, html = load_about()
    write_page(PUBLIC_DIR / 'about' / 'index.html',
               render(env, 'about.html', meta=meta, html=html))


def build_sitemap(config: dict, posts: list[Post], events: list[dict]) -> None:
    base = config['site']['base_url'].rstrip('/')

    urls: list[dict] = [
        {'loc': f'{base}/',        'changefreq': 'weekly',  'priority': '1.0'},
        {'loc': f'{base}/posts/',  'changefreq': 'weekly',  'priority': '0.8'},
        {'loc': f'{base}/events/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'loc': f'{base}/tags/',   'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f'{base}/about/',  'changefreq': 'monthly', 'priority': '0.7'},
    ]

    for post in posts:
        entry: dict = {'loc': f'{base}{post.url}', 'changefreq': 'monthly', 'priority': '0.9'}
        if post.date != datetime.min:
            entry['lastmod'] = post.date.strftime('%Y-%m-%d')
        urls.append(entry)

    for event in events:
        urls.append({'loc': f'{base}/events/{event["slug"]}/', 'changefreq': 'monthly', 'priority': '0.6'})

    tags: set[str] = set()
    for post in posts:
        tags.update(post.tags)
    for tag in sorted(tags):
        urls.append({'loc': f'{base}/tags/{slugify(tag)}/', 'changefreq': 'monthly', 'priority': '0.4'})

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        lines.append('  <url>')
        lines.append(f'    <loc>{url["loc"]}</loc>')
        if 'lastmod' in url:
            lines.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
        lines.append(f'    <changefreq>{url["changefreq"]}</changefreq>')
        lines.append(f'    <priority>{url["priority"]}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')

    (PUBLIC_DIR / 'sitemap.xml').write_text('\n'.join(lines), encoding='utf-8')
    print('  [+] Sitemap generated')


def build_404(env: Environment) -> None:
    write_page(PUBLIC_DIR / '404.html', render(env, '404.html'))


def build(config: dict, clean: bool = False, include_drafts: bool = False) -> None:
    if clean and PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
        print('  [+] Cleaned public/')

    PUBLIC_DIR.mkdir(exist_ok=True)

    print('  [+] Discovering content...')
    posts = discover_posts(include_drafts=include_drafts)
    event_meta = load_events()
    events = collect_events(posts, event_meta)
    print(f'      {len(posts)} post(s)')

    env = make_env(config)

    print('  [+] Static files...')
    copy_static()

    print('  [+] Tailwind CSS...')
    run_tailwind()

    print('  [+] Syntax CSS...')
    generate_syntax_css()

    print('  [+] Building pages...')
    build_index(env, posts)
    build_post_pages(env, posts)
    build_posts_list(env, posts, config)
    build_tag_pages(env, posts)
    build_event_pages(env, events)
    build_events_index(env, events)
    build_about(env)

    print('  [+] Post assets...')
    copy_post_assets(posts)
    copy_event_assets(events)

    print('  [+] Sitemap & 404...')
    build_sitemap(config, posts, events)
    build_404(env)

    print('  [✓] Done → public/')


def serve(config: dict) -> None:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print('  [!] watchdog not installed: pip install watchdog')
        sys.exit(1)

    class _Handler(FileSystemEventHandler):
        def __init__(self) -> None:
            self._timer: threading.Timer | None = None

        def on_any_event(self, event):
            if event.is_directory:
                return
            if event.event_type not in {'modified', 'created', 'deleted', 'moved'}:
                return
            raw_paths = [getattr(event, 'src_path', ''), getattr(event, 'dest_path', '')]
            paths = [Path(p).resolve(strict=False) for p in raw_paths if p]
            if any(path.name == '.DS_Store' for path in paths):
                return
            if any(PUBLIC_DIR == path or PUBLIC_DIR in path.parents for path in paths):
                return
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(0.4, self._rebuild)
            self._timer.start()

        def _rebuild(self):
            print('\n  [~] Rebuilding...')
            try:
                build(config, include_drafts=True)
            except Exception as exc:
                print(f'  [!] {exc}')

    build(config, include_drafts=True)

    observer = Observer()
    handler  = _Handler()
    for watch in (CONTENT_DIR, TEMPLATES_DIR, STATIC_DIR):
        if Path(watch).exists():
            observer.schedule(handler, str(watch), recursive=True)
    observer.schedule(handler, str(ROOT), recursive=False)
    observer.start()

    class _Server(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)
        def log_message(self, fmt, *args):
            pass

    print('\n  [✓] http://localhost:8000  (Ctrl-C to stop)\n')
    try:
        with http.server.ThreadingHTTPServer(('0.0.0.0', 8000), _Server) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve',  '-s', action='store_true')
    parser.add_argument('--clean',  '-c', action='store_true')
    parser.add_argument('--drafts', '-d', action='store_true')
    args = parser.parse_args()
    cfg  = load_config()
    serve(cfg) if args.serve else build(cfg, clean=args.clean, include_drafts=args.drafts)
