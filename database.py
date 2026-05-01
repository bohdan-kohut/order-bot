import sqlite3

DB_NAME = "orders.db"


def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        phone TEXT,
        description TEXT,
        status TEXT DEFAULT 'new',
        amount INTEGER DEFAULT 0,
        invoice_id TEXT,
        payment_url TEXT,
        payment_status TEXT DEFAULT 'pending'
    )
    """)

    columns = {
        "user_id": "INTEGER",
        "status": "TEXT DEFAULT 'new'",
        "amount": "INTEGER DEFAULT 0",
        "invoice_id": "TEXT",
        "payment_url": "TEXT",
        "payment_status": "TEXT DEFAULT 'pending'",
    }

    for column, column_type in columns.items():
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {column} {column_type}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def save_order(user_id, name, phone, description, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO orders (user_id, name, phone, description, status, amount, payment_status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, phone, description, "new", amount, "pending"))

    order_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return order_id


def save_payment_info(order_id, invoice_id, payment_url):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE orders
    SET invoice_id = ?, payment_url = ?
    WHERE id = ?
    """, (invoice_id, payment_url, order_id))

    conn.commit()
    conn.close()


def get_orders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, user_id, name, phone, description, status, amount, invoice_id, payment_url, payment_status
    FROM orders
    ORDER BY id DESC
    LIMIT 10
    """)

    orders = cursor.fetchall()
    conn.close()

    return orders


def get_order_by_id(order_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, user_id, name, phone, description, status, amount, invoice_id, payment_url, payment_status
    FROM orders
    WHERE id = ?
    """, (order_id,))

    order = cursor.fetchone()
    conn.close()

    return order


def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE orders
    SET status = ?
    WHERE id = ?
    """, (status, order_id))

    conn.commit()
    conn.close()


def update_payment_status(order_id, payment_status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE orders
    SET payment_status = ?
    WHERE id = ?
    """, (payment_status, order_id))

    conn.commit()
    conn.close()