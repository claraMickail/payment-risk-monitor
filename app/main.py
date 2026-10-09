from fastapi import FastAPI, HTTPException

from app.analytics import get_category_risk, get_overview_metrics, get_top_risky_merchants


app = FastAPI(
    title="Payment Risk Monitor API",
    description="API for payment-risk analytics from BankSim transaction data.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API is running."""
    return {"status": "ok"}


@app.get("/metrics/overview")
def overview_metrics(
    import_run_id: int | None = None,
) -> dict[str, int | float]:
    """Return high-level payment-risk KPIs for one import batch."""
    metrics = get_overview_metrics(import_run_id)

    if metrics is None:
        raise HTTPException(
            status_code=404,
            detail="No import data is available yet.",
        )

    return metrics

@app.get("/metrics/categories")
def category_risk(
    import_run_id: int | None = None,
) -> list[dict[str, str | int | float]]:
    """Return payment-risk KPIs grouped by transaction category."""
    return get_category_risk(import_run_id)

@app.get("/metrics/merchants")
def top_risky_merchants(
    import_run_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, str | int | float]]:
    """Return merchants with the highest flagged-payment value."""
    return get_top_risky_merchants(
        import_run_id,
        limit=limit,
    )