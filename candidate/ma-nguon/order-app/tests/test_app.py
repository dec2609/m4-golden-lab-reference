import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app import app


class OrderApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_ready_when_database_connected(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn

        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = (1,)

        with patch(
            "app.get_db_connection",
            return_value=conn,
        ) as mock_db:
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "ready", "database": "connected"},
        )
        cursor.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_called_once()
        mock_db.assert_called_once()

    def test_ready_connection_failure(self):
        with patch(
            "app.get_db_connection",
            side_effect=Exception("SENSITIVE_DB_DETAILS"),
        ) as mock_db:
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "status": "unready",
                "error": "database unreachable",
            },
        )
        self.assertNotIn(
            "SENSITIVE_DB_DETAILS",
            response.get_data(as_text=True),
        )
        mock_db.assert_called_once()

    def test_ready_query_failure(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn

        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        cursor.execute.side_effect = Exception("SENSITIVE_SQL_DETAILS")

        with patch("app.get_db_connection", return_value=conn):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "status": "unready",
                "error": "database unreachable",
            },
        )
        self.assertNotIn(
            "SENSITIVE_SQL_DETAILS",
            response.get_data(as_text=True),
        )

    def test_ready_connection_timeout_returns_503(self):
        with patch(
            "app.get_db_connection",
            side_effect=TimeoutError("simulated connect timeout"),
        ) as mock_db:
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "status": "unready",
                "error": "database unreachable",
            },
        )
        self.assertNotIn(
            "simulated connect timeout",
            response.get_data(as_text=True),
        )
        mock_db.assert_called_once()

    def test_ready_query_timeout_returns_503(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn

        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        cursor.execute.side_effect = TimeoutError(
            "simulated query timeout"
        )

        with patch("app.get_db_connection", return_value=conn):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "status": "unready",
                "error": "database unreachable",
            },
        )
        self.assertNotIn(
            "simulated query timeout",
            response.get_data(as_text=True),
        )

    def test_ready_recovers_after_database_returns(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn

        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = (1,)

        with patch(
            "app.get_db_connection",
            side_effect=[
                Exception("simulated database outage"),
                conn,
            ],
        ) as mock_db:
            failed_response = self.client.get("/ready")
            recovered_response = self.client.get("/ready")

        self.assertEqual(failed_response.status_code, 503)
        self.assertEqual(recovered_response.status_code, 200)
        self.assertEqual(
            recovered_response.get_json(),
            {"status": "ready", "database": "connected"},
        )
        self.assertEqual(mock_db.call_count, 2)

    def test_health_stays_ok_when_database_unavailable(self):
        with patch(
            "app.get_db_connection",
            side_effect=Exception("database unavailable"),
        ) as mock_db:
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        mock_db.assert_not_called()


    def test_get_orders(self):
        response = self.client.get("/orders")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIsInstance(data, dict)
        self.assertIn("orders", data)
        self.assertIsInstance(data["orders"], list)

    def test_create_order_and_read_back(self):
        payload = {
            "customer_name": "Test Customer",
            "product_name": "Test Product",
            "quantity": 2,
        }

        create_response = self.client.post("/orders", json=payload)

        self.assertEqual(create_response.status_code, 201)

        created = create_response.get_json()

        self.assertIsInstance(created["id"], int)
        self.assertEqual(created["customer_name"], payload["customer_name"])
        self.assertEqual(created["product_name"], payload["product_name"])
        self.assertEqual(created["quantity"], payload["quantity"])
        self.assertEqual(created["status"], "pending")
        self.assertTrue(created["created_at"].endswith("Z"))

        get_response = self.client.get("/orders")

        self.assertEqual(get_response.status_code, 200)

        orders = get_response.get_json()["orders"]
        ids = [order["id"] for order in orders]

        self.assertIn(created["id"], ids)

    def test_missing_customer_name(self):
        response = self.client.post(
            "/orders",
            json={
                "product_name": "Mouse",
                "quantity": 1,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_blank_customer_name(self):
        response = self.client.post(
            "/orders",
            json={
                "customer_name": "   ",
                "product_name": "Mouse",
                "quantity": 1,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_product_name(self):
        response = self.client.post(
            "/orders",
            json={
                "customer_name": "Test Customer",
                "quantity": 1,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_valid_quantity_boundaries(self):
        for quantity in (1, 2147483647):
            with self.subTest(quantity=quantity):
                row = {
                    "id": 101,
                    "customer_name": "Test Customer",
                    "product_name": "Mouse",
                    "quantity": quantity,
                    "status": "pending",
                    "created_at": datetime(
                        2026, 1, 1, tzinfo=timezone.utc
                    ),
                }

                conn = MagicMock()
                conn.__enter__.return_value = conn

                cur = MagicMock()
                conn.cursor.return_value.__enter__.return_value = cur
                cur.fetchone.return_value = row

                with patch(
                    "app.get_db_connection",
                    return_value=conn,
                ) as mock_db:
                    response = self.client.post(
                        "/orders",
                        json={
                            "customer_name": "Test Customer",
                            "product_name": "Mouse",
                            "quantity": quantity,
                        },
                    )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(
                    response.get_json()["quantity"],
                    quantity,
                )
                mock_db.assert_called_once()

                sql_params = cur.execute.call_args.args[1]
                self.assertEqual(sql_params[2], quantity)
    def test_extra_fields_are_ignored(self):
        row = {
            "id": 101,
            "customer_name": "Test Customer",
            "product_name": "Mouse",
            "quantity": 1,
            "status": "pending",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }

        conn = MagicMock()
        conn.__enter__.return_value = conn
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        cur.fetchone.return_value = row

        with patch("app.get_db_connection", return_value=conn):
            response = self.client.post(
                "/orders",
                json={
                    "customer_name": "Test Customer",
                    "product_name": "Mouse",
                    "quantity": 1,
                    "id": 999,
                    "status": "shipped",
                    "created_at": "not-controlled-by-client",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["id"], 101)
        self.assertEqual(response.get_json()["status"], "pending")
        self.assertEqual(
            cur.execute.call_args.args[1],
            ("Test Customer", "Mouse", 1),
        )

    def test_invalid_quantity_values(self):
        invalid_quantities = [
            0,
            -1,
            "2",
            2.5,
            True,
            None,
            2147483648,
        ]

        with patch("app.get_db_connection") as mock_db:
            for quantity in invalid_quantities:
                with self.subTest(quantity=quantity):
                    response = self.client.post(
                        "/orders",
                        json={
                            "customer_name": "Test Customer",
                            "product_name": "Mouse",
                            "quantity": quantity,
                        },
                    )

                    self.assertEqual(response.status_code, 400)

            mock_db.assert_not_called()
    def test_invalid_payloads_rejected_before_database(self):
        invalid_payloads = [
            [],
            "not an object",
            123,
            None,
            {},
            {
                "customer_name": "",
                "product_name": "Mouse",
                "quantity": 1,
            },
            {
                "customer_name": "Test Customer",
                "product_name": "",
                "quantity": 1,
            },
            {
                "customer_name": "Test Customer",
                "product_name": "   ",
                "quantity": 1,
            },
            {
                "customer_name": "Test Customer",
                "product_name": "Mouse",
            },
        ]

        with patch("app.get_db_connection") as mock_db:
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    response = self.client.post(
                        "/orders",
                        json=payload,
                    )
                    self.assertEqual(response.status_code, 400)

            mock_db.assert_not_called()

    def test_malformed_json(self):
        response = self.client.post(
            "/orders",
            data='{"customer_name":"Test","product_name":"Mouse","quantity":',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "Invalid JSON body"},
        )

    def test_get_orders_database_failure(self):
        with patch("app.get_db_connection", side_effect=Exception("database unavailable")):
            response = self.client.get("/orders")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json(),
            {"error": "Internal server error"},
        )

    def test_create_order_database_failure(self):
        with patch("app.get_db_connection", side_effect=Exception("database unavailable")):
            response = self.client.post(
                "/orders",
                json={
                    "customer_name": "Test Customer",
                    "product_name": "Mouse",
                    "quantity": 1,
                },
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json(),
            {"error": "Internal server error"},
        )


if __name__ == "__main__":
    unittest.main()