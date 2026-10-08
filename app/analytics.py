from app.database import get_connection, get_latest_import_run_id


def get_overview_metrics(
    import_run_id: int | None = None,
) -> dict[str, int | float] | None:
    """Return high-level payment-risk KPIs for one import batch."""
    selected_run_id = import_run_id or get_latest_import_run_id()

    if selected_run_id is None:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS transaction_count,
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(is_fraud), 0) AS fraud_transaction_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN is_fraud = 1 THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS fraud_exposure
            FROM transactions
            WHERE import_run_id = ?
            """,
            (selected_run_id,),
        ).fetchone()

    transaction_count = int(row["transaction_count"])
    fraud_transaction_count = int(row["fraud_transaction_count"])

    fraud_rate_percent = (
        (fraud_transaction_count / transaction_count) * 100
        if transaction_count
        else 0.0
    )

    return {
        "import_run_id": selected_run_id,
        "transaction_count": transaction_count,
        "total_amount": round(float(row["total_amount"]), 2),
        "fraud_transaction_count": fraud_transaction_count,
        "fraud_rate_percent": round(fraud_rate_percent, 2),
        "fraud_exposure": round(float(row["fraud_exposure"]), 2),
    }


def get_category_risk(
    import_run_id: int | None = None,
) -> list[dict[str, str | int | float]]:
    """Return payment-risk KPIs grouped by category for one import batch."""
    selected_run_id = import_run_id or get_latest_import_run_id()

    if selected_run_id is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                category,
                COUNT(*) AS transaction_count,
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(is_fraud), 0) AS fraud_transaction_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN is_fraud = 1 THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS fraud_exposure
            FROM transactions
            WHERE import_run_id = ?
            GROUP BY category
            ORDER BY fraud_exposure DESC, fraud_transaction_count DESC
            """,
            (selected_run_id,),
        ).fetchall()

    category_metrics = []

    for row in rows:
        transaction_count = int(row["transaction_count"])
        fraud_transaction_count = int(row["fraud_transaction_count"])

        fraud_rate_percent = (
            (fraud_transaction_count / transaction_count) * 100
            if transaction_count
            else 0.0
        )

        category_metrics.append(
            {
                "category": row["category"],
                "transaction_count": transaction_count,
                "total_amount": round(float(row["total_amount"]), 2),
                "fraud_transaction_count": fraud_transaction_count,
                "fraud_rate_percent": round(fraud_rate_percent, 2),
                "fraud_exposure": round(float(row["fraud_exposure"]), 2),
            }
        )

    return category_metrics

def get_top_risky_merchants(
    import_run_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, str | int | float]]:
    """Return the merchants with the highest flagged-payment value."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    selected_run_id = import_run_id or get_latest_import_run_id()

    if selected_run_id is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                merchant_id,
                COUNT(*) AS transaction_count,
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(is_fraud), 0) AS fraud_transaction_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN is_fraud = 1 THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS fraud_exposure
            FROM transactions
            WHERE import_run_id = ?
            GROUP BY merchant_id
            HAVING SUM(is_fraud) > 0
            ORDER BY fraud_exposure DESC, fraud_transaction_count DESC
            LIMIT ?
            """,
            (selected_run_id, limit),
        ).fetchall()

    merchant_metrics = []

    for row in rows:
        transaction_count = int(row["transaction_count"])
        fraud_transaction_count = int(row["fraud_transaction_count"])

        fraud_rate_percent = (
            (fraud_transaction_count / transaction_count) * 100
            if transaction_count
            else 0.0
        )

        merchant_metrics.append(
            {
                "merchant_id": row["merchant_id"],
                "transaction_count": transaction_count,
                "total_amount": round(float(row["total_amount"]), 2),
                "fraud_transaction_count": fraud_transaction_count,
                "fraud_rate_percent": round(fraud_rate_percent, 2),
                "fraud_exposure": round(float(row["fraud_exposure"]), 2),
            }
        )

    return merchant_metrics

def get_step_risk_trend(
    import_run_id: int | None = None,
) -> list[dict[str, int | float]]:
    """Return payment-risk KPIs across BankSim time steps."""
    selected_run_id = import_run_id or get_latest_import_run_id()

    if selected_run_id is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                step,
                COUNT(*) AS transaction_count,
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(is_fraud), 0) AS fraud_transaction_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN is_fraud = 1 THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS fraud_exposure
            FROM transactions
            WHERE import_run_id = ?
            GROUP BY step
            ORDER BY step ASC
            """,
            (selected_run_id,),
        ).fetchall()

    trend = []

    for row in rows:
        transaction_count = int(row["transaction_count"])
        fraud_transaction_count = int(row["fraud_transaction_count"])

        fraud_rate_percent = (
            (fraud_transaction_count / transaction_count) * 100
            if transaction_count
            else 0.0
        )

        trend.append(
            {
                "step": int(row["step"]),
                "transaction_count": transaction_count,
                "total_amount": round(float(row["total_amount"]), 2),
                "fraud_transaction_count": fraud_transaction_count,
                "fraud_rate_percent": round(fraud_rate_percent, 2),
                "fraud_exposure": round(float(row["fraud_exposure"]), 2),
            }
        )

    return trend