# API

## Quick Start

Example of using the API in Python:

```python
import urllib, urllib.request
url = 'http://export.arxiv.org/api/query?search_query=all:electron&start=0&max_results=1'
data = urllib.request.urlopen(url)
print(data.read().decode('utf-8'))
```

## Query Interface
A typical API call:

```
Request from url: http://export.arxiv.org/api/query  (1)
 with parameters: search_query=all:electron
                .
                .
                .
API server processes the request and sends the response
                .
                .
                .
Response received by client.  (2)
```

Base url: `http://export.arxiv.org/api/{method_name}?{parameters}`

The API query interface has method_name=query. The table below outlines the parameters that can be passed to the query interface. Parameters are separated with the & sign in the constructed URLs.

| Parameter | Type | Default | Required |
|-----------|------|---------|----------|
| search_query | string | None | No |
| id_list | comma-delimited string | None | No |
| start | int | 0 | No |
| max_results | int | 10 | No |

## Query Parameters

### `search_query` and `id_list` Logic

- If only `search_query` is given (id_list is blank or not given), then the API will return results for each article that matches the search query.
- If only `id_list` is given (search_query is blank or not given), then the API will return results for each article in id_list.
- If both `search_query` and `id_list` are given, then the API will return each article in id_list that matches search_query. This allows the API to act as a results filter.


### `sortBy` and `sortOrder` Parameters

- `sortBy` can be "relevance" (Apache Lucene's default RELEVANCE ordering), "lastUpdatedDate", or "submittedDate"
- `sortOrder` can be either "ascending" or "descending"

Example:

```
http://export.arxiv.org/api/query?search_query=ti:"electron thermal conductivity"&sortBy=lastUpdatedDate&sortOrder=ascending
```


## Details of Query Construction

In the arXiv search engine, each article is divided up into a number of fields that can individually be searched. For example, the titles of an article can be searched, as well as the author list, abstracts, comments and journal reference. To search one of these fields, we simply prepend the field prefix followed by a colon to our search term. For example, suppose we wanted to find all articles by the author Adrian Del Maestro. We could construct the following query: `http://export.arxiv.org/api/query?search_query=au:del_maestro`. This returns nine results. The following table lists the field prefixes for all the fields that can be searched.

| Prefix | Explanation |
|--------|-------------|
| ti | Title |
| au | Author |
| abs | Abstract |
| co | Comment |
| jr | Journal Reference |
| cat | Subject Category |
| rn | Report Number |
| id | Id (use id_list instead) |
| all | All of the above |

The API provides one date filter, `submittedDate`, that allows you to select data within a given date range of when the data was submitted to arXiv. The expected format is `[YYYYMMDDTTTT+TO+YYYYMMDDTTTT]` where TTTT is provided in 24-hour time to the minute, in GMT. You can construct the following query using `submittedDate`:

Example:

```
https://export.arxiv.org/api/query?search_query=au:del_maestro+AND+submittedDate:[202301010600+TO+202401010600]
```

The API allows advanced query construction by combining these search fields with Boolean operators. For example, suppose we want to find all articles by the author `Adrian DelMaestro` that also contain the word `checkerboard` in the title. We could construct the following query, using the `AND` operator:

```
http://export.arxiv.org/api/query?search_query=au:del_maestro+AND+ti:checkerboard
```

As expected, this query returns one of the nine previous results with "checkerboard" in the title. Note that + signs are included in the URLs to the API. In a URL, a + sign encodes a space, which is useful since spaces are not allowed in URLs. It is always a good idea to escape the characters in your URLs, which is a common feature in most programming libraries that deal with URLs. Note that the `<title>` of the returned feed has spaces in the query constructed. It is a good idea to look at `<title>` to see if you have escaped your URL correctly.

The following table lists the three possible Boolean operators.

| Operator | Explanation |
|----------|-------------|
| AND | All of the conditions must be true |
| OR | At least one of the conditions must be true |
| ANDNOT | All of the conditions must be true, except for the ones that are negated |


So far, we have only used single words as the field terms to search for. You can include entire phrases by enclosing the phrase in double quotes, escaped by %22. For example, if you want all articles by the author Adrian DelMaestro with titles that contain "quantum criticality", you can construct the following query:

```
http://export.arxiv.org/api/query?search_query=au:del_maestro+AND+ti:%22quantum+criticality%22
```

This query returns one result, and notice that the feed `<title>` contains double quotes as expected. The table below lists the grouping operators used in the API.
| Symbol | Encoding | Explanation |
|--------|----------|-------------|
| ( ) | %28 %29 | Used to group Boolean expressions for Boolean operator precedence |
| double quotes | %22 %22 | Used to group multiple words into phrases to search a particular field |
| space | + | Used to extend a search_query to include multiple fields |

When using the API, if you want to retrieve the latest version of an article, you can simply enter the arXiv ID in the `id_list` parameter. If you want to retrieve information about a specific version, you can do this by appending `vn` to the ID, where `n` is the version number you are interested in.

For example, to retrieve the latest version of `cond-mat/0207270`, you can use the query:

```
http://export.arxiv.org/api/query?id_list=cond-mat/0207270
```

To retrieve the very first version of this article, you can use the query:

```
http://export.arxiv.org/api/query?id_list=cond-mat/0207270v1
```

## Details of Atom Results Returned

The following table lists each element of the returned Atom results. For a more detailed explanation, see the Outline of an Atom Feed.

| Element | Explanation |
|---------|-------------|
| **`<feed>` elements** | **Explanation** |
| `<title>` | The title of the feed containing a canonicalized query string. |
| `<id>` | A unique ID assigned to this query |
| `<updated>` | The last time search results for this query were updated. Set to midnight of the current day |
| `<link>` | A URL that will retrieve this feed via a GET request |
| `<opensearch:totalResults>` | The total number of search results for this query |
| `<opensearch:startIndex>` | The 0-based index of the first returned result in the total results list |
| `<opensearch:itemsPerPage>` | The number of results returned |
| **`<entry>` elements** | **Explanation** |
| `<title>` | The title of the article |
| `<id>` | A URL in the format http://arxiv.org/abs/id |
| `<published>` | The date that version 1 of the article was submitted |
| `<updated>` | The date that the retrieved version of the article was submitted. Same as `<published>` if the retrieved version is version 1 |
| `<summary>` | The article abstract |
| `<author>` | One for each author. Has child element `<name>` containing the author name |
| `<link>` | Can be up to 3 given URLs associated with this article |
| `<category>` | The arXiv, ACM, or MSC category for an article if present |
| `<arxiv:primary_category>` | The primary arXiv category |
| `<arxiv:comment>` | The author's comment if present |
| `<arxiv:affiliation>` | The author's affiliation included as a subelement of `<author>` if present |
| `<arxiv:journal_ref>` | A journal reference if present |
| `<arxiv:doi>` | A URL for the resolved DOI to an external resource if present |