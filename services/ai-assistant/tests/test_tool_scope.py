import unittest
from unittest.mock import Mock, patch

from app.config import get_settings
from app.tools import RiskTools


class ToolScopeTest(unittest.TestCase):
    def test_customer_audit_query_filters_by_verified_user(self):
        tools = RiskTools(get_settings())
        connection = Mock()
        cursor = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        with patch.object(tools, '_connect', return_value=connection), patch.object(tools, '_cursor_factory'):
            result = tools.get_transaction_audit('tx-other', user_id='verified-user')
        sql, params = cursor.execute.call_args.args
        self.assertIn('AND user_id = %s', sql)
        self.assertEqual(params, ('tx-other', 'verified-user'))
        self.assertIsNone(result.result)

if __name__ == '__main__':
    unittest.main()
