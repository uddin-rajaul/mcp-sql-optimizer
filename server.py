from mcp.server.fastmcp import FastMCP
from core.dialect_detector import detect_dialect
from core.parser import QueryParser
from core.analyzer import QueryAnalyzer
from core.rewriter import QueryRewriter
from core.indexer import IndexSuggester
from core.explain_parser import ExplainParser
from utils.formatting import format_json_response, create_table_comparison
from typing import Optional, Dict, Any

# Initialize FastMCP server
mcp = FastMCP("sql-optimizer")

# Initialize core components
parser = QueryParser()
analyzer = QueryAnalyzer()
rewriter = QueryRewriter()
indexer = IndexSuggester()
explain_parser = ExplainParser()

@mcp.tool()
def analyze_query(sql: str, dialect: str = "auto", schema: Optional[str] = None, explain_plan: Optional[str] = None) -> str:
    """
    Analyzes a SQL query for performance issues and inefficiencies.
    
    Args:
        sql: The SQL query to analyze.
        dialect: The SQL dialect (postgresql, mysql, oracle, sqlserver, auto).
        schema: Optional schema definition (not fully used in this version).
        explain_plan: Optional text output from an EXPLAIN command.
    """
    if dialect == "auto":
        dialect = detect_dialect(sql)

    # Parse
    parse_result = parser.parse(sql, dialect)
    if "error" in parse_result:
        return format_json_response({"error": parse_result["error"]})

    ast = parse_result["ast"]
    
    # Analyze
    issues = analyzer.analyze(ast)
    complexity_data = analyzer.calculate_complexity_score(ast)
    
    # Explain Plan Analysis
    explain_analysis = {}
    explain_visualization = ""
    if explain_plan:
        explain_analysis = explain_parser.parse(explain_plan, dialect)
        explain_visualization = explain_parser.visualize_plan(explain_analysis)

    response = {
        "dialect": dialect,
        "query_structure": parse_result["metadata"],
        "complexity": complexity_data,
        "issues": issues,
        "explain_analysis": explain_analysis,
        "explain_visualization": explain_visualization,
        "summary": f"Found {len(issues)} potential performance issues. Complexity Score: {complexity_data['score']}/10"
    }
    
    return format_json_response(response)

@mcp.tool()
def optimize_query(sql: str, dialect: str = "postgres") -> str:
    """
    Rewrites a SQL query to be more optimized.
    
    Args:
        sql: The SQL query to optimize.
        dialect: The SQL dialect.
    """
    # Rewrite
    optimized_sql = rewriter.rewrite(sql, dialect)
    
    # Compare
    improvements = rewriter.get_improvements(sql, optimized_sql)
    
    # Alternatives
    alternatives = rewriter.generate_alternatives(sql, dialect)
    
    # Cost Estimation
    # We need to parse both to get complexity
    try:
        orig_ast = parser.parse(sql, dialect)["ast"]
        opt_ast = parser.parse(optimized_sql, dialect)["ast"]
        orig_score = analyzer.calculate_complexity_score(orig_ast)["score"]
        opt_score = analyzer.calculate_complexity_score(opt_ast)["score"]
        cost_reduction = rewriter.estimate_cost_reduction(orig_score, opt_score)
    except:
        cost_reduction = "Could not estimate cost reduction."

    response = {
        "original_sql": sql,
        "optimized_sql": optimized_sql,
        "alternatives": alternatives,
        "improvements": improvements,
        "cost_reduction": cost_reduction,
        "comparison": create_table_comparison(sql, optimized_sql)
    }
    
    return format_json_response(response)

@mcp.tool()
def suggest_indexes(sql: str, schema: Optional[str] = None) -> str:
    """
    Suggests indexes based on the query's WHERE, JOIN, and GROUP BY clauses.
    
    Args:
        sql: The SQL query.
        schema: Optional schema context.
    """
    dialect = detect_dialect(sql)
    suggestions = indexer.suggest_indexes(sql, dialect)
    
    response = {
        "dialect": dialect,
        "index_suggestions": suggestions,
        "count": len(suggestions)
    }
    
    return format_json_response(response)

if __name__ == "__main__":
    import sys
    print("Universal SQL Query Optimizer MCP Server running on stdio...", file=sys.stderr)
    mcp.run()
