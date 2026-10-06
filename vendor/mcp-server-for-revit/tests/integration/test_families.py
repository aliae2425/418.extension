# -*- coding: utf-8 -*-
"""Integration tests — family, level, and category tools."""
import pytest


@pytest.mark.integration
async def test_list_levels(revit_ready, revit_get, revit_post, test_file_path):
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        response = await revit_get("/list_levels/")
        assert isinstance(response, dict)
        assert response["status"] == "success"
        assert "levels" in response
    finally:
        await revit_post("/close_document/", {"save": False})


@pytest.mark.integration
async def test_list_families(revit_ready, revit_post, test_file_path):
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        response = await revit_post("/list_families/", {"limit": 10})
        # Route may not be registered in all pyRevit extension versions
        if isinstance(response, str) and "RouteHandlerNotDefined" in response:
            pytest.skip("list_families route not registered in pyRevit extension")
        assert isinstance(response, dict)
        assert response["status"] == "success"
    finally:
        await revit_post("/close_document/", {"save": False})


@pytest.mark.integration
async def test_list_family_categories(revit_ready, revit_get, revit_post, test_file_path):
    await revit_post("/open_document/", {"file_path": test_file_path})
    try:
        response = await revit_get("/list_family_categories/")
        assert isinstance(response, dict)
        assert response["status"] == "success"
    finally:
        await revit_post("/close_document/", {"save": False})
