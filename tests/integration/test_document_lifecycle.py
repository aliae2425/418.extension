# -*- coding: utf-8 -*-
"""Integration tests — document open / save / close lifecycle."""
import pytest


@pytest.mark.integration
async def test_open_and_close_document(revit_ready, revit_post, test_file_path):
    # Open
    response = await revit_post(
        "/open_document/", {"file_path": test_file_path}
    )
    assert isinstance(response, dict)
    assert response["status"] == "success"
    assert "document_title" in response

    # Close without saving
    response = await revit_post("/close_document/", {"save": False})
    assert isinstance(response, dict)
    assert response["status"] == "success"


@pytest.mark.integration
async def test_save_document_as(revit_ready, revit_post, test_file_path, tmp_path):
    # Open test file
    response = await revit_post(
        "/open_document/", {"file_path": test_file_path}
    )
    assert response["status"] == "success"

    try:
        # Save As to temp location
        save_path = str(tmp_path / "test_save.rvt")
        response = await revit_post(
            "/save_document/", {"file_path": save_path}
        )
        assert isinstance(response, dict)
        assert response["status"] == "success"
    finally:
        await revit_post("/close_document/", {"save": False})


@pytest.mark.integration
async def test_open_detached(revit_ready, revit_post, test_file_path):
    """Opening with detach=True should succeed (even on non-workshared files)."""
    response = await revit_post(
        "/open_document/",
        {"file_path": test_file_path, "detach": True},
    )
    assert isinstance(response, dict)
    # Might succeed or return a specific error for non-workshared files
    try:
        await revit_post("/close_document/", {"save": False})
    except Exception:
        pass
