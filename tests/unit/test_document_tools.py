# -*- coding: utf-8 -*-
"""Tests for document tool wrappers — verify correct payloads."""
import pytest
from unittest.mock import AsyncMock
from tools.document_tools import register_document_tools


@pytest.fixture
def doc_tools(mock_mcp, mock_revit_get, mock_revit_post):
    """Register document tools and return the captured tool functions."""
    mock_revit_post.return_value = {"status": "success", "message": "OK"}
    register_document_tools(mock_mcp, mock_revit_get, mock_revit_post)
    return mock_mcp.tools


class TestOpenDocument:
    async def test_open_sends_correct_payload(self, doc_tools, mock_revit_post):
        await doc_tools["open_document"](
            ctx=None, file_path="C:/test.rvt"
        )
        mock_revit_post.assert_called_once_with(
            "/open_document/",
            {"file_path": "C:/test.rvt", "detach": False, "audit": False},
            None,
            timeout=120.0,
        )

    async def test_open_detach_flag(self, doc_tools, mock_revit_post):
        await doc_tools["open_document"](
            ctx=None, file_path="C:/test.rvt", detach=True
        )
        call_data = mock_revit_post.call_args[0][1]
        assert call_data["detach"] is True

    async def test_open_audit_flag(self, doc_tools, mock_revit_post):
        await doc_tools["open_document"](
            ctx=None, file_path="C:/test.rvt", audit=True
        )
        call_data = mock_revit_post.call_args[0][1]
        assert call_data["audit"] is True


class TestCloseDocument:
    async def test_close_default_no_save(self, doc_tools, mock_revit_post):
        await doc_tools["close_document"](ctx=None)
        mock_revit_post.assert_called_once_with(
            "/close_document/", {"save": False}, None
        )

    async def test_close_with_save(self, doc_tools, mock_revit_post):
        await doc_tools["close_document"](ctx=None, save=True)
        call_data = mock_revit_post.call_args[0][1]
        assert call_data["save"] is True


class TestSaveDocument:
    async def test_save_in_place(self, doc_tools, mock_revit_post):
        await doc_tools["save_document"](ctx=None)
        mock_revit_post.assert_called_once_with(
            "/save_document/", {"file_path": None}, None
        )

    async def test_save_as(self, doc_tools, mock_revit_post):
        await doc_tools["save_document"](ctx=None, file_path="new.rvt")
        call_data = mock_revit_post.call_args[0][1]
        assert call_data["file_path"] == "new.rvt"


class TestSyncWithCentral:
    async def test_sync_defaults(self, doc_tools, mock_revit_post):
        await doc_tools["sync_with_central"](ctx=None)
        mock_revit_post.assert_called_once_with(
            "/sync_with_central/",
            {"comment": "", "compact": False, "relinquish_all": True},
            None,
            timeout=120.0,
        )

    async def test_sync_custom(self, doc_tools, mock_revit_post):
        await doc_tools["sync_with_central"](
            ctx=None, comment="test", compact=True, relinquish_all=False
        )
        call_data = mock_revit_post.call_args[0][1]
        assert call_data["comment"] == "test"
        assert call_data["compact"] is True
        assert call_data["relinquish_all"] is False
