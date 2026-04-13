from __future__ import annotations

import argparse
import http.server
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

ROOT          = Path(__file__).parent
CONTENT_DIR   = ROOT / "content"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR    = ROOT / "static"
PUBLIC_DIR    = ROOT / "public"
CONFIG_FILE   = ROOT / "config.toml"

_TERMINAL_RE = re.compile(r'```terminal\n(.*?)\n```', re.DOTALL)


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


def md_to_html(body: str) -> tuple[str, str]:
    body = _TERMINAL_RE.sub(_terminal_replace, body)
    parser = markdown.Markdown(
        extensions=['fenced_code', 'tables', 'toc', 'codehilite', 'attr_list', 'md_in_html'],
        extension_configs={
            'codehilite': {'css_class': 'highlight', 'guess_lang': False, 'use_pygments': True},
            'toc': {'permalink': True},
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

        self.platform = meta.get('platform', '')
        self.os       = meta.get('os', '')

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

    def as_dict(self) -> dict:
        return {
            'title': self.title, 'type': self.type, 'author': self.author,
            'tags': self.tags, 'pinned': self.pinned, 'image': self.image,
            'date_str': self.date_str, 'date_iso': self.date_iso,
            'url': self.url, 'slug': self.slug,
            'event': self.event, 'event_slug': self.event_slug,
            'category': self.category, 'difficulty': self.difficulty, 'stars': self.stars,
            'solves': self.solves, 'challenge_author': self.challenge_author,
            'challenge_author_url': self.challenge_author_url,
            'rating': self.rating, 'flag': self.flag,
            'platform': self.platform, 'os': self.os,
            'html': self.html, 'toc': self.toc,
            'sources': self.sources, 'solve_files': self.solve_files,
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
    return env


def write_page(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def render(env: Environment, template: str, **ctx) -> str:
    return env.get_template(template).render(**ctx)


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
        for subdir in ('assets', 'sources', 'solve'):
            src = post.dir / subdir
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
    pinned = [p.as_dict() for p in posts if p.pinned]
    recent = [p.as_dict() for p in posts if not p.pinned][:10]
    write_page(PUBLIC_DIR / 'index.html', render(env, 'index.html', pinned=pinned, recent=recent))


def build_post_pages(env: Environment, posts: list[Post]) -> None:
    for post in posts:
        write_page(PUBLIC_DIR / 'posts' / post.slug / 'index.html',
                   render(env, 'post.html', post=post.as_dict()))


def build_posts_list(env: Environment, posts: list[Post], config: dict) -> None:
    per_page = config.get('build', {}).get('posts_per_page', 15)
    chunks   = [posts[i:i + per_page] for i in range(0, max(len(posts), 1), per_page)]
    total    = len(chunks)

    for i, chunk in enumerate(chunks):
        page_num = i + 1
        prev_url = None if i == 0 else ('/posts/' if i == 1 else f'/posts/page/{i}/')
        next_url = f'/posts/page/{i + 2}/' if page_num < total else None
        ctx = dict(posts=[p.as_dict() for p in chunk],
                   page_num=page_num, total_pages=total,
                   prev_url=prev_url, next_url=next_url)
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
    write_page(PUBLIC_DIR / 'tags' / 'index.html',
               render(env, 'tags_list.html',
                      tags=[(t, slugify(t), len(tags[t])) for t in all_tags]))


def build_event_pages(env: Environment, posts: list[Post]) -> None:
    events: dict[str, list[Post]] = {}
    for post in posts:
        if post.event:
            events.setdefault(post.event, []).append(post)

    for event_name, eposts in events.items():
        event_slug = slugify(event_name)
        write_page(PUBLIC_DIR / 'events' / event_slug / 'index.html',
                   render(env, 'event.html', event=event_name, event_slug=event_slug,
                          posts=[p.as_dict() for p in eposts]))


def build_about(env: Environment) -> None:
    about_file = ROOT / 'about.md'
    if about_file.exists():
        meta, body = parse_frontmatter(about_file.read_text(encoding='utf-8'))
        html, _    = md_to_html(body)
    else:
        meta, html = {}, '<p>Coming soon.</p>'
    write_page(PUBLIC_DIR / 'about' / 'index.html',
               render(env, 'about.html', meta=meta, html=html))


def build(config: dict, clean: bool = False, include_drafts: bool = False) -> None:
    if clean and PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
        print('  [+] Cleaned public/')

    PUBLIC_DIR.mkdir(exist_ok=True)

    print('  [+] Discovering content...')
    posts = discover_posts(include_drafts=include_drafts)
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
    build_event_pages(env, posts)
    build_about(env)

    print('  [+] Post assets...')
    copy_post_assets(posts)

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
            if event.is_directory or '.DS_Store' in event.src_path:
                return
            if str(PUBLIC_DIR) in event.src_path:
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
    for watch in (CONTENT_DIR, TEMPLATES_DIR, STATIC_DIR, ROOT / 'about.md', CONFIG_FILE):
        if Path(watch).exists():
            observer.schedule(handler, str(watch), recursive=True)
    observer.start()

    class _Server(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)
        def log_message(self, fmt, *args):
            pass

    print('\n  [✓] http://localhost:8000  (Ctrl-C to stop)\n')
    try:
        with http.server.HTTPServer(('', 8000), _Server) as httpd:
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
