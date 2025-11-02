# mcp-server-papers

*Thank you to arXiv for use of its open access interoperability.*

## ✅ What You CAN Do

- Retrieve and store descriptive metadata (titles, abstracts, authors, identifiers, classifications)

- Search and discover papers through API

- Retrieve paper content for research purposes

## 📋 Rate Limits

- Maximum 1 request every 3 seconds for legacy APIs (including the main ArXiv API)

- Single connection at a time

## ✨ Features

### 🔍 Search & Discovery
- **Advanced Search**: Query arXiv papers with field-specific searches (`ti:`, `au:`, `abs:`, etc.)
- **Boolean Logic**: Support for `AND`, `OR`, `ANDNOT` operators
- **Flexible Sorting**: Sort by relevance, submission date, or last updated
- **ID-based Lookup**: Direct paper retrieval by arXiv ID

### 📥 Paper Download
- **PDF Download**: Download papers directly by arXiv ID
- **Flexible Paths**: Save to custom locations or use auto-generated filenames
- **Progress Tracking**: File size reporting and download status
- **Error Handling**: Robust validation and error reporting

### 🛡️ Validation Categories:

1. Query Parameter Validation
- Required parameters: Ensure either `search_query` or `id_list` is provided
- Parameter combinations: Validate logic between `search_query` and `id_list`
- Unknown parameters: Reject invalid parameter names
2. Field Prefix Validation
- Valid prefixes: `ti`, `au`, `abs`, `co`, `jr`, `cat`, `rn`, `id`, `all`
- Boolean operators: `AND`, `OR`, `ANDNOT`
- Syntax checking: Proper field:value format
3. Parameter Type Validation
- `start`: Non-negative integer
- `max_results`: Positive integer (1-2000 limit)
- `sortBy`: Must be "relevance", "lastUpdatedDate", or "submittedDate"
- `sortOrder`: Must be "ascending" or "descending"
4. ID List Validation
- Old format: `math.GT/0309136v1` (subject-class/YYMMnnn)
- New format: `2301.00001v1` (YYMM.NNNN)
- Version numbers: Optional vN suffix
- Comma separation: Multiple IDs properly formatted
5. Date Range Validation (from your API spec)
- `submittedDate` format: [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]
- Date logic: Start date before end date
- GMT time format: TTTT in 24-hour format
6. URL Encoding Validation
- Special characters: Proper encoding of spaces (+), quotes (%22), parentheses (%28, %29) in `search_query`
- Reserved characters: Ensure proper escaping in `search_query`

## 🚀 How to Use

Integrate with AI Agents
```json
{
  "mcpServers": {
    "papers": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/locch/Works/mcp-server-papers",
        "run",
        "mcp_server_papers"
      ]
    }
  }
}
```

Or:

```json
{
  "mcpServers": {
    "papers": {
      "serverUrl": "http://localhost:8000/mcp"
    }
  }
}
```

## 📚 Reference

- [arXiv API](https://info.arxiv.org/help/api/index.html)

- [arXiv API Terms of Use](https://info.arxiv.org/help/api/tou.html)

- [arXiv API Basics](https://info.arxiv.org/help/api/basics.html)

- [arXiv API User Manual](https://info.arxiv.org/help/api/user-manual.html)