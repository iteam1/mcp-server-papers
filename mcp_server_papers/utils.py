"""
Validation utilities for arXiv API parameters and HTML extraction.
"""

import re
from urllib.parse import parse_qs, urljoin, quote
from typing import Dict, Any, List, Optional
import trafilatura
import feedparser
from html.parser import HTMLParser


def validate_arxiv_id(arxiv_id: str) -> str:
    """
    Validate a single arXiv ID format.

    Args:
        arxiv_id: arXiv ID to validate

    Returns:
        Validated arXiv ID

    Raises:
        ValueError: If ID format is invalid
    """
    # Remove any whitespace
    arxiv_id = arxiv_id.strip()

    # arXiv ID patterns
    OLD_PATTERN = r"^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$"  # e.g., math.GT/0309136v1
    NEW_PATTERN = r"^\d{4}\.\d{4,5}(v\d+)?$"  # e.g., 2301.00001v1

    if not (re.match(OLD_PATTERN, arxiv_id) or re.match(NEW_PATTERN, arxiv_id)):
        raise ValueError(
            f"Invalid arXiv ID format: '{arxiv_id}'. Expected formats: 'YYMM.NNNN[vN]' or 'subject-class/YYMMnnn[vN]'"
        )

    return arxiv_id


def validate_arxiv_params(params: str) -> Dict[str, Any]:
    """
    Validate arXiv API parameters against the specification.
    Returns parsed and validated parameters.

    Args:
        params: Query string parameters (e.g., "search_query=ti:quantum&max_results=5")

    Returns:
        Dict of validated parameters

    Raises:
        ValueError: If parameters are invalid
    """
    try:
        # Parse query string
        parsed = parse_qs(params)
        validated = {}

        # 1. Query Parameter Validation
        has_search_query = "search_query" in parsed
        has_id_list = "id_list" in parsed

        if not has_search_query and not has_id_list:
            raise ValueError("Either 'search_query' or 'id_list' parameter is required")

        # Validate each parameter
        if has_search_query:
            validated["search_query"] = validate_search_query(parsed["search_query"][0])

        if has_id_list:
            validated["id_list"] = validate_id_list(parsed["id_list"][0])

        if "start" in parsed:
            validated["start"] = validate_start(parsed["start"][0])

        if "max_results" in parsed:
            validated["max_results"] = validate_max_results(parsed["max_results"][0])

        if "sortBy" in parsed:
            validated["sortBy"] = validate_sort_by(parsed["sortBy"][0])

        if "sortOrder" in parsed:
            validated["sortOrder"] = validate_sort_order(parsed["sortOrder"][0])

        # Check for unknown parameters
        known_params = {
            "search_query",
            "id_list",
            "start",
            "max_results",
            "sortBy",
            "sortOrder",
        }
        unknown_params = set(parsed.keys()) - known_params
        if unknown_params:
            raise ValueError(f"Unknown parameters: {', '.join(unknown_params)}")

        return validated

    except Exception as e:
        raise ValueError(f"Parameter validation failed: {e}")


def validate_search_query(query: str) -> str:
    """
    Validate search_query field prefixes and syntax.

    2. Field Prefix Validation
    """
    # Valid prefixes from API spec
    VALID_PREFIXES = {"ti", "au", "abs", "co", "jr", "cat", "rn", "id", "all"}
    VALID_OPERATORS = {"AND", "OR", "ANDNOT"}

    # Check for field prefixes
    field_pattern = r"(\w+):"
    fields = re.findall(field_pattern, query)

    for field in fields:
        if field not in VALID_PREFIXES:
            raise ValueError(
                f"Invalid field prefix '{field}'. Valid prefixes: {', '.join(sorted(VALID_PREFIXES))}"
            )

    # Basic syntax validation for Boolean operators
    for operator in VALID_OPERATORS:
        if operator in query.upper():
            # Check for proper spacing around operators
            if f" {operator} " not in query and f"+{operator}+" not in query:
                raise ValueError(
                    f"Boolean operator '{operator}' should be surrounded by spaces or + signs"
                )

    return query


def validate_id_list(id_list: str) -> str:
    """
    Validate arXiv ID format in id_list.

    4. ID List Validation
    """
    # arXiv ID patterns
    OLD_PATTERN = r"^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$"  # e.g., math.GT/0309136v1
    NEW_PATTERN = r"^\d{4}\.\d{4,5}(v\d+)?$"  # e.g., 2301.00001v1

    ids = [id.strip() for id in id_list.split(",")]

    for arxiv_id in ids:
        if not arxiv_id:
            raise ValueError("Empty arXiv ID in id_list")

        if not (re.match(OLD_PATTERN, arxiv_id) or re.match(NEW_PATTERN, arxiv_id)):
            raise ValueError(
                f"Invalid arXiv ID format: '{arxiv_id}'. Expected formats: 'YYMM.NNNN[vN]' or 'subject-class/YYMMnnn[vN]'"
            )

    return id_list


def validate_start(start_str: str) -> int:
    """
    Validate start parameter.

    3. Parameter Type Validation
    """
    try:
        start = int(start_str)
        if start < 0:
            raise ValueError("'start' must be non-negative")
        return start
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("'start' must be a valid integer")
        raise


def validate_max_results(max_results_str: str) -> int:
    """
    Validate max_results parameter.

    3. Parameter Type Validation
    """
    try:
        max_results = int(max_results_str)
        if max_results <= 0:
            raise ValueError("'max_results' must be positive")
        if max_results > 2000:  # arXiv API limit
            raise ValueError("'max_results' cannot exceed 2000 (arXiv API limit)")
        return max_results
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("'max_results' must be a valid integer")
        raise


def validate_sort_by(sort_by: str) -> str:
    """
    Validate sortBy parameter.

    3. Parameter Type Validation
    """
    VALID_SORT_BY = {"relevance", "lastUpdatedDate", "submittedDate"}
    if sort_by not in VALID_SORT_BY:
        raise ValueError(
            f"Invalid 'sortBy' value '{sort_by}'. Valid options: {', '.join(sorted(VALID_SORT_BY))}"
        )
    return sort_by


def validate_sort_order(sort_order: str) -> str:
    """
    Validate sortOrder parameter.

    3. Parameter Type Validation
    """
    VALID_SORT_ORDER = {"ascending", "descending"}
    if sort_order not in VALID_SORT_ORDER:
        raise ValueError(
            f"Invalid 'sortOrder' value '{sort_order}'. Valid options: {', '.join(sorted(VALID_SORT_ORDER))}"
        )
    return sort_order


def validate_submitted_date(date_range: str) -> str:
    """
    Validate submittedDate format.

    5. Date Range Validation
    """
    # Pattern: [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]
    pattern = r"^\[(\d{8}\d{4})\+TO\+(\d{8}\d{4})\]$"
    match = re.match(pattern, date_range)

    if not match:
        raise ValueError(
            "Invalid 'submittedDate' format. Expected: [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]"
        )

    start_date, end_date = match.groups()

    # Basic date validation (could be enhanced)
    if start_date >= end_date:
        raise ValueError("Start date must be before end date in 'submittedDate' range")

    return date_range


def extract_paper_text(html: str) -> str:
    """
    Extract readable text from HTML, stripping markup and noise.

    Uses trafilatura for robust content extraction. Falls back to raw HTML
    if parsing fails (don't lose content on parser failure).

    Args:
        html: Raw HTML content from arXiv

    Returns:
        Extracted text content, or original HTML if extraction fails
    """
    if not html or not html.strip():
        return ""

    try:
        extracted = trafilatura.extract(html, include_comments=False, favor_precision=True)
        # Return extracted text if any was found, otherwise fall back to raw HTML
        if extracted and len(extracted.strip()) > 10:
            return extracted
        # If extraction failed or produced minimal content, return original to avoid losing data
        return html
    except Exception:
        # On parse failure, fall back to raw HTML
        return html


def extract_figures(html: str, arxiv_id: str) -> List[Dict[str, str]]:
    """
    Extract figure URLs and captions from HTML.

    Finds <img> tags (with or without <figure> wrappers) and builds absolute URLs.
    Captions come from <figcaption> or alt text.

    Args:
        html: Raw HTML content from arXiv
        arxiv_id: Paper's arXiv ID for building absolute URLs

    Returns:
        List of {url, caption} dicts
    """
    if not html or not html.strip():
        return []

    figures = []
    base_url = f"https://arxiv.org/html/{arxiv_id}/"

    class FigureParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_figure = False
            self.current_img = None
            self.current_caption = None

        def handle_starttag(self, tag, attrs):
            nonlocal figures
            attrs_dict = dict(attrs)

            if tag == "figure":
                self.in_figure = True
            elif tag == "img":
                src = attrs_dict.get("src")
                alt = attrs_dict.get("alt", "")
                if src:
                    self.current_img = {"src": src, "alt": alt}
            elif tag == "figcaption":
                self.current_caption = ""

        def handle_data(self, data):
            if self.current_caption is not None:
                self.current_caption += data.strip()

        def handle_endtag(self, tag):
            nonlocal figures
            if tag == "figcaption" and self.current_caption:
                if self.current_img:
                    url = urljoin(base_url, self.current_img["src"])
                    caption = self.current_caption
                    figures.append({"url": url, "caption": caption})
                    self.current_img = None
                self.current_caption = None
            elif tag == "figure":
                # If we have an image but no caption, use alt text
                if self.current_img and self.current_caption is None:
                    url = urljoin(base_url, self.current_img["src"])
                    caption = self.current_img.get("alt", "Figure")
                    figures.append({"url": url, "caption": caption})
                self.in_figure = False
                self.current_img = None

    try:
        parser = FigureParser()
        parser.feed(html)
    except Exception:
        # On parse error, return what we found so far
        pass

    return figures


def build_arxiv_query(
    title: Optional[str] = None,
    author: Optional[str] = None,
    abstract: Optional[str] = None,
    category: Optional[str] = None,
    all_fields: Optional[str] = None,
    max_results: int = 10,
    start: int = 0,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
) -> str:
    """
    Build an arXiv API query string from structured parameters.

    Combines fields with AND, quotes phrases, URL-encodes result.

    Args:
        title: Search in title
        author: Search in author
        abstract: Search in abstract
        category: arXiv category (e.g., "quant-ph")
        all_fields: Search in all fields
        max_results: Max results (clamped to 2000)
        start: Result offset
        sort_by: 'relevance', 'lastUpdatedDate', or 'submittedDate'
        sort_order: 'ascending' or 'descending'

    Returns:
        URL-encoded query string (e.g., "search_query=ti:quantum+AND+au:einstein&max_results=10")
    """
    # Clamp max_results
    max_results = min(max_results, 2000)

    # Build search_query
    terms = []

    if title:
        # Quote if multi-word
        if " " in title.strip():
            terms.append(f'ti:"{title.strip()}"')
        else:
            terms.append(f"ti:{title.strip()}")

    if author:
        if " " in author.strip():
            terms.append(f'au:"{author.strip()}"')
        else:
            terms.append(f"au:{author.strip()}")

    if abstract:
        if " " in abstract.strip():
            terms.append(f'abs:"{abstract.strip()}"')
        else:
            terms.append(f"abs:{abstract.strip()}")

    if category:
        terms.append(f"cat:{category.strip()}")

    if all_fields:
        if " " in all_fields.strip():
            terms.append(f'all:"{all_fields.strip()}"')
        else:
            terms.append(f"all:{all_fields.strip()}")

    # Build query
    if not terms:
        # No search terms provided
        return ""

    search_query = " AND ".join(terms)

    # URL-encode the query
    params = f"search_query={quote(search_query)}"
    params += f"&max_results={max_results}"

    if start > 0:
        params += f"&start={start}"

    if sort_by:
        params += f"&sortBy={sort_by}"

    if sort_order:
        params += f"&sortOrder={sort_order}"

    return params


def parse_arxiv_atom(atom_xml: str) -> List[Dict[str, Any]]:
    """
    Parse arXiv Atom feed and return structured paper list.

    Extracts arxiv_id, title, authors, abstract, URLs from Atom response.

    Args:
        atom_xml: Atom XML from arXiv API response

    Returns:
        List of {arxiv_id, title, authors, abstract, published, pdf_url, html_url, categories}
    """
    if not atom_xml or not atom_xml.strip():
        return []

    try:
        feed = feedparser.parse(atom_xml)
    except Exception:
        return []

    papers = []
    for entry in feed.get("entries", []):
        try:
            # Extract arxiv ID from entry ID (e.g., http://arxiv.org/abs/2510.26784v1)
            entry_id = entry.get("id", "")
            arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else ""

            if not arxiv_id:
                continue

            # Extract authors
            authors = []
            for author_entry in entry.get("authors", []):
                if "name" in author_entry:
                    authors.append(author_entry["name"])

            # Extract PDF URL
            pdf_url = ""
            for link in entry.get("links", []):
                if link.get("rel") == "related" and "pdf" in link.get("type", ""):
                    pdf_url = link.get("href", "")
                    break
            # Fallback: construct from arxiv_id
            if not pdf_url:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            # Extract HTML URL
            html_url = ""
            for link in entry.get("links", []):
                if link.get("rel") == "alternate":
                    html_url = link.get("href", "")
                    break

            # Extract categories
            categories = []
            for tag in entry.get("tags", []):
                if "term" in tag:
                    categories.append(tag["term"])

            paper = {
                "arxiv_id": arxiv_id,
                "title": entry.get("title", "").strip(),
                "authors": authors,
                "abstract": entry.get("summary", "").strip(),
                "published": entry.get("published", ""),
                "pdf_url": pdf_url,
                "html_url": html_url,
                "categories": categories,
            }
            papers.append(paper)
        except Exception:
            # Skip entries with parse errors
            continue

    return papers
