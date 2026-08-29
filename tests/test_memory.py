"""
tests/test_memory.py — Tests for Persistent Module Memory Store.
"""

import pytest
from agent.memory_store import ModuleMemoryStore


def test_module_memory_initialization():
    store = ModuleMemoryStore("sales")
    assert store.doc_status == "UNDOCUMENTED"
    assert store.module_key == "sales"

    audit_store = ModuleMemoryStore("audit")
    assert audit_store.doc_status == "DOCUMENTED"


def test_record_and_persist_discrepancy():
    store = ModuleMemoryStore("audit")
    initial_count = len(store.state.get("discrepancies", []))

    store.record_discrepancy(
        title="Test Discrepancy",
        documented_expectation="Audit history should have no edit button",
        actual_behavior="Edit button is visible",
    )

    # Reload from disk
    reloaded = ModuleMemoryStore("audit")
    assert len(reloaded.state.get("discrepancies", [])) == initial_count + 1
    latest = reloaded.state.get("discrepancies", [])[-1]
    assert latest["title"] == "Test Discrepancy"


def test_record_api_call():
    store = ModuleMemoryStore("inventory")
    store.record_api_call(method="POST", url="/api/v1/items", status=201, action="Add Item")
    apis = [a["url"] for a in store.state.get("apis", [])]
    assert "/api/v1/items" in apis
