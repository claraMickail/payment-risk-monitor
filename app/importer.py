import csv
import math
from dataclasses import dataclass
from pathlib import Path
from app.database import (
    complete_import_run,
    create_import_run,
    initialize_database,
    insert_transactions,
)


# BankSim fields needed
# I deliberately do not use age, gender, or postal-code fields.
REQUIRED_COLUMNS = {
    "step",
    "customer",
    "merchant",
    "category",
    "amount",
    "fraud",
}

# (source_row, step, customer_id, merchant_id, category, amount, is_fraud)
TransactionRecord = tuple[int, int, str, str, str, float, int]


@dataclass
class ValidationResult:
    """The clean records and rejected rows from one CSV validation run."""

    valid_records: list[TransactionRecord]
    rejected_rows: list[str]

    @property
    def rows_received(self) -> int:
        return len(self.valid_records) + len(self.rejected_rows)

    @property
    def rows_loaded(self) -> int:
        return len(self.valid_records)

    @property
    def rows_rejected(self) -> int:
        return len(self.rejected_rows)

def clean_text(value: str | None) -> str:
    """Remove whitespace and BankSim's surrounding single quotes."""
    return (value or "").strip().strip("'")

def validate_csv_headers(fieldnames: list[str] | None) -> None:
    """Confirm that the input file has every column needed."""
    available_columns = set(fieldnames or [])
    missing_columns = REQUIRED_COLUMNS - available_columns

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required column(s): {missing_text}")


def parse_transaction(
    row: dict[str, str],
    source_row: int,
) -> TransactionRecord:
    """Validate one CSV row and return its cleaned transaction record."""
    customer_id = clean_text(row.get("customer"))
    merchant_id = clean_text(row.get("merchant"))
    category = clean_text(row.get("category"))

    try:
        step = int(row.get("step") or "")
        amount = float(row.get("amount") or "")
        is_fraud = int(row.get("fraud") or "")
    except ValueError as error:
        raise ValueError("step, amount, or fraud is not a valid number") from error

    if not customer_id or not merchant_id or not category:
        raise ValueError("customer, merchant, and category must not be blank")

    if step < 0:
        raise ValueError("step must be zero or greater")

    if not math.isfinite(amount) or amount < 0:
        raise ValueError("amount must be a finite value of zero or greater")

    if is_fraud not in (0, 1):
        raise ValueError("fraud must be either 0 or 1")

    return (source_row, step, customer_id, merchant_id, category, amount, is_fraud)

def validate_csv(
    csv_path: Path,
    max_rows: int | None = None,
) -> ValidationResult:
    """
    Read a BankSim CSV and separate valid transaction records from bad rows.

    max_rows lets us test safely on a small slice before importing the full file.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if max_rows is not None and max_rows <= 0:
        raise ValueError("max_rows must be greater than zero")

    valid_records: list[TransactionRecord] = []
    rejected_rows: list[str] = []
    processed_rows = 0

    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        validate_csv_headers(reader.fieldnames)

        for source_row, row in enumerate(reader, start=2):
            if max_rows is not None and processed_rows >= max_rows:
                break

            processed_rows += 1

            try:
                valid_records.append(parse_transaction(row, source_row))
            except ValueError as error:
                rejected_rows.append(f"Row {source_row}: {error}")

    return ValidationResult(
        valid_records=valid_records,
        rejected_rows=rejected_rows,
    )

def import_csv(
    csv_path: Path,
    max_rows: int | None = None,
) -> ValidationResult:
    """Validate a BankSim CSV, store it in SQLite, and return the result."""
    result = validate_csv(csv_path, max_rows=max_rows)

    initialize_database()

    import_run_id = create_import_run(
        source_name=csv_path.name,
        rows_received=result.rows_received,
    )

    insert_transactions(
        import_run_id=import_run_id,
        records=result.valid_records,
    )

    complete_import_run(
        import_run_id=import_run_id,
        rows_loaded=result.rows_loaded,
        rows_rejected=result.rows_rejected,
    )

    return result