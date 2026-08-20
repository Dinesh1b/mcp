"""
tests/test_rag.py — Tests for Doc Crawler and RAG Retriever.
"""

import pytest
from knowledge.doc_crawler import DocCrawler, clean_html, extract_title
from knowledge.rag_retriever import RAGRetriever


def test_clean_html():
    html = "<div><h1>Title</h1><p>Description with <a href='#'>link</a>.</p><script>var x=1;</script></div>"
    cleaned = clean_html(html)
    assert "Title" in cleaned
    assert "Description with link" in cleaned
    assert "var x=1" not in cleaned


def test_extract_title():
    html = "<html><head><title>Inventory Guide | Stockount</title></head><body><h1>Inventory Guide</h1></body></html>"
    assert extract_title(html) == "Inventory Guide"


def test_coverage_status_documented():
    retriever = RAGRetriever()
    cov_audit = retriever.get_coverage_status("audit")
    assert cov_audit["status"] == "DOCUMENTED"

    cov_inv = retriever.get_coverage_status("inventory")
    assert cov_inv["status"] == "DOCUMENTED"


def test_coverage_status_undocumented():
    retriever = RAGRetriever()
    cov_sales = retriever.get_coverage_status("sales")
    assert cov_sales["status"] == "UNDOCUMENTED"

    cov_purchases = retriever.get_coverage_status("purchases")
    assert cov_purchases["status"] == "UNDOCUMENTED"

    cov_reports = retriever.get_coverage_status("reports")
    assert cov_reports["status"] == "UNDOCUMENTED"


def test_retrieve_relevant_chunks():
    retriever = RAGRetriever()
    prompt = retriever.build_reference_context_prompt("Create Audit Plan", module_name="audit")
    assert "DOCUMENTED" in prompt
    assert "audit" in prompt.lower()
