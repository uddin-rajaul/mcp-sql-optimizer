import sqlglot
from sqlglot import exp
from typing import List, Dict, Any

class IndexSuggester:
    def suggest_indexes(self, sql: str, dialect: str = "postgres") -> List[Dict[str, Any]]:
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
        except:
            return []

        suggestions = []
        
        # Helper to resolve table name
        tables = [t.name for t in parsed.find_all(exp.Table)]
        default_table = tables[0] if len(tables) == 1 else None

        def get_table_name(column: exp.Column) -> str:
            if column.table:
                return column.table
            return default_table

        # 1. Analyze WHERE clause
        where = parsed.args.get("where")
        if where:
            for column in where.find_all(exp.Column):
                table = get_table_name(column)
                col_name = column.name
                if table:
                    suggestions.append({
                        "table": table,
                        "columns": [col_name],
                        "reason": "Column used in WHERE clause filter.",
                        "priority": "high"
                    })

        # 2. Analyze JOIN ON clauses
        for join in parsed.find_all(exp.Join):
            on = join.args.get("on")
            if on:
                for column in on.find_all(exp.Column):
                    table = get_table_name(column)
                    col_name = column.name
                    if table:
                        suggestions.append({
                            "table": table,
                            "columns": [col_name],
                            "reason": "Column used in JOIN condition.",
                            "priority": "high"
                        })

        # 3. Analyze GROUP BY
        group = parsed.args.get("group")
        if group:
            for column in group.find_all(exp.Column):
                table = get_table_name(column)
                col_name = column.name
                if table:
                    suggestions.append({
                        "table": table,
                        "columns": [col_name],
                        "reason": "Column used in GROUP BY.",
                        "priority": "medium"
                    })

        # 4. Analyze ORDER BY
        order = parsed.args.get("order")
        if order:
            for column in order.find_all(exp.Column):
                table = get_table_name(column)
                col_name = column.name
                if table:
                    suggestions.append({
                        "table": table,
                        "columns": [col_name],
                        "reason": "Column used in ORDER BY.",
                        "priority": "low"
                    })

        # 5. Analyze AND conditions for Composite Indexes
        # Heuristic: If multiple columns are used in AND equality predicates in WHERE, suggest a composite index.
        if where:
            and_columns = []
            for binary in where.find_all(exp.And):
                # Check left and right sides
                for node in [binary.left, binary.right]:
                    if isinstance(node, exp.EQ):
                        # Check if it's a column
                        cols = list(node.find_all(exp.Column))
                        if len(cols) == 1:
                            col = cols[0]
                            table = get_table_name(col)
                            if table:
                                and_columns.append((table, col.name))
            
            # Group by table
            table_cols = {}
            for table, col in and_columns:
                if table not in table_cols:
                    table_cols[table] = set()
                table_cols[table].add(col)
            
            for table, cols in table_cols.items():
                if len(cols) > 1:
                    col_list = list(cols)
                    suggestions.append({
                        "table": table,
                        "columns": col_list,
                        "reason": "Columns used together in AND equality predicates. Composite index recommended.",
                        "priority": "critical"
                    })

        # 6. Analyze Covering Indexes
        # Check if we can satisfy the query using only the index (SELECT cols + WHERE cols)
        # This is hard to do perfectly without schema, but we can suggest it if SELECT list is small.
        if isinstance(parsed, exp.Select):
            select_cols = set()
            for col in parsed.expressions:
                if isinstance(col, exp.Column):
                    select_cols.add(col.name)
                elif isinstance(col, exp.Star):
                    select_cols = None # Can't determine covering index for SELECT *
                    break
            
            if select_cols:
                # Check against WHERE columns for each table
                where_cols_by_table = {}
                if where:
                    for col in where.find_all(exp.Column):
                        t = get_table_name(col)
                        if t:
                            if t not in where_cols_by_table:
                                where_cols_by_table[t] = set()
                            where_cols_by_table[t].add(col.name)
                
                for table, w_cols in where_cols_by_table.items():
                    # If all select cols for this table are in w_cols or we add them...
                    # Actually covering index = WHERE cols + SELECT cols
                    # We need to know which select cols belong to this table.
                    # Simplified: If we have a high priority index suggestion for this table,
                    # suggest adding the SELECT columns to it to make it covering.
                    
                    # Find existing suggestions for this table
                    existing = [s for s in suggestions if s['table'] == table and s['priority'] in ('high', 'critical')]
                    for s in existing:
                        # If the index columns don't already cover the select columns
                        idx_cols = set(s['columns'])
                        missing = select_cols - idx_cols
                        # Filter missing to likely belong to this table (heuristic: if unique name or we assume)
                        # Without schema, this is risky. Let's just suggest if it's a small number of extra cols.
                        if missing and len(missing) < 3:
                             suggestions.append({
                                "table": table,
                                "columns": s['columns'] + list(missing),
                                "reason": f"Extend index to include {list(missing)} for a Covering Index (avoids table lookup).",
                                "priority": "medium"
                            })

        # 7. Suggest Foreign Key Indexes
        # Heuristic: Columns ending in _id are likely FKs and should be indexed for joins/lookups.
        # Only suggest if not already covered by other suggestions.
        if isinstance(parsed, exp.Select):
             # Check all columns in the query (WHERE, JOIN, SELECT)
             # Actually, we should check tables involved.
             # Let's just scan for columns ending in _id in WHERE/JOIN/GROUP/ORDER
             # We already cover WHERE/JOIN/GROUP/ORDER in previous steps.
             # So this is mostly for columns that MIGHT be used in joins later or are standard practice.
             # Let's stick to what's in the query.
             pass

        # Deduplicate and format suggestions
        unique_suggestions = {}
        for s in suggestions:
            # Sort columns for consistent key in composite indexes
            cols_key = ",".join(sorted(s['columns']))
            key = f"{s['table']}:{cols_key}"
            
            # Generate DDL
            # Name convention: idx_<table>_<col1>_<col2>
            idx_name = f"idx_{s['table']}_{'_'.join(s['columns'])[:40]}"
            ddl = f"CREATE INDEX {idx_name} ON {s['table']} ({', '.join(s['columns'])});"
            s['ddl'] = ddl
            
            if key not in unique_suggestions:
                unique_suggestions[key] = s
            else:
                # Upgrade priority if found again
                current_p = unique_suggestions[key]['priority']
                new_p = s['priority']
                priorities = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
                if priorities.get(new_p, 0) > priorities.get(current_p, 0):
                    unique_suggestions[key] = s

        return list(unique_suggestions.values())
