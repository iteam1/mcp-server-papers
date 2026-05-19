import pytest
import httpx
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_httpx_client():
    """Provide a mock httpx.AsyncClient for testing without network calls."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        yield mock_client


@pytest.fixture
def arxiv_html_fixture():
    """Sample arXiv HTML for testing."""
    return """<!DOCTYPE html>
<html>
<head><title>Sample Paper</title></head>
<body>
<h1>Quantum Computing and Its Applications</h1>
<p>This is a sample paper about quantum computing.</p>
<figure>
<img src="x1.png" alt="Figure 1">
<figcaption>Figure 1: Quantum gates</figcaption>
</figure>
</body>
</html>
"""


@pytest.fixture
def arxiv_atom_fixture():
    """Sample arXiv Atom feed for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query Results</title>
  <link href="http://arxiv.org/api/query?search_query=all:electron&amp;start=0&amp;max_results=1" rel="self" type="application/atom+xml"/>
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1000</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2510.26784v1</id>
    <published>2025-10-01T18:02:09Z</published>
    <updated>2025-10-01T18:02:09Z</updated>
    <title>Sample Quantum Paper</title>
    <summary>This is a sample abstract about quantum computing.</summary>
    <author><name>John Doe</name></author>
    <link href="http://arxiv.org/abs/2510.26784v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2510.26784v1" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="quant-ph"/>
    <category term="quant-ph"/>
  </entry>
</feed>
"""
