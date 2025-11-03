import anyio
import click
import hashlib
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


async def read_online_paper(arxiv_id: str) -> str:
    """
    Fetch and read the HTML version of an arXiv paper online.

    Args:
        arxiv_id: arXiv ID (e.g., "2510.04618" or "math.GT/0309136v1")

    Returns:
        Formatted paper content including text and structure
    """
    try:
        # Validate arXiv ID
        validated_id = validate_arxiv_id(arxiv_id)

        # Construct HTML URL
        html_url = f"https://arxiv.org/html/{validated_id}"
        logger.info(f"Fetching paper from: {html_url}")

        # Fetch the HTML content
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            response = await client.get(html_url)
            response.raise_for_status()

            # Basic content processing
            html_content = response.text
            content_length = len(html_content)
            logger.info(f"Successfully fetched paper '{validated_id}' ({content_length} characters)")

            # Return formatted response
            return f"Successfully fetched arXiv paper '{validated_id}' from HTML version.\n\nContent length: {content_length:,} characters\n\nHTML URL: {html_url}\n\nNote: This is the raw HTML content. For better readability, consider processing with additional HTML parsing tools."

    except ValueError as e:
        # Validation error
        logger.error(f"Paper fetch validation error: {e}")
        raise ValueError(f"Invalid arXiv ID: {e}")
    except httpx.RequestError as e:
        logger.error(f"Network error fetching paper: {e}")
        raise ValueError(f"Failed to fetch paper: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching paper: {e.response.status_code}")
        if e.response.status_code == 404:
            raise ValueError(f"Paper '{arxiv_id}' HTML version not found on arXiv")
        else:
            raise ValueError(f"arXiv server error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error fetching paper: {e}")
        raise ValueError(f"Failed to fetch paper: {e}")


async def get_image(image_url: str) -> str:
    """
    Download an image from URL and return the file path where it's saved.

    Args:
        image_url: Direct URL to an image file

    Returns:
        File path where the image is downloaded for AI agent analysis
    """
    try:
        logger.info(f"Downloading image from: {image_url}")

        # Download the image
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            # Get image content
            image_bytes = response.content
            file_size = len(image_bytes)
            
            # Determine image format from URL or content type
            content_type = response.headers.get('content-type', '').lower()
            if 'png' in content_type or image_url.lower().endswith('.png'):
                file_extension = 'png'
            elif 'jpeg' in content_type or 'jpg' in content_type or image_url.lower().endswith(('.jpg', '.jpeg')):
                file_extension = 'jpg'
            elif 'gif' in content_type or image_url.lower().endswith('.gif'):
                file_extension = 'gif'
            elif 'webp' in content_type or image_url.lower().endswith('.webp'):
                file_extension = 'webp'
            else:
                # Default to png if format unclear
                file_extension = 'png'

            # Create downloads directory if it doesn't exist
            downloads_dir = Path("downloaded")
            downloads_dir.mkdir(exist_ok=True)
            
            # Generate filename from URL hash to avoid conflicts
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            filename = f"image_{url_hash}.{file_extension}"
            file_path = downloads_dir / filename

            # Save image to file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            logger.info(f"Successfully downloaded image ({file_size:,} bytes) to {file_path}")

            # Return just the file path
            return str(file_path.absolute())

    except httpx.RequestError as e:
        logger.error(f"Network error downloading image: {e}")
        raise ValueError(f"Failed to download image: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading image: {e.response.status_code}")
        raise ValueError(f"Server error {e.response.status_code} for image: {image_url}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing image: {e}")
        raise ValueError(f"Failed to analyze image: {e}")


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


def read_workflow_guide() -> str:
    """Read the AI agent workflow guide from the docs directory."""
    try:
        # Get the project root directory
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        workflow_doc_path = project_root / "docs" / "WORKFLOW.md"

        if not workflow_doc_path.exists():
            raise FileNotFoundError(f"Workflow documentation not found at {workflow_doc_path}")

        return workflow_doc_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read workflow guide: {e}")
        raise ValueError(f"Could not load workflow documentation: {e}")


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
                                "search_query=au:del_maestro+AND+ti:checkerboard",
                                "search_query=ti:%22quantum+criticality%22&sortBy=lastUpdatedDate&sortOrder=descending",
                                "search_query=cat:cond-mat.mes-hall+AND+abs:graphene&max_results=20",
                                "id_list=cond-mat/0207270v1,2301.00001",
                                "search_query=all:electron&start=10&max_results=50",
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
            types.Tool(
                name="read_online",
                title="Read arXiv Paper Online",
                description="Fetch and read the HTML version of an arXiv paper online. Returns the paper content for analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "arxiv_id": {
                            "type": "string",
                            "description": "arXiv paper ID (e.g., '2510.04618', '2301.00001v1', or 'math.GT/0309136v1')",
                            "examples": [
                                "2510.04618",
                                "2301.00001v1",
                                "math.GT/0309136v1",
                            ],
                        },
                    },
                    "required": ["arxiv_id"],
                },
            ),
            types.Tool(
                name="get_image",
                title="Get Image from URL",
                description="Download an image from URL and return the local file path.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_url": {
                            "type": "string",
                            "description": "Direct URL to an image file (PNG, JPEG, GIF, WebP)",
                            "examples": [
                                "https://arxiv.org/html/2510.04618/x1.png",
                                "https://example.com/chart.png",
                                "https://research-paper.com/figures/figure1.jpg",
                            ],
                        },
                    },
                    "required": ["image_url"],
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

        elif name == "read_online":
            if "arxiv_id" not in arguments:
                raise ValueError("Missing arxiv_id parameter")

            try:
                arxiv_id = arguments["arxiv_id"]
                result = await read_online_paper(arxiv_id)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error executing read_online tool: {e}")
                return [types.TextContent(type="text", text=f"Error: {e}")]

        elif name == "get_image":
            if "image_url" not in arguments:
                raise ValueError("Missing image_url parameter")

            try:
                image_url = arguments["image_url"]
                result = await get_image(image_url)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error executing get_image tool: {e}")
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
            ),
            types.Resource(
                uri="docs://workflow",
                name="AI Agent Workflow",
                description="Step-by-step workflow guide for AI agents to read papers online using read_online and get_image tools",
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
        elif uri_str == "docs://workflow":
            try:
                content = read_workflow_guide()
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
