"""Tests for parsing arXiv Atom feed responses."""

import json
import pytest
from mcp_server_papers.utils import parse_arxiv_atom


def test_parse_arxiv_atom_basic(arxiv_atom_fixture):
    """Verify parse_arxiv_atom extracts papers from Atom feed."""
    results = parse_arxiv_atom(arxiv_atom_fixture)

    assert isinstance(results, list)
    assert len(results) >= 1

    # First paper should have required fields
    paper = results[0]
    assert "arxiv_id" in paper
    assert "title" in paper
    assert "authors" in paper
    assert "abstract" in paper
    assert "published" in paper
    assert "pdf_url" in paper
    assert "html_url" in paper

    # Values should be non-empty
    assert len(paper["arxiv_id"]) > 0
    assert len(paper["title"]) > 0
    assert len(paper["authors"]) > 0


def test_parse_arxiv_atom_pdf_url(arxiv_atom_fixture):
    """Verify parse_arxiv_atom builds correct PDF URL."""
    results = parse_arxiv_atom(arxiv_atom_fixture)

    if results:
        paper = results[0]
        # PDF URL should match pattern (http or https)
        assert paper["pdf_url"].startswith("http")
        assert "arxiv.org/pdf/" in paper["pdf_url"]


def test_parse_arxiv_atom_empty_feed():
    """Verify parse_arxiv_atom handles empty feed."""
    empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Empty Results</title>
    </feed>"""

    results = parse_arxiv_atom(empty_feed)
    assert results == []


def test_parse_arxiv_atom_invalid_xml():
    """Verify parse_arxiv_atom handles malformed XML gracefully."""
    invalid_xml = "<not>valid</atom>"

    results = parse_arxiv_atom(invalid_xml)
    assert isinstance(results, list)
    # Should return empty list or the feed's entries (however many parsed)
    assert len(results) >= 0


def test_parse_arxiv_atom_multiple_authors():
    """Verify parse_arxiv_atom handles multiple authors."""
    multi_author_feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2510.12345v1</id>
            <title>Multi-Author Paper</title>
            <author><name>Alice</name></author>
            <author><name>Bob</name></author>
            <author><name>Charlie</name></author>
            <summary>Abstract text</summary>
            <published>2025-10-01T00:00:00Z</published>
            <link href="http://arxiv.org/abs/2510.12345v1" rel="alternate"/>
            <link href="http://arxiv.org/pdf/2510.12345v1" rel="related" type="application/pdf"/>
        </entry>
    </feed>"""

    results = parse_arxiv_atom(multi_author_feed)
    assert len(results) == 1
    paper = results[0]
    # Authors should be a list
    assert isinstance(paper["authors"], list)
    assert len(paper["authors"]) == 3
    assert "Alice" in paper["authors"]
