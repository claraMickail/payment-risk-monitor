from pathlib import Path
import sqlite3
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "payment_risk_monitor.db"

# open the database function
def get_connection() -> sqlite3.Connection:
    """Connect to the local SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

# define how data is organized function
def initialize_database() -> None:
    """Create the tables used by the risk-monitoring workflow."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS import_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                rows_received INTEGER NOT NULL CHECK(rows_received >= 0),
                rows_loaded INTEGER NOT NULL DEFAULT 0 CHECK(rows_loaded >= 0),
                rows_rejected INTEGER NOT NULL DEFAULT 0 CHECK(rows_rejected >= 0)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_run_id INTEGER NOT NULL,
                source_row INTEGER NOT NULL,
                step INTEGER NOT NULL CHECK(step >= 0),
                customer_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                is_fraud INTEGER NOT NULL CHECK(is_fraud IN (0, 1)),
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (import_run_id)
                    REFERENCES import_runs(id)
                    ON DELETE CASCADE,
                UNIQUE(import_run_id, source_row)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_import_run
                ON transactions(import_run_id);

            CREATE INDEX IF NOT EXISTS idx_transactions_category
                ON transactions(category);

            CREATE INDEX IF NOT EXISTS idx_transactions_merchant
                ON transactions(merchant_id);
            """
        )


def create_import_run(source_name: str, rows_received: int) -> int:
    """Record a new data batch and return its ID."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO import_runs (source_name, rows_received)
            VALUES (?, ?)
            """,
            (source_name, rows_received),
        )
        return int(cursor.lastrowid)


def complete_import_run(
    import_run_id: int,
    rows_loaded: int,
    rows_rejected: int,
) -> None:
    """Save the final outcome of an import."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE import_runs
            SET rows_loaded = ?, rows_rejected = ?
            WHERE id = ?
            """,
            (rows_loaded, rows_rejected, import_run_id),
        )


def insert_transactions(
    import_run_id: int,
    records: Iterable[tuple[int, int, str, str, str, float, int]],
) -> None:
    """Store validated transaction records for one import."""
    rows = [(import_run_id, *record) for record in records]

    if not rows:
        return

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO transactions (
                import_run_id,
                source_row,
                step,
                customer_id,
                merchant_id,
                category,
                amount,
                is_fraud
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_latest_import_run_id() -> int | None:
    """Return the newest import ID, if data has been loaded."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM import_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    return int(row["id"]) if row else None