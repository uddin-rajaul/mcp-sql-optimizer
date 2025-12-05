import re

def detect_dialect(sql: str) -> str:
    """
    Detects the SQL dialect based on specific keywords and patterns.
    Defaults to 'postgres' if no specific dialect is detected.
    """
    sql_upper = sql.upper()

    # Oracle indicators
    if "NVL" in sql_upper or "ROWNUM" in sql_upper or "SYSDATE" in sql_upper:
        return "oracle"
    
    # SQL Server indicators
    if "TOP " in sql_upper and "LIMIT" not in sql_upper:
        return "tsql" # sqlglot uses tsql for SQL Server
    if "GETDATE()" in sql_upper:
        return "tsql"

    # MySQL indicators
    if "LIMIT" in sql_upper and "OFFSET" in sql_upper:
        # PostgreSQL also uses LIMIT/OFFSET, but MySQL often uses backticks which we could check,
        # but for now, let's look for other hints or default to postgres if ambiguous, 
        # as postgres is a safe default for standard SQL.
        pass
    
    if "`" in sql: # Backticks are strong indicator for MySQL
        return "mysql"

    # PostgreSQL (default)
    # Look for specific PG functions or syntax if needed, but usually it's the target for standard SQL
    
    return "postgres"
