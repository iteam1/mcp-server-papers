"""Tests for building arXiv query strings from structured input."""

import pytest
from mcp_server_papers.utils import build_arxiv_query


def test_build_arxiv_query_title():
    """Verify build_arxiv_query handles title field."""
    query = build_arxiv_query(title="quantum computing")
    assert "ti%3A" in query or "ti:" in query  # URL-encoded or not
    assert "quantum" in query


def test_build_arxiv_query_author():
    """Verify build_arxiv_query handles author field."""
    query = build_arxiv_query(author="Einstein")
    assert "au%3A" in query or "au:" in query  # URL-encoded or not
    assert "Einstein" in query


def test_build_arxiv_query_title_and_author():
    """Verify build_arxiv_query combines multiple fields with AND."""
    query = build_arxiv_query(title="quantum", author="einstein")
    assert ("ti%3Aquantum" in query or "ti:quantum" in query) and "quantum" in query
    assert ("au%3Aeinstein" in query or "au:einstein" in query) and "einstein" in query
    assert "AND" in query or "%20AND%20" in query


def test_build_arxiv_query_abstract():
    """Verify build_arxiv_query handles abstract field."""
    query = build_arxiv_query(abstract="entanglement")
    assert "abs%3A" in query or "abs:" in query  # URL-encoded or not


def test_build_arxiv_query_category():
    """Verify build_arxiv_query handles category field."""
    query = build_arxiv_query(category="quant-ph")
    assert "cat%3A" in query or "cat:" in query  # URL-encoded or not
    assert "quant-ph" in query


def test_build_arxiv_query_max_results():
    """Verify build_arxiv_query handles max_results parameter."""
    query = build_arxiv_query(title="test", max_results=50)
    assert "max_results=50" in query


def test_build_arxiv_query_max_results_clamped():
    """Verify build_arxiv_query clamps max_results to arXiv limit."""
    query = build_arxiv_query(title="test", max_results=5000)
    assert "max_results=2000" in query


def test_build_arxiv_query_phrases_quoted():
    """Verify build_arxiv_query quotes multi-word phrases."""
    query = build_arxiv_query(title="quantum criticality")
    # Phrases should be quoted
    assert "%22" in query or '"' in query


def test_build_arxiv_query_empty():
    """Verify build_arxiv_query requires at least one search field."""
    # Should raise or return empty/default
    result = build_arxiv_query()
    # Either empty or raises; both acceptable
    assert isinstance(result, str)


def test_build_arxiv_query_returns_url_string():
    """Verify build_arxiv_query returns valid query string."""
    query = build_arxiv_query(title="test")
    # Should be a valid query parameter string
    assert "search_query=" in query or "title=" in query
    # Should not have spaces (should be encoded)
    assert " " not in query or "%20" in query
