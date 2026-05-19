"""Tests for HTML extraction and parsing."""

import pytest
from mcp_server_papers.utils import extract_paper_text


def test_extract_paper_text_basic(arxiv_html_fixture):
    """Verify extract_paper_text returns readable text."""
    result = extract_paper_text(arxiv_html_fixture)

    # Should contain meaningful content
    assert result is not None
    assert len(result) > 0
    # Should preserve key content
    assert "Quantum" in result or "computing" in result.lower()
    # Should be significantly shorter than raw HTML
    assert len(result) < len(arxiv_html_fixture)


def test_extract_paper_text_strips_html_tags(arxiv_html_fixture):
    """Verify extract_paper_text removes HTML markup."""
    result = extract_paper_text(arxiv_html_fixture)

    # Should not contain HTML tags
    assert "<" not in result
    assert ">" not in result
    assert "<html>" not in result


def test_extract_paper_text_empty_input():
    """Verify extract_paper_text handles empty input."""
    result = extract_paper_text("")
    assert result == "" or result is None or len(result.strip()) == 0


def test_extract_paper_text_minimal_content():
    """Verify extract_paper_text returns fallback on minimal content."""
    minimal_html = "<html><body>Hi</body></html>"
    result = extract_paper_text(minimal_html)
    # Should either return minimal extracted text or the original
    assert result is not None
    assert len(result) > 0


def test_extract_paper_text_with_script_and_style():
    """Verify extract_paper_text removes script and style tags."""
    html_with_junk = """
    <html>
    <head>
        <style>body { color: red; }</style>
        <script>alert('xss');</script>
    </head>
    <body>
        <h1>Important Content</h1>
        <p>Real paragraph text.</p>
    </body>
    </html>
    """
    result = extract_paper_text(html_with_junk)

    # Should have the real content
    assert "Important Content" in result or "Real paragraph" in result
    # Should NOT have style or script content
    assert "color: red" not in result
    assert "alert" not in result
    assert "xss" not in result
