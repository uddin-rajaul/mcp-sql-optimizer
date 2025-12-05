import sqlglot
from sqlglot import exp

def get_tables(expression: exp.Expression) -> list[str]:
    """Extracts all table names from a sqlglot expression."""
    return [t.name for t in expression.find_all(exp.Table)]

def get_columns(expression: exp.Expression) -> list[str]:
    """Extracts all column names from a sqlglot expression."""
    return [c.name for c in expression.find_all(exp.Column)]

def is_select_star(expression: exp.Expression) -> bool:
    """Checks if the query is a SELECT *."""
    if isinstance(expression, exp.Select):
        for projection in expression.expressions:
            if isinstance(projection, exp.Star):
                return True
    return False
