import sqlglot
from sqlglot import exp
from typing import List, Dict, Any
from utils.sql_utils import is_select_star

class QueryAnalyzer:
    def analyze(self, ast: exp.Expression) -> List[Dict[str, Any]]:
        issues = []
        
        # 1. Check for SELECT *
        if is_select_star(ast):
            issues.append({
                "type": "performance",
                "severity": "medium",
                "message": "Avoid using SELECT *, specify columns explicitly to reduce I/O.",
                "code": "SELECT_STAR"
            })

        # 2. Check for missing WHERE clause (potential full table scan)
        # Only relevant for SELECT, UPDATE, DELETE
        if isinstance(ast, (exp.Select, exp.Update, exp.Delete)):
            if not ast.args.get("where"):
                # Exception: If it's a simple SELECT without joins, maybe it's intended, but still worth a warning for large tables
                # If there are joins, it's definitely suspicious if there's no WHERE (though ON clauses handle joins)
                issues.append({
                    "type": "performance",
                    "severity": "high",
                    "message": "Query has no WHERE clause, which may cause a full table scan.",
                    "code": "MISSING_WHERE"
                })

        # 3. Check for leading wildcards in LIKE
        for like in ast.find_all(exp.Like):
            pattern = like.args.get("this")
            if isinstance(pattern, exp.Literal) and pattern.is_string:
                val = pattern.this
                if val.startswith("%"):
                    issues.append({
                        "type": "performance",
                        "severity": "high",
                        "message": "Leading wildcard in LIKE pattern ('%...') prevents index usage.",
                        "code": "LEADING_WILDCARD"
                    })

        # 4. Check for functions on columns in WHERE clause
        # Example: WHERE YEAR(date_col) = 2023
        if ast.args.get("where"):
            where = ast.args.get("where")
            for binary in where.find_all(exp.Binary):
                left = binary.left
                # If left side is a function call
                if isinstance(left, exp.Func):
                    # And it involves a column
                    if any(left.find_all(exp.Column)):
                        issues.append({
                            "type": "performance",
                            "severity": "medium",
                            "message": f"Function call {left.sql()} on column in WHERE clause may prevent index usage.",
                            "code": "FUNCTION_ON_COLUMN"
                        })

        # 5. Check for OR conditions which might block index usage (simple heuristic)
        if ast.args.get("where"):
            where = ast.args.get("where")
            if list(where.find_all(exp.Or)):
                 issues.append({
                    "type": "performance",
                    "severity": "low",
                    "message": "OR conditions can sometimes prevent effective index usage. Consider UNION ALL if appropriate.",
                    "code": "OR_CONDITION"
                })

        # 6. Check for Join Explosion (Too many joins)
        joins = list(ast.find_all(exp.Join))
        if len(joins) > 3:
            issues.append({
                "type": "performance",
                "severity": "medium",
                "message": f"Query has {len(joins)} joins. Complex joins can be slow and hard to optimize.",
                "code": "JOIN_EXPLOSION"
            })

        # 7. Check for NULL Pitfall (NOT IN with subquery)
        # NOT IN (SELECT ...) returns NULL if any value in subquery is NULL, causing unexpected empty results.
        if isinstance(ast, exp.Select):
            for not_in in ast.find_all(exp.In):
                parent = not_in.parent
                if isinstance(parent, exp.Not):
                    if any(not_in.find_all(exp.Subquery)):
                         issues.append({
                            "type": "correctness",
                            "severity": "high",
                            "message": "NOT IN with subquery is dangerous if subquery returns NULLs. Use NOT EXISTS or LEFT JOIN.",
                            "code": "NULL_PITFALL"
                        })

        # 8. Check for Implicit Casts (Heuristic)
        # Look for string literals compared to likely numeric columns (ending in _id, _count, etc.)
        where = ast.args.get("where")
        if where:
            for binary in where.find_all(exp.Binary):
                left = binary.left
                right = binary.right
                
                # Check left=col, right=string literal
                if isinstance(left, exp.Column) and isinstance(right, exp.Literal) and right.is_string:
                    if left.name.endswith(("_id", "_count", "_num", "_qty")):
                         issues.append({
                            "type": "performance",
                            "severity": "medium",
                            "message": f"Potential implicit cast: Comparing string '{right.this}' to likely numeric column '{left.name}'.",
                            "code": "IMPLICIT_CAST"
                        })
                # Check left=string literal, right=col
                elif isinstance(right, exp.Column) and isinstance(left, exp.Literal) and left.is_string:
                    if right.name.endswith(("_id", "_count", "_num", "_qty")):
                         issues.append({
                            "type": "performance",
                            "severity": "medium",
                            "message": f"Potential implicit cast: Comparing string '{left.this}' to likely numeric column '{right.name}'.",
                            "code": "IMPLICIT_CAST"
                        })

        # 9. Check for N+1 Pattern (Heuristic)
        # Queries that select from a table with a WHERE id = ? inside a loop (hard to detect static SQL, but can warn on simple ID lookups if context implies)
        # Actually, a better static check is: SELECT * FROM table WHERE id IN (...) is better than many single lookups.
        # But for single query analysis, we can't easily detect N+1 without seeing the application loop.
        # Instead, let's detect "LIMIT 1" without ORDER BY which is often non-deterministic.
        if isinstance(ast, exp.Select):
            limit = ast.args.get("limit")
            order = ast.args.get("order")
            if limit and not order:
                 issues.append({
                    "type": "correctness",
                    "severity": "low",
                    "message": "LIMIT used without ORDER BY causes non-deterministic results.",
                    "code": "NON_DETERMINISTIC_LIMIT"
                })

        return issues

    def calculate_complexity_score(self, ast: exp.Expression) -> Dict[str, Any]:
        """
        Calculates a heuristic complexity score (1-10) for the query.
        Returns a dictionary with score and breakdown.
        """
        score = 1
        breakdown = {
            "base": 1,
            "joins": 0,
            "subqueries": 0,
            "group_by": 0,
            "order_by": 0,
            "having": 0,
            "set_ops": 0
        }
        
        # +1 for each JOIN
        joins = len(list(ast.find_all(exp.Join)))
        score += joins
        breakdown["joins"] = joins
        
        # +1 for each Subquery
        subqueries = len(list(ast.find_all(exp.Subquery)))
        score += subqueries
        breakdown["subqueries"] = subqueries
        
        # +1 for GROUP BY
        if ast.args.get("group"):
            score += 1
            breakdown["group_by"] = 1
            
        # +1 for ORDER BY
        if ast.args.get("order"):
            score += 1
            breakdown["order_by"] = 1
            
        # +1 for HAVING
        if ast.args.get("having"):
            score += 1
            breakdown["having"] = 1

        # +2 for UNION / INTERSECT / EXCEPT
        set_ops = 0
        set_ops += len(list(ast.find_all(exp.Union))) * 2
        set_ops += len(list(ast.find_all(exp.Intersect))) * 2
        set_ops += len(list(ast.find_all(exp.Except))) * 2
        score += set_ops
        breakdown["set_ops"] = set_ops

        final_score = min(score, 10)
        return {
            "score": final_score,
            "breakdown": breakdown
        }
