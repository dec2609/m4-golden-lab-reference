import os
from datetime import timezone

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import dict_row


app = Flask(__name__)


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "order-db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "orders"),
        user=os.getenv("DB_USER", "orders"),
        password=os.getenv("DB_PASSWORD", "orders-dev"),
        connect_timeout=2,
        options="-c statement_timeout=2000",
    )

def serialize_order(row):
    created_at = row["created_at"].astimezone(timezone.utc)

    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "product_name": row["product_name"],
        "quantity": row["quantity"],
        "status": row["status"],
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


@app.get("/health")
def health():
    return jsonify(status="ok")

@app.get("/ready")
def ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return jsonify(
            status="ready",
            database="connected",
        ), 200

    except Exception:
        return jsonify(
            status="unready",
            error="database unreachable",
        ), 503


@app.get("/orders")
def get_orders():
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, customer_name, product_name,
                           quantity, status, created_at
                    FROM orders
                    ORDER BY id
                    """
                )
                rows = cur.fetchall()

        return jsonify(orders=[serialize_order(row) for row in rows]), 200

    except Exception:
        return jsonify(error="Internal server error"), 500


@app.post("/orders")
def create_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON body"), 400

    customer_name = data.get("customer_name")
    product_name = data.get("product_name")
    quantity = data.get("quantity")

    if (
        not isinstance(customer_name, str)
        or not customer_name.strip()
    ):
        return jsonify(error="customer_name must be a non-empty string"), 400

    if (
        not isinstance(product_name, str)
        or not product_name.strip()
    ):
        return jsonify(error="product_name must be a non-empty string"), 400

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or not 1 <= quantity <= 2_147_483_647
    ):
        return jsonify(
            error="quantity must be an integer between 1 and 2147483647"
        ), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO orders (
                        customer_name,
                        product_name,
                        quantity
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id, customer_name, product_name,
                              quantity, status, created_at
                    """,
                    (
                        customer_name.strip(),
                        product_name.strip(),
                        quantity,
                    ),
                )
                row = cur.fetchone()

        return jsonify(serialize_order(row)), 201

    except Exception:
        return jsonify(error="Internal server error"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)