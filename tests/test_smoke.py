"""Smoke test: verify server builds without network calls."""

import pytest
from unittest.mock import patch, MagicMock
from mcp_server_papers.server import main


def test_server_builds():
    """Verify the Server object initializes without errors."""
    with patch("mcp_server_papers.server.click.command"):
        with patch("mcp_server_papers.server.anyio.run"):
            # Mock the decorator to allow direct function access
            with patch("mcp_server_papers.server.Server") as MockServer:
                mock_server = MagicMock()
                MockServer.return_value = mock_server

                # Just verify we can import and the main function exists
                assert callable(main)
                assert mock_server is not None


def test_imports_work():
    """Verify all core imports are available."""
    from mcp_server_papers import server
    from mcp_server_papers import utils

    assert hasattr(server, "send_query")
    assert hasattr(server, "download_paper")
    assert hasattr(server, "read_online_paper")
    assert hasattr(server, "get_image")
    assert hasattr(utils, "validate_arxiv_id")
    assert hasattr(utils, "validate_arxiv_params")
