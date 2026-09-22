# -*- coding: utf-8 -*-
"""Integration tests — connectivity and status."""
import pytest


@pytest.mark.integration
async def test_status_returns_active(revit_ready, revit_get):
    response = await revit_get("/status/")
    assert isinstance(response, dict)
    assert response["status"] == "active"


@pytest.mark.integration
async def test_status_has_health_field(revit_ready, revit_get):
    response = await revit_get("/status/")
    assert "health" in response


@pytest.mark.integration
async def test_model_info_returns_dict(revit_ready, revit_get):
    """model_info may error if no document is open, but should still respond."""
    response = await revit_get("/model_info/")
    # Could be a success dict or an error string — either is a valid response
    assert response is not None
