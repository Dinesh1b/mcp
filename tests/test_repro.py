"""
tests/test_repro.py — Tests for Reproduction Engine.
"""

import pytest
from agent.repro_engine import ReproductionEngine


def test_parse_sequence():
    engine = ReproductionEngine()
    sequence = "Create Audit Plan -> Perform Audit -> Verify Audit History"
    plan = engine.parse_input(sequence)

    assert plan["module"] == "audit"
    assert plan["doc_status"] == "DOCUMENTED"
    assert len(plan["scenarios"]) == 3
    assert plan["scenarios"][0]["title"] == "Create Audit Plan"
    assert plan["scenarios"][2]["title"] == "Verify Audit History"


def test_parse_undocumented_sequence():
    engine = ReproductionEngine()
    sequence = "Open Sales -> Click New Order -> Submit"
    plan = engine.parse_input(sequence)

    assert plan["module"] == "sales"
    assert plan["doc_status"] == "UNDOCUMENTED"
    assert plan["scenarios"][0]["doc_status"] == "UNDOCUMENTED"
    assert "Observe" in plan["scenarios"][0]["expected_result"]


def test_parse_plain_text():
    engine = ReproductionEngine()
    plan = engine.parse_input("Test Item Group and Item creation in Inventory")
    assert plan["module"] == "inventory"
    assert plan["doc_status"] == "DOCUMENTED"
