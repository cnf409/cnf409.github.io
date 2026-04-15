from __future__ import annotations

import argparse
import http.server
import json
import math
import re
import shutil
import subprocess
import sys
import threading
import tomllib
from datetime import date, datetime
from html import unescape as html_unescape
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

import markdown
from jinja2 import Environment, FileSystemLoader
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, get_lexer_for_filename
from pygments.util import ClassNotFound
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
_INLINE_FILE_MAX_BYTES = 100_000
_PHP_FENCE_RE = re.compile(
    r'(^|\n)```(?P<lang>php\d*)[^\n]*\n(?P<code>.*?)(?:\n)```(?=\n|$)',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r'(<[^>]+>)')
_BARE_URL_RE = re.compile(r'https?://[^\s<]+')
_IMAGE_LINE_RE = re.compile(
    r'^(?P<indent>\s*)\[(?P<alt>[^\]]*)\]\((?P<src>images/[^)\s]+\.(?:png|jpe?g|gif|webp|svg))\)\s*$',
    re.IGNORECASE,
)
_FLAG_MARKER_RE = re.compile(r'\[\[!FLAG\]\]')
_FENCED_CODE_RE = re.compile(r'```.*?```', re.DOTALL)
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_MARKDOWN_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_IMG_TAG_RE = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
_REFERENCE_TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
_WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
_WHITESPACE_RE = re.compile(r'\s+')
_GIT_DATE_CACHE: dict[Path, datetime | None] = {}
_REFERENCE_TITLE_CACHE: dict[str, str] = {}
_REFERENCE_FETCH_TIMEOUT_SECONDS = 2.0
_REFERENCE_TITLE_MAX_BYTES = 64_000


def load_config() -> dict:
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def _normalize_toml_frontmatter(raw: str) -> str:
    return re.sub(
        r'(?m)^(\s*solves\s*=\s*)\?(\s*(?:#.*)?)$',
        lambda m: f'{m.group(1)}"?"{m.group(2)}',
        raw,
    )


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("+++"):
        return {}, text
    try:
        end = text.index("+++", 3)
    except ValueError:
        return {}, text
    frontmatter = _normalize_toml_frontmatter(text[3:end].strip())
    return tomllib.loads(frontmatter), text[end + 3:].strip()


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


def _split_csv_list(raw: object) -> list[str]:
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(',') if part.strip()]
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


def _xml_escape(text: str) -> str:
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
    )


def _rfc2822(dt: datetime) -> str:
    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size / (1024 * 1024):.1f} MB'


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(' ', text).strip()


def _markdown_to_text(body: str) -> str:
    text = _FENCED_CODE_RE.sub(' ', body)
    text = _MARKDOWN_IMAGE_RE.sub(lambda m: m.group(1) or ' ', text)
    text = _MARKDOWN_LINK_RE.sub(lambda m: m.group(1), text)
    text = _INLINE_CODE_RE.sub(lambda m: m.group(1), text)
    text = _FLAG_MARKER_RE.sub(' ', text)
    text = _HTML_TAG_RE.sub(' ', text)
    text = re.sub(r'(?m)^\s{0,3}#{1,6}\s*', '', text)
    text = re.sub(r'(?m)^\s*[-*+]\s+', '', text)
    text = re.sub(r'(?m)^\s*\d+\.\s+', '', text)
    text = re.sub(r'(?m)^\s*>\s?', '', text)
    return _normalize_whitespace(html_unescape(text))


def _count_reading_words(body: str) -> int:
    return len(_WORD_RE.findall(_markdown_to_text(body)))


def _estimate_reading_time(body: str) -> int:
    return max(1, math.ceil(_count_reading_words(body) / 220))


def _make_excerpt(body: str, fallback: str = '', limit: int = 170) -> str:
    text = _markdown_to_text(body) or fallback.strip()
    if not text or len(text) <= limit:
        return text

    shortened = text[:limit].rsplit(' ', 1)[0].strip()
    return f'{shortened}…' if shortened else f'{text[:limit].strip()}…'


def _path_mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None


def _git_last_commit_date(path: Path) -> datetime | None:
    path = path.resolve()
    if path in _GIT_DATE_CACHE:
        return _GIT_DATE_CACHE[path]

    try:
        rel_path = path.relative_to(ROOT)
    except ValueError:
        rel_path = path

    try:
        proc = subprocess.run(
            ['git', '-C', str(ROOT), 'log', '-1', '--format=%cs', '--', str(rel_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        _GIT_DATE_CACHE[path] = None
        return None

    output = proc.stdout.strip()
    if proc.returncode == 0 and output:
        try:
            committed_at = datetime.fromisoformat(output)
            _GIT_DATE_CACHE[path] = committed_at
            return committed_at
        except ValueError:
            pass

    _GIT_DATE_CACHE[path] = None
    return None


def _read_inline_source(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if len(data) > _INLINE_FILE_MAX_BYTES or b'\x00' in data:
        return None

    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return None


def _highlight_source(filename: str, source: str) -> str:
    try:
        lexer = get_lexer_for_filename(filename, source)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)

    formatter = HtmlFormatter(style='dracula', cssclass='highlight')
    return highlight(source, lexer, formatter)


def _highlight_php_inline(code: str) -> str:
    formatter = HtmlFormatter(style='dracula', cssclass='highlight')
    lexer = get_lexer_by_name('php', startinline=True)
    return highlight(code, lexer, formatter)


def _normalize_php_fences(body: str) -> str:
    def replace(match: re.Match) -> str:
        prefix = match.group(1)
        code = match.group('code')
        return f"{prefix}\n{_highlight_php_inline(code)}\n"

    return _PHP_FENCE_RE.sub(replace, body)


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


def _autolink_text_chunk(text: str) -> str:
    def repl(match: re.Match) -> str:
        url = match.group(0)
        trailing = ''

        while url and url[-1] in '.,;!?:':
            trailing = url[-1] + trailing
            url = url[:-1]

        while url.endswith(')') and url.count('(') < url.count(')'):
            trailing = ')' + trailing
            url = url[:-1]

        return f'<a href="{url}">{url}</a>{trailing}'

    return _BARE_URL_RE.sub(repl, text)


def _autolink_html(html: str) -> str:
    tokens = _HTML_TAG_RE.split(html)
    out: list[str] = []
    in_anchor = False
    in_code = False
    in_pre = False

    for token in tokens:
        if not token:
            continue

        if token.startswith('<'):
            match = re.match(r'<\s*(/)?\s*([a-zA-Z0-9]+)', token)
            if match:
                closing = bool(match.group(1))
                tag = match.group(2).lower()
                is_self_closing = token.rstrip().endswith('/>')

                if tag == 'a':
                    in_anchor = not closing and not is_self_closing
                elif tag == 'code':
                    in_code = not closing and not is_self_closing
                elif tag == 'pre':
                    in_pre = not closing and not is_self_closing

            out.append(token)
            continue

        if in_anchor or in_code or in_pre:
            out.append(token)
        else:
            out.append(_autolink_text_chunk(token))

    return ''.join(out)


def _blankify_html_links(html: str) -> str:
    def repl(match: re.Match) -> str:
        attrs = match.group(1)
        has_target = re.search(r'\btarget\s*=', attrs, flags=re.IGNORECASE)
        has_rel = re.search(r'\brel\s*=', attrs, flags=re.IGNORECASE)

        if not has_target:
            attrs += ' target="_blank"'
        if not has_rel:
            attrs += ' rel="noopener"'

        return f'<a{attrs}>'

    return re.sub(r'<a\b([^>]*)>', repl, html, flags=re.IGNORECASE)


def _normalize_html_links(html: str) -> str:
    return _blankify_html_links(_autolink_html(html))


def _optimize_html_images(html: str) -> str:
    def repl(match: re.Match) -> str:
        attrs = match.group(1)
        closing = ''

        if re.search(r'/\s*$', attrs):
            attrs = re.sub(r'/\s*$', '', attrs).rstrip()
            closing = ' /'

        if not re.search(r'\bloading\s*=', attrs, flags=re.IGNORECASE):
            attrs += ' loading="lazy"'
        if not re.search(r'\bdecoding\s*=', attrs, flags=re.IGNORECASE):
            attrs += ' decoding="async"'
        return f'<img{attrs}{closing}>'

    return _IMG_TAG_RE.sub(repl, html)


def _make_flag_block_html(flag: str) -> str:
    escaped = flag.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return (
        '\n<div class="flag-block my-8">'
        '\n<div class="flag-block__label font-mono text-xs font-bold uppercase tracking-widest text-green-t mb-2">Flag</div>'
        f'\n<code class="flag-block__value font-mono text-sm">{escaped}</code>'
        '\n</div>\n'
    )


def _normalize_reference_host(hostname: str) -> str:
    host = hostname.strip().lower()
    return host[4:] if host.startswith('www.') else host


def _fallback_reference_title(url: str) -> str:
    parsed = urlparse(url)
    host = _normalize_reference_host(parsed.hostname or parsed.netloc)
    segments = [unquote(segment).strip() for segment in parsed.path.split('/') if segment.strip()]

    while segments and segments[-1].lower() in {'index', 'default', 'home', 'amp'}:
        segments.pop()

    candidate = segments[-1] if segments else host
    candidate = re.sub(r'\.[a-z0-9]{1,8}$', '', candidate, flags=re.IGNORECASE)
    candidate = candidate.replace('-', ' ').replace('_', ' ')
    candidate = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', candidate)
    candidate = _normalize_whitespace(candidate)
    if not candidate:
        return host or url
    if candidate == candidate.lower():
        return candidate.title()
    return candidate[0].upper() + candidate[1:]


def _fetch_reference_title(url: str) -> str:
    if url in _REFERENCE_TITLE_CACHE:
        return _REFERENCE_TITLE_CACHE[url]

    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        _REFERENCE_TITLE_CACHE[url] = ''
        return ''

    request = Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; cnf409.me build bot/1.0)',
            'Accept': 'text/html,application/xhtml+xml',
        },
    )

    try:
        with urlopen(request, timeout=_REFERENCE_FETCH_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get_content_type()
            if content_type and 'html' not in content_type:
                _REFERENCE_TITLE_CACHE[url] = ''
                return ''
            payload = response.read(_REFERENCE_TITLE_MAX_BYTES)
    except Exception:
        _REFERENCE_TITLE_CACHE[url] = ''
        return ''

    match = _REFERENCE_TITLE_RE.search(payload.decode('utf-8', errors='ignore'))
    if not match:
        _REFERENCE_TITLE_CACHE[url] = ''
        return ''

    title = _normalize_whitespace(html_unescape(_HTML_TAG_RE.sub(' ', match.group(1))))
    _REFERENCE_TITLE_CACHE[url] = title
    return title


def _coerce_reference_entries(raw: object) -> list[dict[str, str]]:
    if raw is None:
        return []

    items = list(raw) if isinstance(raw, (list, tuple)) else [raw]
    references: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in items:
        title = ''
        if isinstance(item, dict):
            url = str(item.get('url', '')).strip()
            title = str(item.get('title', item.get('label', ''))).strip()
        else:
            url = str(item).strip()

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        references.append({'url': url, 'title': title})

    return references


def _build_reference_card(reference: dict[str, str]) -> dict | None:
    url = reference.get('url', '').strip()
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return None

    host = _normalize_reference_host(parsed.hostname or parsed.netloc)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    title = reference.get('title', '').strip() or _fetch_reference_title(url) or _fallback_reference_title(url)

    return {
        'url': url,
        'title': title,
        'host': host,
        'favicon_url': f'https://www.google.com/s2/favicons?sz=64&domain_url={quote(origin, safe="")}',
    }


def md_to_html(body: str, flag: str = '') -> tuple[str, str, bool]:
    flag_inline = bool(flag and _FLAG_MARKER_RE.search(body))
    if flag_inline:
        body = _FLAG_MARKER_RE.sub(_make_flag_block_html(flag), body)
    body = _normalize_markdown_images(body)
    body = _normalize_php_fences(body)
    body = _TERMINAL_RE.sub(_terminal_replace, body)
    parser = markdown.Markdown(
        extensions=['fenced_code', 'tables', 'toc', 'codehilite', 'attr_list', 'md_in_html'],
        extension_configs={
            'codehilite': {'css_class': 'highlight', 'guess_lang': True, 'use_pygments': True},
            'toc': {},
        },
    )
    html = _optimize_html_images(_normalize_html_links(parser.convert(body)))
    return html, parser.toc, flag_inline


class Post:
    def __init__(
        self,
        meta: dict,
        html: str,
        toc: str,
        dir_path: Path,
        source_path: Path,
        raw_body: str,
        flag_inline: bool = False,
    ) -> None:
        self.meta  = meta
        self.html  = html
        self.toc   = toc
        self.dir   = dir_path
        self.source_path = source_path
        self.raw_body = raw_body
        self.slug  = dir_path.name
        self.flag_inline = flag_inline

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

        raw_last_updated = meta.get('updated', meta.get('last_updated'))
        self.last_updated = (
            _coerce_datetime(raw_last_updated)
            or _git_last_commit_date(source_path)
            or _path_mtime(source_path)
        )
        if self.last_updated and self.date != datetime.min and self.last_updated < self.date:
            self.last_updated = self.date

        self.event               = meta.get('event', '')
        self.event_slug          = slugify(self.event) if self.event else ''
        self.category            = meta.get('category', '')
        self.difficulty          = meta.get('difficulty', '')
        self.stars               = meta.get('stars')
        raw_solves               = meta.get('solves')
        self.solves              = raw_solves
        if isinstance(raw_solves, str) and raw_solves.strip() == '?':
            self.solves_display = '???'
        elif raw_solves is None:
            self.solves_display = ''
        else:
            self.solves_display = str(raw_solves)
        author_names = _split_csv_list(meta.get('challenge_author', []))
        author_urls = _split_csv_list(meta.get('challenge_author_url', []))
        self.challenge_author_names = author_names
        self.challenge_author_urls = author_urls
        self.challenge_author = ', '.join(author_names)
        self.challenge_author_url = ', '.join(author_urls)
        self.challenge_authors = [
            {
                'name': name,
                'url': author_urls[idx] if idx < len(author_urls) else '',
            }
            for idx, name in enumerate(author_names)
        ]
        self.rating              = meta.get('rating')
        self.flag                = meta.get('flag', '')

        self.platform      = meta.get('platform', '')
        self.os            = meta.get('os', '')
        self.description   = meta.get('description', '')
        raw_redirects      = meta.get('redirect_from', [])
        self.redirect_from = _coerce_str_list(raw_redirects)
        raw_references = meta.get('references', meta.get('related_articles', meta.get('related', [])))
        self.references = [
            card
            for card in (_build_reference_card(reference) for reference in _coerce_reference_entries(raw_references))
            if card
        ]
        self.reading_time_minutes = _estimate_reading_time(raw_body)
        self.reading_time_label = f'{self.reading_time_minutes} min read'
        self.excerpt = _make_excerpt(raw_body, fallback=self.description)

        self.sources     = self._list_files('sources')
        self.solve_files = self._list_files('solve')

    def _list_files(self, subdir: str) -> list[str]:
        d = self.dir / subdir
        if not d.exists():
            return []

        files: list[dict] = []
        for file_path in sorted((f for f in d.iterdir() if f.is_file()), key=lambda p: p.name.lower()):
            inline_source = _read_inline_source(file_path)
            files.append({
                'name': file_path.name,
                'stem': file_path.stem,
                'ext':  file_path.suffix,
                'size_bytes': file_path.stat().st_size,
                'size_label': _format_file_size(file_path.stat().st_size),
                'raw_url': f"/posts/{self.slug}/{subdir}/{quote(file_path.name)}",
                'viewer_url': f"/posts/{self.slug}/_fileview/{subdir}/{quote(file_path.name)}/" if inline_source is not None else '',
                'inline_view': inline_source is not None,
            })

        return files

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
    def last_updated_str(self) -> str:
        return _format_date(self.last_updated)

    @property
    def last_updated_iso(self) -> str:
        return self.last_updated.strftime('%Y-%m-%d') if self.last_updated else ''

    @property
    def has_last_updated(self) -> bool:
        return bool(
            self.last_updated
            and self.date != datetime.min
            and self.last_updated.date() != self.date.date()
        )

    @property
    def context_label(self) -> str:
        if self.type == 'ctf':
            return self.event or self.category
        if self.type == 'box':
            return self.platform or self.os
        return self.author

    @property
    def keywords(self) -> str:
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
            'last_updated_str': self.last_updated_str, 'last_updated_iso': self.last_updated_iso,
            'has_last_updated': self.has_last_updated,
            'language': self.language, 'language_code': self.language_code, 'language_label': self.language_label,
            'language_flag': self.language_flag,
            'url': self.url, 'slug': self.slug,
            'event': self.event, 'event_slug': self.event_slug,
            'category': self.category, 'difficulty': self.difficulty, 'stars': self.stars,
            'solves': self.solves, 'solves_display': self.solves_display,
            'challenge_author': self.challenge_author,
            'challenge_author_url': self.challenge_author_url,
            'challenge_author_names': self.challenge_author_names,
            'challenge_author_urls': self.challenge_author_urls,
            'challenge_authors': self.challenge_authors,
            'rating': self.rating, 'flag': self.flag, 'flag_inline': self.flag_inline,
            'platform': self.platform, 'os': self.os,
            'description': self.description,
            'excerpt': self.excerpt,
            'context_label': self.context_label,
            'reading_time_minutes': self.reading_time_minutes,
            'reading_time_label': self.reading_time_label,
            'keywords': self.keywords,
            'html': self.html, 'toc': self.toc,
            'references': self.references,
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
        meta, body       = parse_frontmatter(md_file.read_text(encoding='utf-8'))
        flag             = str(meta.get('flag', ''))
        html, toc, flag_inline = md_to_html(body, flag=flag)
        return Post(meta, html, toc, dir_path, md_file, body, flag_inline=flag_inline)
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


def reset_public_dir(verbose: bool = False) -> None:
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
        print('  [+] Cleaned public/' if verbose else '  [+] Reset public/')
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def load_about() -> tuple[dict, str]:
    about_file = ROOT / 'about.md'
    if about_file.exists():
        meta, body = parse_frontmatter(about_file.read_text(encoding='utf-8'))
        html, _, _ = md_to_html(body)
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
            html, _, _ = md_to_html(body)
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
    post_dicts = [p.as_dict() for p in posts]

    for idx, post in enumerate(posts):
        newer_post = post_dicts[idx - 1] if idx > 0 else None
        older_post = post_dicts[idx + 1] if idx + 1 < len(post_dicts) else None
        write_page(
            PUBLIC_DIR / 'posts' / post.slug / 'index.html',
            render(
                env,
                'post.html',
                post=post_dicts[idx],
                newer_post=newer_post,
                older_post=older_post,
            ),
        )


def build_post_file_views(env: Environment, posts: list[Post]) -> None:
    for post in posts:
        post_dict = post.as_dict()

        for subdir, files in (('sources', post.sources), ('solve', post.solve_files)):
            for file_info in files:
                if not file_info['inline_view']:
                    continue

                source_path = post.dir / subdir / file_info['name']
                source = _read_inline_source(source_path)
                if source is None:
                    continue

                file_ctx = dict(file_info)
                file_ctx['kind_label'] = 'Solve script' if subdir == 'solve' else 'Challenge file'
                file_ctx['kind'] = subdir

                write_page(
                    PUBLIC_DIR / 'posts' / post.slug / '_fileview' / subdir / file_info['name'] / 'index.html',
                    render(
                        env,
                        'file_view.html',
                        post=post_dict,
                        file=file_ctx,
                        highlighted_code=_highlight_source(file_info['name'], source),
                    ),
                )


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


def build_search_index(posts: list[Post], events: list[dict]) -> None:
    items: list[dict] = []
    tags: dict[str, int] = {}
    about_meta, _ = load_about()

    items.append({
        'title': 'About',
        'url': '/about/',
        'kind': 'page',
        'kind_label': 'Page',
        'subtitle': str(about_meta.get('tagline', '')).strip(),
        'description': 'Background, current focus and links.',
        'search_text': _normalize_whitespace(
            f"about {about_meta.get('name', '')} {about_meta.get('tagline', '')} {about_meta.get('location', '')} {about_meta.get('school', '')}"
        ).lower(),
        'priority': 90,
        'date_iso': '',
    })

    for post in posts:
        for tag in post.tags:
            tags[tag] = tags.get(tag, 0) + 1

        subtitle_parts = [post.context_label]
        if post.type == 'ctf' and post.category:
            subtitle_parts.append(post.category)
        if post.type == 'box' and post.os:
            subtitle_parts.append(post.os)
        if post.date_str:
            subtitle_parts.append(post.date_str)

        kind_label = {
            'ctf': 'CTF writeup',
            'box': 'Box writeup',
            'post': 'Post',
        }.get(post.type, 'Post')

        items.append({
            'title': post.title,
            'url': post.url,
            'kind': post.type,
            'kind_label': kind_label,
            'subtitle': ' · '.join(part for part in subtitle_parts if part),
            'description': post.description or post.excerpt,
            'search_text': _normalize_whitespace(
                ' '.join([
                    post.title,
                    post.description,
                    post.excerpt,
                    post.author,
                    post.event,
                    post.category,
                    post.platform,
                    post.os,
                    post.challenge_author,
                    ' '.join(post.tags),
                ])
            ).lower(),
            'priority': 320 if post.pinned else 220,
            'date_iso': post.date_iso,
        })

    for event in events:
        items.append({
            'title': event['title'],
            'url': f"/events/{event['slug']}/",
            'kind': 'event',
            'kind_label': 'Event',
            'subtitle': ' · '.join(part for part in [
                event.get('date_range', ''),
                f"{event.get('writeup_count', 0)} writeup(s)",
            ] if part),
            'description': _make_excerpt(event.get('html', ''), limit=120) if event.get('html') else '',
            'search_text': _normalize_whitespace(
                ' '.join([
                    event['title'],
                    ' '.join(event.get('organizers', [])),
                    ' '.join(event.get('organizer_countries', [])),
                    ' '.join(post['title'] for post in event.get('posts', [])),
                ])
            ).lower(),
            'priority': 140 + int(event.get('writeup_count', 0)),
            'date_iso': event.get('end_date_iso') or event.get('start_date_iso') or '',
        })

    for tag, count in sorted(tags.items(), key=lambda item: item[0].lower()):
        items.append({
            'title': f'#{tag}',
            'url': f"/tags/{slugify(tag)}/",
            'kind': 'tag',
            'kind_label': 'Tag',
            'subtitle': f'{count} post(s)',
            'description': '',
            'search_text': _normalize_whitespace(f'tag {tag}').lower(),
            'priority': 60 + count,
            'date_iso': '',
        })

    (PUBLIC_DIR / 'search-index.json').write_text(
        json.dumps({'items': items}, ensure_ascii=False),
        encoding='utf-8',
    )
    print('  [+] Search index generated')


def build_sitemap(config: dict, posts: list[Post], events: list[dict]) -> None:
    base = config['site']['base_url'].rstrip('/')

    urls: list[dict] = [
        {'loc': f'{base}/',        'changefreq': 'weekly',  'priority': '1.0'},
        {'loc': f'{base}/posts/',  'changefreq': 'weekly',  'priority': '0.8'},
        {'loc': f'{base}/events/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'loc': f'{base}/tags/',   'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f'{base}/about/',  'changefreq': 'monthly', 'priority': '0.7'},
    ]

    tag_lastmods: dict[str, datetime] = {}

    for post in posts:
        entry: dict = {'loc': f'{base}{post.url}', 'changefreq': 'monthly', 'priority': '0.9'}
        lastmod = post.last_updated or (post.date if post.date != datetime.min else None)
        if lastmod:
            entry['lastmod'] = lastmod.strftime('%Y-%m-%d')
        urls.append(entry)

        if lastmod:
            for tag in post.tags:
                current = tag_lastmods.get(tag)
                if current is None or lastmod > current:
                    tag_lastmods[tag] = lastmod

    for event in events:
        entry = {'loc': f'{base}/events/{event["slug"]}/', 'changefreq': 'monthly', 'priority': '0.6'}
        event_lastmod = event.get('end_date_iso') or event.get('start_date_iso')
        if event_lastmod:
            entry['lastmod'] = event_lastmod
        urls.append(entry)

    tags: set[str] = set()
    for post in posts:
        tags.update(post.tags)
    for tag in sorted(tags):
        entry = {'loc': f'{base}/tags/{slugify(tag)}/', 'changefreq': 'monthly', 'priority': '0.4'}
        if tag in tag_lastmods:
            entry['lastmod'] = tag_lastmods[tag].strftime('%Y-%m-%d')
        urls.append(entry)

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


def build_robots(config: dict) -> None:
    base = config['site']['base_url'].rstrip('/')
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /posts/*/_fileview/',
        'Disallow: /posts/*/solve/',
        'Disallow: /posts/*/sources/',
        f'Sitemap: {base}/sitemap.xml',
    ]
    (PUBLIC_DIR / 'robots.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('  [+] robots.txt generated')


def build_rss(config: dict, posts: list[Post]) -> None:
    site  = config['site']
    base  = site['base_url'].rstrip('/')
    limit = 42

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '<channel>',
        f'  <title>{_xml_escape(site["title"])}</title>',
        f'  <link>{base}/</link>',
        f'  <description>{_xml_escape(site["description"])}</description>',
        f'  <atom:link href="{base}/rss.xml" rel="self" type="application/rss+xml"/>',
        '  <language>en-us</language>',
        f'  <lastBuildDate>{_rfc2822(datetime.now())}</lastBuildDate>',
        f'  <generator>conflict-blog-builder</generator>',
    ]

    for post in posts[:limit]:
        link     = f'{base}{post.url}'
        desc_raw = post.description or post.title
        lines += [
            '  <item>',
            f'    <title>{_xml_escape(post.title)}</title>',
            f'    <link>{link}</link>',
            f'    <guid isPermaLink="true">{link}</guid>',
        ]
        if post.date != datetime.min:
            lines.append(f'    <pubDate>{_rfc2822(post.date)}</pubDate>')
        lines.append(f'    <description>{_xml_escape(desc_raw)}</description>')
        for tag in post.tags:
            lines.append(f'    <category>{_xml_escape(tag)}</category>')
        lines.append('  </item>')

    lines += ['</channel>', '</rss>']
    (PUBLIC_DIR / 'rss.xml').write_text('\n'.join(lines), encoding='utf-8')
    print('  [+] RSS feed generated')


def build_redirects(posts: list[Post]) -> None:
    count = 0
    for post in posts:
        for old_url in post.redirect_from:
            old_path = old_url.strip('/')
            dest = PUBLIC_DIR / old_path / 'index.html'
            new_url = post.url
            html = (
                '<!DOCTYPE html>\n<html>\n<head>\n'
                '<meta charset="UTF-8">\n'
                f'<meta http-equiv="refresh" content="0; url={new_url}">\n'
                f'<link rel="canonical" href="{new_url}">\n'
                f'<script>window.location.replace("{new_url}");</script>\n'
                '</head>\n<body></body>\n</html>'
            )
            write_page(dest, html)
            count += 1
    if count:
        print(f'  [+] Redirects: {count} legacy URL(s)')


def build_404(env: Environment) -> None:
    write_page(PUBLIC_DIR / '404.html', render(env, '404.html'))


def build(config: dict, clean: bool = False, include_drafts: bool = False) -> None:
    reset_public_dir(verbose=clean)

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
    build_post_file_views(env, posts)
    build_posts_list(env, posts, config)
    build_tag_pages(env, posts)
    build_event_pages(env, events)
    build_events_index(env, events)
    build_about(env)
    build_search_index(posts, events)

    print('  [+] Post assets...')
    copy_post_assets(posts)
    copy_event_assets(events)

    print('  [+] Redirects...')
    build_redirects(posts)

    print('  [+] RSS & sitemap...')
    build_rss(config, posts)
    build_sitemap(config, posts, events)
    build_robots(config)
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
