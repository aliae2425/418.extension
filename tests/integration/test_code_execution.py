# -*- coding: utf-8 -*-
"""Integration tests — code execution round-trip."""
import pytest


@pytest.mark.integration
async def test_execute_simple_code(revit_ready, revit_post, test_file_path):
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        response = await revit_post(
            "/execute_code/",
            {"code": "print(doc.Title)", "description": "Test: print title"},
        )
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert len(response["output"]) > 0
    finally:
        await revit_post("/close_document/", {"save": False})


@pytest.mark.integration
async def test_execute_code_with_error(revit_ready, revit_post, test_file_path):
    """Code that raises should return an error response, not crash."""
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        response = await revit_post(
            "/execute_code/",
            {
                "code": "raise ValueError('test error')",
                "description": "Test: deliberate error",
            },
        )
        # pyRevit returns HTTP 500 for code errors, so the response may be
        # a dict with status="error" or an error string from our HTTP helper.
        if isinstance(response, dict):
            assert response["status"] == "error"
        else:
            assert "error" in response.lower()
            assert "test error" in response
    finally:
        await revit_post("/close_document/", {"save": False})


@pytest.mark.integration
async def test_execute_multi_line_code(revit_ready, revit_post, test_file_path):
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        code = "x = 1\ny = 2\nprint(x + y)"
        response = await revit_post(
            "/execute_code/",
            {"code": code, "description": "Test: multi-line"},
        )
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert "3" in response["output"]
    finally:
        await revit_post("/close_document/", {"save": False})
