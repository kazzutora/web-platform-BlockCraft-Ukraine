from apps.mods.markdown import render_markdown


def test_markdown_and_safe_html_are_kept():
    html = render_markdown(
        "# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        '<p align="center"><img src="https://cdn.x/a.png" alt="A"></p>'
    )

    assert "<h1>Title</h1>" in html
    assert "<table>" in html
    assert '<p align="center">' in html
    assert 'loading="lazy"' in html


def test_scripts_handlers_and_frames_are_removed():
    html = render_markdown(
        '<script>alert(1)</script><img src="x" onerror="alert(1)">'
        '<iframe src="https://evil"></iframe><a href="javascript:alert(1)">x</a>'
        "<style>body{display:none}</style>"
    )

    assert "script" not in html
    assert "onerror" not in html
    assert "iframe" not in html
    assert "javascript:" not in html
    assert "<style" not in html


def test_links_get_safe_rel():
    html = render_markdown("[Sodium](https://modrinth.com/mod/sodium)")

    assert 'rel="noopener noreferrer nofollow"' in html


def test_empty_description():
    assert render_markdown("") == ""


def test_images_without_alt_become_decorative():
    html = render_markdown('<img src="https://cdn.x/a.png"><img src="https://cdn.x/b.png" alt="B">')

    assert html.count('alt=""') == 1
    assert 'alt="B"' in html
