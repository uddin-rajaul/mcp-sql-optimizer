import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    # Get absolute path to server.py
    server_script = os.path.abspath("server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None
    )

    print(f"Starting server: {sys.executable} {server_script}")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            sql_missing_where = "SELECT name FROM users"
            print(f"Input SQL: {sql_missing_where}")
            result = await session.call_tool("analyze_query", arguments={
                "sql": sql_missing_where
            })
            print("Result:")
            print(result.content[0].text)

            # Test 1c: Analyze Query - Leading Wildcard & Function on Column
            print("\n--- Testing analyze_query (Wildcard & Function) ---")
            sql_wildcard = "SELECT id FROM users WHERE name LIKE '%doe' AND YEAR(created_at) = 2023"
            print(f"Input SQL: {sql_wildcard}")
            result = await session.call_tool("analyze_query", arguments={
                "sql": sql_wildcard
            })
            print("Result:")
            print(result.content[0].text)

            # Test 1d: Analyze Query - Complexity & Join Explosion & NULL Pitfall
            print("\n--- Testing analyze_query (Complexity, Joins, NULL Pitfall) ---")
            sql_complex = """
            SELECT * 
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN products p ON o.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN regions r ON u.region_id = r.id
            WHERE u.id NOT IN (SELECT user_id FROM banned_users)
            """
            print(f"Input SQL: {sql_complex}")
            result = await session.call_tool("analyze_query", arguments={
                "sql": sql_complex
            })
            print("Result:")
            print(result.content[0].text)

            # Test 3: Suggest Indexes (Composite & Covering)
            print("\n--- Testing suggest_indexes (Composite & Covering) ---")
            sql_composite = "SELECT id, name FROM users WHERE region_id = 5 AND status = 'active'"
            print(f"Input SQL: {sql_composite}")
            result = await session.call_tool("suggest_indexes", arguments={
                "sql": sql_composite
            })
            print("Result:")
            print(result.content[0].text)

            # Test 1e: Analyze Query - Anti-Patterns (Implicit Cast, N+1)
            print("\n--- Testing analyze_query (Anti-Patterns) ---")
            sql_antipattern = "SELECT * FROM orders WHERE user_id = '123' LIMIT 1"
            print(f"Input SQL: {sql_antipattern}")
            result = await session.call_tool("analyze_query", arguments={
                "sql": sql_antipattern
            })
            print("Result:")
            print(result.content[0].text)

            # Test 1f: Analyze Query - Explain Plan Visualization
            print("\n--- Testing analyze_query (Explain Plan) ---")
            explain_text = """
            Seq Scan on orders  (cost=0.00..458.00 rows=10000 width=244)
            """
            sql_explain = "SELECT * FROM orders"
            print(f"Input Explain Plan: {explain_text.strip()}")
            result = await session.call_tool("analyze_query", arguments={
                "sql": sql_explain,
                "explain_plan": explain_text
            })
            print("Result:")
            print(result.content[0].text)
            
            # Test 3: Suggest Indexes
            print("\n--- Testing suggest_indexes ---")
            sql_index = "SELECT * FROM products WHERE category = 'electronics' AND price < 500"
            print(f"Input SQL: {sql_index}")
            result = await session.call_tool("suggest_indexes", arguments={
                "sql": sql_index
            })
            print("Result:")
            print(result.content[0].text)

if __name__ == "__main__":
    # Fix for Windows asyncio loop policy if needed, though Python 3.10+ usually handles it
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run())
