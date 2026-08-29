"""
mcp/modules/audit/docs.py — Documented expected behaviors and business rules for Audit.
"""

from typing import Any


def get_expected_behaviors() -> dict[str, Any]:
    """Return specification behaviors for Stockount Audit Module."""
    return {
        "expected_behaviors": {
            "create_quick_audit": {
                "description": "User creates a Quick Audit under Manual mode.",
                "mandatory_fields": ["audit_name"],
                "expected_outcome": "Audit record created and user navigated to audit tracker page.",
            },
            "import_stock_sheet": {
                "description": "User imports CSV or Excel stock sheet into audit.",
                "supported_formats": [".csv", ".xlsx"],
                "expected_outcome": "Stock items and expected quantities populated in count table.",
            },
            "stock_counting": {
                "description": "Auditors perform physical inventory count.",
                "counting_modes": ["Search", "Barcode", "Camera"],
                "expected_outcome": "Item count increments accurately; variances calculated.",
            },
            "audit_summary": {
                "description": "View summary of counted vs expected stock quantities.",
                "expected_outcome": "Variance percentage and reconciliation report generated.",
            },
        },
        "business_rules": [
            "Audit name must not be empty.",
            "Auditor must be assigned or created in manual mode before completion.",
            "Discrepancies exceeding variance threshold require manager review.",
        ],
    }
