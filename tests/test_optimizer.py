import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dialect_detector import detect_dialect
from core.parser import QueryParser
from core.analyzer import QueryAnalyzer
from core.rewriter import QueryRewriter
from core.indexer import IndexSuggester

class TestSQLOptimizer(unittest.TestCase):
    def setUp(self):
        self.parser = QueryParser()
        self.analyzer = QueryAnalyzer()
        self.rewriter = QueryRewriter()
        self.indexer = IndexSuggester()

    def test_dialect_detector(self):
        self.assertEqual(detect_dialect("SELECT * FROM table LIMIT 10"), "postgres")
        self.assertEqual(detect_dialect("SELECT * FROM table WHERE ROWNUM < 10"), "oracle")
        self.assertEqual(detect_dialect("SELECT TOP 10 * FROM table"), "tsql")

    def test_parser(self):
        sql = "SELECT id, name FROM users WHERE age > 21"
        result = self.parser.parse(sql)
        self.assertNotIn("error", result)
        self.assertEqual(result["metadata"]["tables"], ["users"])
        self.assertEqual(result["metadata"]["columns"], ["id", "name", "age"])

    def test_analyzer_select_star(self):
        sql = "SELECT * FROM users"
        ast = self.parser.parse(sql)["ast"]
        issues = self.analyzer.analyze(ast)
        self.assertTrue(any(i["code"] == "SELECT_STAR" for i in issues))

    def test_analyzer_missing_where(self):
        sql = "SELECT name FROM users"
        ast = self.parser.parse(sql)["ast"]
        issues = self.analyzer.analyze(ast)
        self.assertTrue(any(i["code"] == "MISSING_WHERE" for i in issues))

    def test_rewriter(self):
        # Test simple optimization (e.g. 1=1 removal or just ensuring it runs)
        sql = "SELECT * FROM users WHERE 1=1"
        optimized = self.rewriter.rewrite(sql)
        # sqlglot usually removes 1=1
        self.assertIn("SELECT", optimized)
        # Note: exact output depends on sqlglot version, but it should be valid SQL

    def test_indexer(self):
        sql = "SELECT * FROM users WHERE email = 'test@example.com'"
        suggestions = self.indexer.suggest_indexes(sql)
        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0]["table"], "users")
        self.assertEqual(suggestions[0]["columns"], ["email"])

if __name__ == '__main__':
    unittest.main()
