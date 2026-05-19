"""Tests for read_online_paper function."""

import pytest
from unittest.mock import AsyncMock, patch
from mcp_server_papers.server import read_online_paper


@pytest.mark.anyio
async def test_read_online_returns_content(arxiv_html_fixture):
    """Verify read_online returns the actual HTML content."""
    arxiv_id = "2510.04618"

    with patch("mcp_server_papers.server.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.text = arxiv_html_fixture
        mock_response.raise_for_status = AsyncMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = await read_online_paper(arxiv_id)

        # Result should contain the actual HTML content
        assert "Quantum Computing" in result
        assert "Figure 1: Quantum gates" in result
        assert len(result) > 100  # Non-trivial content


@pytest.mark.anyio
async def test_read_online_invalid_arxiv_id():
    """Verify read_online raises ValueError on invalid arXiv ID."""
    invalid_id = "not-a-valid-id!!!"

    with pytest.raises(ValueError, match="Invalid arXiv ID"):
        await read_online_paper(invalid_id)


@pytest.mark.anyio
async def test_read_online_404_not_found():
    """Verify read_online handles 404 gracefully."""
    from httpx import HTTPStatusError, Request

    arxiv_id = "9999.99999"

    with patch("mcp_server_papers.server.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404

        # raise_for_status is synchronous in httpx
        def raise_404():
            raise HTTPStatusError(
                "404 Not Found",
                request=Request("GET", "https://arxiv.org/html/9999.99999"),
                response=mock_response
            )

        mock_response.raise_for_status = raise_404

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await read_online_paper(arxiv_id)
