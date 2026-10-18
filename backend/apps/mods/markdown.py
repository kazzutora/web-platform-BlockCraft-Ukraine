"""Modrinth descriptions are Markdown with raw HTML: render once at sync time, then sanitize."""

import re

import nh3
from markdown_it import MarkdownIt

_markdown = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
# Images without a description are decorative for screen readers (WCAG image-alt)
_IMG_WITHOUT_ALT = re.compile(r"<img(?![^>]*\balt=)")

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "center", "code", "del", "details", "div", "em",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "kbd", "li", "ol", "p", "pre", "s",
    "small", "span", "strong", "sub", "summary", "sup", "table", "tbody", "td", "th", "thead",
    "tr", "u", "ul",
}  # fmt: skip

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"align"},
    "th": {"align"},
    "p": {"align"},
    "div": {"align"},
    "h1": {"align"},
    "h2": {"align"},
    "h3": {"align"},
}


def render_markdown(source: str) -> str:
    """Markdown → HTML without scripts, styles, iframes or event handlers."""
    if not source:
        return ""
    html = nh3.clean(
        _markdown.render(source),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
        set_tag_attribute_values={"img": {"loading": "lazy"}},
    )
    return _IMG_WITHOUT_ALT.sub('<img alt=""', html)
