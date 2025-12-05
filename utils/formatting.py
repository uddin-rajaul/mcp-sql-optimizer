import json
from typing import Any, Dict, List

def format_json_response(data: Any) -> str:
    """Formats data as a pretty-printed JSON string."""
    return json.dumps(data, indent=2, default=str)

def format_sql_code(sql: str) -> str:
    """Formats SQL code for display (could use sqlglot to pretty print)."""
    # We will use sqlglot in the parser/rewriter, but this is a fallback or wrapper
    return sql.strip()

def create_table_comparison(original: str, optimized: str) -> str:
    """Creates a simple text comparison of original vs optimized SQL."""
    return f"Original:\n{original}\n\nOptimized:\n{optimized}"
