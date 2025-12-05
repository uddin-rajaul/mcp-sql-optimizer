import sqlglot
from sqlglot import exp
from typing import Dict, Any, List, Optional
from utils.sql_utils import get_tables, get_columns

class QueryParser:
    def __init__(self):
        pass

    def parse(self, sql: str, dialect: str = "postgres") -> Dict[str, Any]:
        """
        Parses SQL and returns an AST and metadata breakdown.
        """
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
        except Exception as e:
            return {"error": f"Failed to parse SQL: {str(e)}"}

        metadata = {
            "tables": get_tables(parsed),
            "columns": get_columns(parsed),
            "query_type": parsed.key.upper() if parsed else "UNKNOWN",
            "parts": self._extract_parts(parsed)
        }
        
        return {
            "ast": parsed, # Note: AST object is not JSON serializable directly, handled in server or analyzer
            "metadata": metadata,
            "sql_normalized": parsed.sql(dialect=dialect)
        }

    def _extract_parts(self, expression: exp.Expression) -> Dict[str, str]:
        parts = {}
        if isinstance(expression, exp.Select):
            parts["SELECT"] = [e.sql() for e in expression.expressions]
            if expression.args.get("from"):
                parts["FROM"] = expression.args.get("from").sql()
            if expression.args.get("where"):
                parts["WHERE"] = expression.args.get("where").sql()
            if expression.args.get("group"):
                parts["GROUP BY"] = expression.args.get("group").sql()
            if expression.args.get("having"):
                parts["HAVING"] = expression.args.get("having").sql()
            if expression.args.get("order"):
                parts["ORDER BY"] = expression.args.get("order").sql()
            if expression.args.get("limit"):
                parts["LIMIT"] = expression.args.get("limit").sql()
        return parts
