# SQL Query Optimizer MCP Server

A powerful Model Context Protocol (MCP) server that analyzes, optimizes, and suggests indexes for SQL queries across multiple dialects (PostgreSQL, MySQL, Oracle, SQL Server). Built with Python and `sqlglot`.

## Features

### Advanced Query Analysis
- **Complexity Scoring**: Calculates a heuristic complexity score (1-10) based on joins, subqueries, and set operations.
- **Detailed Breakdown**: Provides a granular breakdown of what contributes to the complexity.
- **Anti-Pattern Detection**: Identifies performance killers like:
  - `SELECT *` usage
  - Implicit type casts (e.g., `id = '123'`)
  - Potential N+1 queries (LIMIT without ORDER BY)
  - NULL pitfalls in `NOT IN` subqueries
  - Join explosions (> 3 joins)

### Query Optimization
- **Automated Rewriting**: Uses `sqlglot` to apply optimization rules like predicate pushdown and simplification.
- **Alternative Suggestions**: Generates alternative query forms (e.g., formatted only, CTE refactoring) alongside the main optimization.
- **Cost Estimation**: Estimates the structural complexity reduction (e.g., "~30%").
- **DDL Generation**: Generates `CREATE INDEX` statements for suggested indexes.

### Explain Plan Visualization
- **ASCII Tree View**: Visualizes `EXPLAIN` output as an easy-to-read ASCII tree.
- **Plan Parsing**: Extracts scans, costs, and rows from Postgres and MySQL plans.

### Index Suggestions
- **Composite Indexes**: Suggests multi-column indexes for `AND` conditions.
- **Covering Indexes**: Recommends extending indexes to include selected columns (Index-Only Scans).
- **Smart Prioritization**: Ranks suggestions by impact (Critical, High, Medium, Low).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/mcp-sql-optimizer.git
    cd mcp-sql-optimizer
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Add the server to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sql-optimizer": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\mcp-sql-optimizer\\server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\mcp-sql-optimizer"
      }
    }
  }
}
```

*Note: On Windows, use double backslashes `\\` in paths. The `PYTHONPATH` is crucial for the server to find its internal modules.*

### 🐳 Docker (Recommended)

Run the server in a container to avoid environment issues.

1.  **Build the image:**
    ```bash
    docker build -t mcp-sql-optimizer .
    ```

2.  **Configure Claude Desktop:**
    ```json
    {
      "mcpServers": {
        "sql-optimizer": {
          "command": "docker",
          "args": [
            "run",
            "-i",
            "--rm",
            "mcp-sql-optimizer"
          ]
        }
      }
    }
    ```

## Usage

The server exposes the following MCP tools:

### `analyze_query`
Analyzes a SQL query for performance issues, complexity, and anti-patterns. Optionally accepts an `explain_plan` string to visualize the execution plan.

**Input:**
```json
{
  "sql": "SELECT * FROM orders WHERE user_id = '123'",
  "dialect": "postgres"
}
```

### `optimize_query`
Rewrites the query to be more performant and provides alternative suggestions.

**Input:**
```json
{
  "sql": "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
  "dialect": "postgres"
}
```

### `suggest_indexes`
Suggests indexes to improve query performance, including DDL statements.

**Input:**
```json
{
  "sql": "SELECT * FROM users WHERE region_id = 5 AND status = 'active'",
  "dialect": "postgres"
}
```

## Project Structure

```
mcp-sql-optimizer/
├── server.py              # Main MCP server entry point
├── core/
│   ├── analyzer.py        # Performance & complexity analysis
│   ├── rewriter.py        # Query optimization & alternatives
│   ├── indexer.py         # Index suggestion logic
│   ├── explain_parser.py  # Explain plan parsing & visualization
│   ├── parser.py          # SQL parsing wrapper
│   └── dialect_detector.py# Dialect inference
├── utils/                 # Helper utilities
└── tests/                 # Unit tests
```

## Development

Run the demo client to test features without an MCP client:
```bash
python demo_client.py
```

Run unit tests:
```bash
python -m unittest discover tests
```

## License

MIT
