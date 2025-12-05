import re
from typing import Dict, Any

class ExplainParser:
    def parse(self, explain_output: str, dialect: str = "postgres") -> Dict[str, Any]:
        """
        Parses the text output of an EXPLAIN command.
        """
        if dialect == "postgres":
            return self._parse_postgres(explain_output)
        elif dialect == "mysql":
            return self._parse_mysql(explain_output)
        else:
            return {"raw": explain_output, "message": "Parsing not implemented for this dialect yet."}

    def _parse_postgres(self, output: str) -> Dict[str, Any]:
        """
        Parses PostgreSQL EXPLAIN (ANALYZE, BUFFERS) output.
        """
        result = {
            "scans": [],
            "total_cost": 0.0,
            "slowest_node": None,
            "actual_rows": 0,
            "estimated_rows": 0
        }
        
        # Regex for Seq Scan
        seq_scans = re.findall(r"Seq Scan on (\w+)", output)
        if seq_scans:
            result["scans"].extend([{"type": "Seq Scan", "table": t} for t in seq_scans])
            
        # Regex for Index Scan
        idx_scans = re.findall(r"Index Scan using (\w+) on (\w+)", output)
        if idx_scans:
            result["scans"].extend([{"type": "Index Scan", "index": i, "table": t} for i, t in idx_scans])

        # Regex for Cost and Rows
        # Example: (cost=0.00..458.00 rows=10000 width=244)
        cost_match = re.search(r"cost=(\d+\.\d+)\.\.(\d+\.\d+)", output)
        if cost_match:
            result["total_cost"] = float(cost_match.group(2))
            
        rows_match = re.search(r"rows=(\d+)", output)
        if rows_match:
            result["estimated_rows"] = int(rows_match.group(1))
            
        # Actual rows (if ANALYZE used)
        # Example: (actual time=0.012..0.012 rows=1 loops=1)
        actual_rows_match = re.search(r"actual time=.* rows=(\d+)", output)
        if actual_rows_match:
            result["actual_rows"] = int(actual_rows_match.group(1))

        return result

    def _parse_mysql(self, output: str) -> Dict[str, Any]:
        """
        Parses MySQL EXPLAIN output (tabular or JSON).
        """
        result = {"scans": []}
        
        # Simple tabular parsing
        # id | select_type | table | partitions | type | possible_keys | key | key_len | ref | rows | filtered | Extra
        lines = output.strip().split('\n')
        headers = []
        for line in lines:
            if "select_type" in line and "table" in line:
                headers = [h.strip() for h in line.split('|') if h.strip()]
                continue
            
            if headers and "|" in line and "---" not in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) == len(headers):
                    row = dict(zip(headers, parts))
                    scan_info = {
                        "table": row.get("table"),
                        "type": row.get("type"),
                        "key": row.get("key"),
                        "rows": row.get("rows")
                    }
                    if row.get("type") == "ALL":
                         scan_info["warning"] = "Full Table Scan"
                    
                    result["scans"].append(scan_info)
        
        return result

    def visualize_plan(self, explain_data: Dict[str, Any]) -> str:
        """
        Generates a simple ASCII tree visualization of the plan.
        """
        scans = explain_data.get("scans", [])
        if not scans:
            return "No plan data available to visualize."
            
        lines = ["Execution Plan Tree:"]
        for i, scan in enumerate(scans):
            prefix = "  └─ " if i == len(scans) - 1 else "  ├─ "
            
            # Format node text
            node_type = scan.get("type", "Unknown")
            table = scan.get("table", "")
            index = scan.get("index", "")
            
            text = f"{node_type}"
            if table:
                text += f" on {table}"
            if index:
                text += f" using {index}"
                
            if scan.get("warning"):
                text += f" [WARNING: {scan['warning']}]"
                
            lines.append(f"{prefix}{text}")
            
        if explain_data.get("total_cost"):
            lines.append(f"\nTotal Cost: {explain_data['total_cost']}")
            
        return "\n".join(lines)
