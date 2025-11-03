# Workflow: Reading ArXiv Papers Online

## Step 1: Get Text Content
Use `read_online` tool to fetch the paper's HTML content:
```json
{
  "name": "read_online",
  "arguments": {"arxiv_id": "2510.04618"}
}
```

## Step 2: Extract Image URLs
From the HTML content, extract all image URLs (look for `<img src="...">` tags).
Common arXiv image patterns:
- `x1.png`, `x2.png`, `x3.png` (Figure 1, 2, 3...)  
- `figures/diagram.png`
- Relative URLs need base: `https://arxiv.org/html/{arxiv_id}/`

## Step 3: Download Images Sequentially  
Use `get_image` tool for each image found:
```json
{
  "name": "get_image", 
  "arguments": {"image_url": "https://arxiv.org/html/2510.04618/x1.png"}
}
```

## Step 4: Analyze Images
Read each downloaded image file to understand visual content (charts, diagrams, etc.).

## Step 5: Provide Comprehensive Response
Return analysis in this format:

```
# Paper Analysis: [Paper Title]

## Text Summary
[Key points from HTML content]

## Figures Analysis
**Figure 1** (x1.png): [Visual description]
**Figure 2** (x2.png): [Visual description]
...

## Key Findings
[Combined insights from text + figures]

## Answer to User Query
[Specific response to user's question]
```

## Tips for AI Agents
- Always process images **after** getting text content
- Handle missing/broken image URLs gracefully
- Combine visual and textual information for complete understanding
- Focus on answering the user's specific question using all available information