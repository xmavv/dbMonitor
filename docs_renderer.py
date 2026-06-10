import json
import os
import re

import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension, slugify

DOCS_CONTENT_DIR = os.path.join(os.path.dirname(__file__), "docs", "content")

PAGES = [
    {"slug": None, "title": "Overview", "file": "overview.md", "nav_section": "Introduction"},
    {"slug": "getting-started", "title": "Getting Started", "file": "getting-started.md", "nav_section": "Introduction"},
    {"slug": "configuration", "title": "Configuration", "file": "configuration.md", "nav_section": "Introduction"},
    {"slug": "api", "title": "API Reference", "file": "api.md", "nav_section": "Introduction"},
    {"slug": "color-legend", "title": "Color Legend", "file": "color-legend.md", "nav_section": "Dashboard Panels"},
    {"slug": "top-queries", "title": "Top Queries", "file": "top-queries.md", "nav_section": "Dashboard Panels"},
    {"slug": "table-health", "title": "Table Health", "file": "table-health.md", "nav_section": "Dashboard Panels"},
    {"slug": "db-sizes", "title": "DB Sizes", "file": "db-sizes.md", "nav_section": "Dashboard Panels"},
    {"slug": "index-usage", "title": "Index Usage", "file": "index-usage.md", "nav_section": "Dashboard Panels"},
    {"slug": "lock-monitor", "title": "Lock Monitor", "file": "lock-monitor.md", "nav_section": "Dashboard Panels"},
    {"slug": "triggers", "title": "Triggers", "file": "triggers.md", "nav_section": "Dashboard Panels"},
    {"slug": "extensions", "title": "Extensions", "file": "extensions.md", "nav_section": "Dashboard Panels"},
    {"slug": "explain", "title": "Query Plan Analysis", "file": "explain.md", "nav_section": "Advanced"},
    {"slug": "anomaly-log", "title": "Anomaly Log", "file": "anomaly-log.md", "nav_section": "Advanced"},
    {"slug": "scenarios", "title": "Common Scenarios", "file": "scenarios.md", "nav_section": "Advanced"},
]

_md = markdown.Markdown(extensions=["extra", "fenced_code", TableExtension(), TocExtension(baselevel=1)])


def _page_by_slug(slug):
    for page in PAGES:
        if page["slug"] == slug:
            return page
    return None


def _read_source(filename):
    path = os.path.join(DOCS_CONTENT_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _heading_anchor(heading):
    return slugify(heading, "-")


def _extract_sections(source):
    sections = []
    for match in re.finditer(r"^(#{1,3})\s+(.+)$", source, re.MULTILINE):
        level = len(match.group(1))
        heading = match.group(2).strip()
        anchor = _heading_anchor(heading)
        start = match.end()
        next_heading = re.search(r"^#{1,3}\s+", source[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(source)
        body = source[start:end].strip()
        sections.append({
            "level": level,
            "heading": heading,
            "anchor": anchor,
            "text": _strip_html(body),
        })
    if not sections:
        sections.append({
            "level": 1,
            "heading": "",
            "anchor": "",
            "text": _strip_html(source),
        })
    return sections


def page_url(slug):
    if slug is None:
        return "/docs"
    return f"/docs/{slug}"


def get_nav_sections():
    sections = []
    seen = []
    for page in PAGES:
        section = page["nav_section"]
        if section not in seen:
            seen.append(section)
            sections.append({"name": section, "pages": []})
        sections[-1]["pages"].append({
            **page,
            "url": page_url(page["slug"]),
        })
    return sections


def render_page(slug):
    page = _page_by_slug(slug)
    if page is None:
        return None
    source = _read_source(page["file"])
    _md.reset()
    html = _md.convert(source)
    return {
        "page": page,
        "html": html,
        "sections": _extract_sections(source),
    }


def build_search_index():
    index = []
    for page in PAGES:
        source = _read_source(page["file"])
        sections = _extract_sections(source)
        full_text = _strip_html(source)
        index.append({
            "title": page["title"],
            "slug": page["slug"],
            "url": page_url(page["slug"]),
            "summary": full_text[:240],
            "sections": sections,
            "full_text": full_text,
        })
    return index


def search_index_json():
    return json.dumps(build_search_index(), ensure_ascii=False)
