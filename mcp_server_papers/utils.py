"""
Validation utilities for arXiv API parameters.
"""
import re
from urllib.parse import parse_qs
from typing import Dict, Any


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
        has_search_query = 'search_query' in parsed
        has_id_list = 'id_list' in parsed
        
        if not has_search_query and not has_id_list:
            raise ValueError("Either 'search_query' or 'id_list' parameter is required")
        
        # Validate each parameter
        if has_search_query:
            validated['search_query'] = validate_search_query(parsed['search_query'][0])
        
        if has_id_list:
            validated['id_list'] = validate_id_list(parsed['id_list'][0])
            
        if 'start' in parsed:
            validated['start'] = validate_start(parsed['start'][0])
            
        if 'max_results' in parsed:
            validated['max_results'] = validate_max_results(parsed['max_results'][0])
            
        if 'sortBy' in parsed:
            validated['sortBy'] = validate_sort_by(parsed['sortBy'][0])
            
        if 'sortOrder' in parsed:
            validated['sortOrder'] = validate_sort_order(parsed['sortOrder'][0])
            
        # Check for unknown parameters
        known_params = {'search_query', 'id_list', 'start', 'max_results', 'sortBy', 'sortOrder'}
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
    VALID_PREFIXES = {'ti', 'au', 'abs', 'co', 'jr', 'cat', 'rn', 'id', 'all'}
    VALID_OPERATORS = {'AND', 'OR', 'ANDNOT'}
    
    # Check for field prefixes
    field_pattern = r'(\w+):'
    fields = re.findall(field_pattern, query)
    
    for field in fields:
        if field not in VALID_PREFIXES:
            raise ValueError(f"Invalid field prefix '{field}'. Valid prefixes: {', '.join(sorted(VALID_PREFIXES))}")
    
    # Basic syntax validation for Boolean operators
    for operator in VALID_OPERATORS:
        if operator in query.upper():
            # Check for proper spacing around operators
            if f' {operator} ' not in query and f'+{operator}+' not in query:
                raise ValueError(f"Boolean operator '{operator}' should be surrounded by spaces or + signs")
    
    return query


def validate_id_list(id_list: str) -> str:
    """
    Validate arXiv ID format in id_list.
    
    4. ID List Validation
    """
    # arXiv ID patterns
    OLD_PATTERN = r'^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$'  # e.g., math.GT/0309136v1
    NEW_PATTERN = r'^\d{4}\.\d{4,5}(v\d+)?$'              # e.g., 2301.00001v1
    
    ids = [id.strip() for id in id_list.split(',')]
    
    for arxiv_id in ids:
        if not arxiv_id:
            raise ValueError("Empty arXiv ID in id_list")
            
        if not (re.match(OLD_PATTERN, arxiv_id) or re.match(NEW_PATTERN, arxiv_id)):
            raise ValueError(f"Invalid arXiv ID format: '{arxiv_id}'. Expected formats: 'YYMM.NNNN[vN]' or 'subject-class/YYMMnnn[vN]'")
    
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
    VALID_SORT_BY = {'relevance', 'lastUpdatedDate', 'submittedDate'}
    if sort_by not in VALID_SORT_BY:
        raise ValueError(f"Invalid 'sortBy' value '{sort_by}'. Valid options: {', '.join(sorted(VALID_SORT_BY))}")
    return sort_by


def validate_sort_order(sort_order: str) -> str:
    """
    Validate sortOrder parameter.
    
    3. Parameter Type Validation
    """
    VALID_SORT_ORDER = {'ascending', 'descending'}
    if sort_order not in VALID_SORT_ORDER:
        raise ValueError(f"Invalid 'sortOrder' value '{sort_order}'. Valid options: {', '.join(sorted(VALID_SORT_ORDER))}")
    return sort_order


def validate_submitted_date(date_range: str) -> str:
    """
    Validate submittedDate format.
    
    5. Date Range Validation
    """
    # Pattern: [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]
    pattern = r'^\[(\d{8}\d{4})\+TO\+(\d{8}\d{4})\]$'
    match = re.match(pattern, date_range)
    
    if not match:
        raise ValueError("Invalid 'submittedDate' format. Expected: [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]")
    
    start_date, end_date = match.groups()
    
    # Basic date validation (could be enhanced)
    if start_date >= end_date:
        raise ValueError("Start date must be before end date in 'submittedDate' range")
    
    return date_range
