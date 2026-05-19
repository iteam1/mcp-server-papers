# Improvement Plan: Make `mcp-server-papers` More AI-Efficient

This plan breaks the work into **small, independently shippable units**. Each unit:
- Has a single goal and a thin diff.
- Has explicit acceptance criteria you can verify before merging.
- Lists its dependencies so units can be parallelized where possible.

Units are ordered by **leverage / risk ratio** (biggest payoff + lowest risk first). Ship them in order unless noted.

---

## Unit 0 — Test harness setup

**Goal:** Make every later unit verifiable.

**Why first:** No `tests/` directory exists today. Without a harness, "testable units" is wishful thinking.

**Scope:**
- Add `tests/` package with `__init__.py`.
- Add `tests/conftest.py` with an `httpx` mock fixture (use `pytest-httpx` or `respx`).
- Add `tests/test_smoke.py` that imports `mcp_server_papers.server` and asserts it builds the `Server` object without network calls.
- Add `pytest` config to `pyproject.toml` (`[tool.pytest.ini_options]` with `testpaths = ["tests"]`).
- Add `pytest-httpx` (or `respx`) to dependencies.

**Acceptance:**
- `uv run pytest` runs and `test_smoke.py` passes.
- No network access during the test run (verified by mock).

**Dependencies:** none.

---

## Unit 1 — Fix `read_online` content-loss bug

**Goal:** Return the actual paper content, not just a "successfully fetched" message.

**Why:** `server.py:145` drops `html_content` entirely. The tool is currently useless to an AI. This is a one-line behavior fix with outsized impact.

**Scope:**
- Change `read_online_paper()` to return the fetched HTML (string).
- Keep the URL/length info as a short header or move to logging.

**Acceptance:**
- New test `tests/test_read_online.py`:
  - Mocks `https://arxiv.org/html/2510.04618` to return a fixed HTML string.
  - Calls `read_online_paper("2510.04618")`.
  - Asserts the returned string **contains** the mocked HTML body.
- Existing error paths (404, network error, invalid id) still raise `ValueError`.

**Dependencies:** Unit 0.

---

## Unit 2 — Parse HTML to clean text/markdown

**Goal:** Cut response size ~10× by stripping HTML before returning.

**Why:** A 400 KB raw HTML blob burns tokens; an AI only needs the readable text.

**Scope:**
- Add `trafilatura` (recommended) or `readability-lxml` + `markdownify` as a dependency.
- New helper `extract_paper_text(html: str) -> str` in `utils.py`.
- `read_online_paper()` returns the parsed text; original HTML stays in logs only.
- Keep a fallback: if parsing yields <500 chars, return raw HTML (don't lose content on parser failure).

**Acceptance:**
- `tests/test_extract.py` feeds a small fixture HTML and asserts:
  - Output preserves headings and paragraph text.
  - Output strips `<script>`, `<style>`, nav, footer.
  - Output length < 50% of input length on the fixture.
- `read_online` integration test asserts response is the parsed text, not raw HTML.

**Dependencies:** Unit 1.

---

## Unit 3 — Auto-extract figure URLs in `read_online`

**Goal:** Eliminate WORKFLOW Step 2 — server returns figures the AI can request directly.

**Scope:**
- New helper `extract_figures(html: str, base_url: str) -> list[dict]` returning `[{caption, url}]`.
- `read_online_paper()` returns a structured response (JSON-serialized string or dict via MCP `TextContent`):
  ```json
  {
    "arxiv_id": "...",
    "text": "...",
    "figures": [{"caption": "Figure 1: ...", "url": "https://arxiv.org/html/.../x1.png"}]
  }
  ```
- Resolve relative URLs against `https://arxiv.org/html/{arxiv_id}/`.

**Acceptance:**
- `tests/test_extract.py` with a fixture containing `<figure><img src="x1.png"><figcaption>Figure 1</figcaption></figure>`:
  - Asserts one figure returned with absolute URL and caption text.
- Relative, absolute, and protocol-relative URLs all resolve correctly.

**Dependencies:** Unit 2.

---

## Unit 4 — Structured output for `send_query`

**Goal:** Return parsed JSON instead of raw Atom XML.

**Why:** Today the AI receives Atom XML and has to parse it. Server-side parsing saves tokens and removes a class of AI errors.

**Scope:**
- Add `feedparser` (it natively understands Atom).
- New helper `parse_arxiv_atom(xml: str) -> list[dict]` returning:
  ```python
  [{"arxiv_id", "title", "authors", "abstract", "published", "updated",
    "pdf_url", "html_url", "categories"}]
  ```
- `send_query()` returns the parsed list (JSON-serialized).
- Preserve `total_results` from the OpenSearch fields so paging works.

**Acceptance:**
- `tests/test_parse_atom.py` with a fixture Atom response (saved from a real arXiv call):
  - Asserts ≥1 entry parsed, all required fields populated.
  - Asserts `pdf_url` matches `https://arxiv.org/pdf/{id}` pattern.
- Empty result set returns `[]`, not an error.

**Dependencies:** Unit 0.

---

## Unit 5 — Structured input for `send_query`

**Goal:** Accept `{title, author, abstract, category, max_results, ...}` and build the URL server-side.

**Why:** AIs frequently mis-URL-encode the current free-form `search_query=...` string. Structured input removes the failure mode.

**Scope:**
- Update `inputSchema` for the `send_query` tool to accept structured fields (keep the legacy `query` string as an optional fallback for one release).
- New helper `build_arxiv_query(...) -> str` in `utils.py` that returns a URL-encoded query string.
- Existing `validate_arxiv_params` continues to validate the constructed string.

**Acceptance:**
- `tests/test_build_query.py`:
  - `build_arxiv_query(title="quantum", author="einstein")` →
    `search_query=ti:quantum+AND+au:einstein`.
  - Phrases with spaces are quoted: `title="quantum criticality"` → `ti:%22quantum+criticality%22`.
  - `max_results` clamped to arXiv's max (2000).
- Backward-compat: passing `{"query": "search_query=..."}` still works.

**Dependencies:** Unit 4 (so output is also structured — paired upgrade).

---

## Unit 6 — Rate-limit handling

**Goal:** Stop returning opaque 429s.

**Why:** arXiv recommends ≥3 s between requests and 429s are common (we hit one in the smoke test). Today they surface as a generic ValueError.

**Scope:**
- Add a module-level async semaphore + last-request timestamp in `server.py` (or a tiny `RateLimiter` class in `utils.py`) that enforces 3 s spacing for arXiv calls.
- On 429, retry once after the `Retry-After` header (or 5 s default).
- After retry exhaustion, raise `ValueError("arXiv rate-limited; retry in N seconds")` with the wait time.

**Acceptance:**
- `tests/test_rate_limit.py` using `pytest-httpx`:
  - Mock returns 429 with `Retry-After: 2`, then 200. Tool returns the 200 body.
  - Two parallel calls observe ≥3 s spacing (use a fake clock or `freezegun`).
- Existing tests still pass (no real sleeps in unit tests — inject the clock).

**Dependencies:** Unit 4 (so retry logic lives in one place).

---

## Unit 7 — Return images inline from `get_image`

**Goal:** One round-trip instead of two (download → read file).

**Scope:**
- Change `fetch_tool()` in `server.py` to return `types.ImageContent(type="image", data=<base64>, mimeType=...)` instead of a file path.
- Keep disk caching as an internal optimization (optional), but the response is inline.
- Update the tool description.

**Acceptance:**
- `tests/test_get_image.py`:
  - Mock image bytes; assert returned content block is `ImageContent` with matching base64 + correct `mimeType`.
- Unsupported content-type falls back to `image/png` (current behavior preserved).

**Dependencies:** Unit 0.

---

## Unit 8 — PDF text extraction

**Goal:** Make `download_paper` output usable by AI without an extra tool.

**Scope (pick one — recommend A):**
- **A.** New tool `read_pdf(path_or_arxiv_id)` that extracts text via `pymupdf`.
- **B.** Add `extract_text: bool` param to `download_paper`; when true, return text instead of (or alongside) the file path.

**Acceptance:**
- `tests/test_pdf.py` with a tiny fixture PDF (3–5 pages, checked into `tests/fixtures/`):
  - Returns text containing known marker strings.
  - Handles missing file with `ValueError`.

**Dependencies:** Unit 0.

---

## Unit 9 — MCP tool annotations + naming polish

**Goal:** Help MCP clients (including AIs) choose tools correctly.

**Scope:**
- Add `annotations` to each `types.Tool`:
  - `send_query`: `readOnlyHint=true, idempotentHint=true`.
  - `read_online`: `readOnlyHint=true`.
  - `download_paper`, `get_image`: `readOnlyHint=false` (writes files — until Unit 7 lands for `get_image`).
- Rename `send_query` → `search_arxiv` (keep the old name as an alias for one release).
- Tighten descriptions to mention return shape (after Units 3–4).

**Acceptance:**
- `tests/test_list_tools.py` asserts each tool has the expected annotation flags.
- Both `send_query` and `search_arxiv` names resolve to the same handler.

**Dependencies:** Units 3, 4, 7 (so descriptions reflect new shapes).

---

## Unit 10 — Drop `verify=False` on httpx

**Goal:** Remove an unnecessary TLS-disable.

**Scope:**
- Remove `verify=False` from the three `httpx.AsyncClient(...)` calls in `server.py`.
- If something legitimately broke TLS originally, replace with `httpx.AsyncClient(trust_env=True)` and document why in the commit.

**Acceptance:**
- Existing tests still pass (mocks don't care about TLS).
- Manual smoke: `send_query` and `read_online` against real arXiv succeed.

**Dependencies:** none — can be done anytime.

---

## Suggested shipping order

1. **Unit 0** (test harness) — enables everything else.
2. **Unit 1** (fix `read_online` bug) — single biggest user-visible win.
3. **Unit 2** (HTML → text) — token savings.
4. **Unit 4** (structured search output) — parallelizable with Unit 2.
5. **Unit 3** (figures in `read_online`).
6. **Unit 7** (inline images).
7. **Unit 5** (structured search input).
8. **Unit 6** (rate limiting).
9. **Unit 8** (PDF text).
10. **Unit 9** (annotations + rename).
11. **Unit 10** (TLS cleanup) — any time.

Each unit should be one PR with its tests. If a unit grows past ~150 LOC of changes, split it further before starting.
