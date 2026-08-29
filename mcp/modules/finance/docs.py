"""
mcp/modules/finance/docs.py — Documented expected behaviors and business rules for Finance.
"""

from typing import Any


def get_expected_behaviors() -> dict[str, Any]:
    """Return specification behaviors for Finance & Purchase Module."""
    return {
        "expected_behaviors": {
            "purchase_order_creation": {
                "description": "Create a new purchase transaction or supplier order.",
                "mandatory_fields": ["supplier_name", "items", "amount"],
                "expected_outcome": "Purchase record saved with ledger entry.",
            },
            "invoice_validation": {
                "description": "Validate tax calculations and invoice totals.",
                "expected_outcome": "Subtotal + Tax equals total amount strictly.",
            },
            "payment_recording": {
                "description": "Record payment against open purchase or invoices.",
                "expected_outcome": "Balance updated and payment receipt logged.",
            },
        },
        "business_rules": [
            "Total amount must be greater than zero.",
            "Invoices with pending reconciliation cannot be closed.",
            "Currency precision must adhere to system financial settings (2 decimal places).",
        ],
    }
