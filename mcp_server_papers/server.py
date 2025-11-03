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

from utils import validate_arxiv_params, validate_arxiv_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Tools
async def send_query(params: str) -> str:
    """
    Send a validated query to arXiv API and return the response.
    """
    try:
        # Validate parameters first
        validated_params = validate_arxiv_params(params)
        logger.info(
            f"Parameters validated successfully: {list(validated_params.keys())}"
        )

        url = f"http://export.arxiv.org/api/query?{params}"
        logger.info(f"Sending validated query to arXiv: {url}")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    except ValueError as e:
        # Validation error - return helpful message
        logger.error(f"Parameter validation error: {e}")
        raise ValueError(f"Invalid query parameters: {e}")
    except httpx.RequestError as e:
        logger.error(f"Network error querying arXiv: {e}")
        raise ValueError(f"Failed to query arXiv API: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from arXiv: {e.response.status_code}")
        raise ValueError(f"arXiv API returned error: {e.response.status_code}")


async def download_paper(arxiv_id: str, save_path: str = None) -> str:
    """
    Download a paper PDF from arXiv.

    Args:
        arxiv_id: arXiv ID (e.g., "2510.26784" or "math.GT/0309136v1")
        save_path: Optional path to save the PDF (defaults to current directory)

    Returns:
        Success message with file path
    """
    try:
        # Validate arXiv ID
        validated_id = validate_arxiv_id(arxiv_id)

        # Construct PDF URL
        pdf_url = f"https://arxiv.org/pdf/{validated_id}.pdf"
        logger.info(f"Downloading paper from: {pdf_url}")

        # Set default save path
        if save_path is None:
            save_path = f"{validated_id.replace('/', '_')}.pdf"

        # Ensure save path has .pdf extension
        if not save_path.endswith(".pdf"):
            save_path += ".pdf"

        # Download the PDF
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()

            # Save to file
            file_path = Path(save_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(response.content)

            file_size = len(response.content) / (1024 * 1024)  # MB
            logger.info(
                f"Successfully downloaded {validated_id} ({file_size:.2f} MB) to {file_path}"
            )

            return f"Successfully downloaded paper '{validated_id}' ({file_size:.2f} MB) to: {file_path.absolute()}"

    except ValueError as e:
        # Validation error
        logger.error(f"Paper download validation error: {e}")
        raise ValueError(f"Invalid arXiv ID: {e}")
    except httpx.RequestError as e:
        logger.error(f"Network error downloading paper: {e}")
        raise ValueError(f"Failed to download paper: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading paper: {e.response.status_code}")
        if e.response.status_code == 404:
            raise ValueError(f"Paper '{arxiv_id}' not found on arXiv")
        else:
            raise ValueError(f"arXiv server error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error downloading paper: {e}")
        raise ValueError(f"Failed to save paper: {e}")


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
            ),
            types.Tool(
                name="download_paper",
                title="Download arXiv Paper PDF",
                description="Download a paper PDF from arXiv by its ID. Saves the PDF file locally.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "arxiv_id": {
                            "type": "string",
                            "description": "arXiv paper ID (e.g., '2510.26784', '2301.00001v1', or 'math.GT/0309136v1')",
                            "examples": [
                                "2510.26784",
                                "2301.00001v1",
                                "math.GT/0309136v1",
                            ],
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional path to save the PDF file. If not provided, saves to current directory with arxiv_id as filename.",
                            "examples": [
                                "papers/quantum_paper.pdf",
                                "/home/user/downloads/paper.pdf",
                            ],
                        },
                    },
                    "required": ["arxiv_id"],
                },
            ),
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

        elif name == "download_paper":
            if "arxiv_id" not in arguments:
                raise ValueError("Missing arxiv_id parameter")

            try:
                arxiv_id = arguments["arxiv_id"]
                save_path = arguments.get("save_path")  # Optional parameter

                result = await download_paper(arxiv_id, save_path)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error executing download_paper tool: {e}")
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
