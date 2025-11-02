import anyio
import click
import httpx
import logging
import mcp.types as types
from pathlib import Path
from typing import Any
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from pydantic import AnyUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Tools
async def send_query(params: str) -> str:
    """
    Send a query to arXiv API and return the response.
    """
    try:
        url = f"http://export.arxiv.org/api/query?{params}"
        logger.info(f"Sending query to arXiv: {url}")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.RequestError as e:
        logger.error(f"Network error querying arXiv: {e}")
        raise ValueError(f"Failed to query arXiv API: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from arXiv: {e.response.status_code}")
        raise ValueError(f"arXiv API returned error: {e.response.status_code}")


# Read resource
def read_api_specification() -> str:
    """Read the API specification from the docs directory."""
    try:
        # Get the project root directory
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        api_doc_path = project_root / "docs" / "API.md"

        if not api_doc_path.exists():
            raise FileNotFoundError(f"API documentation not found at {api_doc_path}")

        return api_doc_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read API specification: {e}")
        raise ValueError(f"Could not load API documentation: {e}")


# Define CLI
@click.command()
@click.option("--port", default=8000, help="Port to listen on for server")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> None:
    # Define server
    app = Server("mcp-server-papers")

    # Define tools
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="send_query",
                title="Search arXiv Papers",
                description="Search for academic papers on arXiv using query parameters. Supports field-specific searches (ti:, au:, abs:, etc.) and Boolean operators (AND, OR, ANDNOT).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "arXiv API query parameters (e.g., 'search_query=au:einstein&max_results=10' or 'id_list=1234.5678'). See API documentation for full syntax.",
                            "examples": [
                                "search_query=ti:quantum&max_results=5",
                                "search_query=au:einstein+AND+ti:relativity",
                                "id_list=2301.00001,2301.00002",
                            ],
                        }
                    },
                    "required": ["query"],
                },
            )
        ]

    @app.call_tool()
    async def fetch_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.ContentBlock]:
        if name == "send_query":
            if "query" not in arguments:
                raise ValueError("Missing query parameter")

            try:
                response = await send_query(arguments["query"])
                return [types.TextContent(type="text", text=response)]
            except Exception as e:
                logger.error(f"Error executing send_query tool: {e}")
                return [types.TextContent(type="text", text=f"Error: {e}")]
        else:
            raise ValueError(f"Unknown tool: {name}")

    # Define resources
    @app.list_resources()
    async def list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri="docs://api",
                name="API Specification",
                description="API specification for this server",
                mimeType="text/markdown",
            )
        ]

    @app.read_resource()
    async def read_resource(uri: AnyUrl):
        uri_str = str(uri)
        if uri_str == "docs://api":
            try:
                content = read_api_specification()
                return [
                    ReadResourceContents(content=content, mime_type="text/markdown")
                ]
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise ValueError(f"Failed to read resource {uri}: {e}")
        else:
            raise ValueError(f"Unknown resource: {uri}")

    # Handle different transports
    if transport == "streamable-http":
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        import contextlib

        # Create session manager
        session_manager = StreamableHTTPSessionManager(app=app)

        # Lifespan context manager
        @contextlib.asynccontextmanager
        async def lifespan(starlette_app: Starlette):
            async with session_manager.run():
                yield

        # Create Starlette application
        starlette_app = Starlette(debug=True, lifespan=lifespan)

        # Add CORS middleware
        starlette_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Create ASGI application wrapper for session manager
        class MCPASGIApp:
            def __init__(self, session_manager):
                self.session_manager = session_manager

            async def __call__(self, scope, receive, send):
                await self.session_manager.handle_request(scope, receive, send)

        # Mount the MCP ASGI app
        mcp_app = MCPASGIApp(session_manager)
        starlette_app.mount("/mcp", mcp_app)

        import uvicorn

        uvicorn.run(starlette_app, host="127.0.0.1", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0
