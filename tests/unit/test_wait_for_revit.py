# -*- coding: utf-8 -*-
"""Tests for _wait_for_revit_ready with mocked async calls."""
import pytest
from unittest.mock import AsyncMock, patch
from tools.launch_tools import _wait_for_revit_ready


@patch("tools.launch_tools.anyio.sleep", new_callable=AsyncMock)
async def test_immediate_ready(mock_sleep):
    """Revit responds on first poll."""
    mock_get = AsyncMock(return_value={"status": "active", "health": "healthy"})
    ready, response = await _wait_for_revit_ready(mock_get, ctx=None, timeout=30)

    assert ready is True
    assert response["status"] == "active"
    mock_sleep.assert_not_called()


@patch("tools.launch_tools.anyio.sleep", new_callable=AsyncMock)
async def test_ready_after_retries(mock_sleep):
    """Revit fails twice then responds."""
    mock_get = AsyncMock(
        side_effect=[
            ConnectionError("refused"),
            ConnectionError("refused"),
            {"status": "active"},
        ]
    )
    ready, response = await _wait_for_revit_ready(
        mock_get, ctx=None, timeout=60, poll_interval=1
    )

    assert ready is True
    assert response == {"status": "active"}
    assert mock_sleep.call_count == 2


@patch("tools.launch_tools.anyio.sleep", new_callable=AsyncMock)
async def test_503_means_ready(mock_sleep):
    """An HTTP 503 string response means Revit is up but has no document."""
    mock_get = AsyncMock(return_value="Error: 503 - Service Unavailable")
    ready, response = await _wait_for_revit_ready(mock_get, ctx=None, timeout=30)

    assert ready is True
    assert response == {"status": "active_no_document"}


@patch("time.time")
@patch("tools.launch_tools.anyio.sleep", new_callable=AsyncMock)
async def test_timeout(mock_sleep, mock_time):
    """Revit never responds — returns False after timeout."""
    # Simulate time progressing past the timeout
    # _wait_for_revit_ready does `import time` locally, so we patch the
    # global time module.  Calls: start=time(), while: time()-start<timeout
    mock_time.side_effect = [0, 0, 5, 5, 11, 11]
    mock_get = AsyncMock(side_effect=ConnectionError("refused"))

    ready, response = await _wait_for_revit_ready(
        mock_get, ctx=None, timeout=10, poll_interval=5
    )

    assert ready is False
    assert response is None
