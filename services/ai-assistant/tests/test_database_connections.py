from unittest.mock import MagicMock, patch
import unittest

import psycopg2

from app.config import get_settings
from app.diagnostics import log_failure
from app.tools import RiskTools
from app.vector_store import PgVectorStore


class DatabaseConnectionTest(unittest.TestCase):
    def test_clients_do_not_send_pooler_incompatible_startup_options(self):
        for client in (RiskTools(get_settings()), PgVectorStore(get_settings())):
            with patch('psycopg2.connect') as connect:
                client._connect()
            self.assertNotIn('options', connect.call_args.kwargs)
            self.assertEqual(connect.call_args.kwargs['sslmode'], get_settings().postgres_sslmode)

    def test_vector_timeout_is_transaction_local(self):
        store = PgVectorStore(get_settings())
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        with patch.object(store, '_connect', return_value=connection):
            self.assertTrue(store.has_version('v1', 1))
        self.assertEqual(cursor.execute.call_args_list[0].args, ("SET LOCAL statement_timeout = '10s'",))
        connection.close.assert_called_once()

    def test_operational_error_categories_never_log_raw_credentials(self):
        for message, category in (
            ('unsupported startup parameter: statement_timeout', 'unsupported_startup_parameter'),
            ('password authentication failed for private-role', 'database_authentication_failed'),
            ('could not translate host name private-host', 'database_dns_failed'),
            ('timeout expired private-details', 'database_connection_timeout'),
        ):
            with self.assertLogs('app.diagnostics', level='ERROR') as logs:
                log_failure('answer', psycopg2.OperationalError(message))
            self.assertIn(category, logs.output[0])
            self.assertNotIn('private-', logs.output[0])

if __name__ == '__main__':
    unittest.main()
