# -*- coding: utf-8 -*-
"""Tests for tools.utils.format_response()"""
import json
import pytest
from tools.utils import format_response


class TestSuccessResponses:
    def test_success_with_output(self):
        result = format_response({"status": "success", "output": "hello"})
        assert result == "hello"

    def test_success_with_message(self):
        result = format_response({"status": "success", "message": "Done"})
        assert result == "Done"

    def test_success_with_result(self):
        result = format_response({"status": "success", "result": 42})
        assert result == "42"

    def test_success_with_data(self):
        result = format_response({"status": "success", "data": [1, 2]})
        assert result == "[1, 2]"

    def test_success_fallback_json(self):
        resp = {"status": "success"}
        result = format_response(resp)
        assert json.loads(result) == resp

    def test_priority_output_over_message(self):
        result = format_response(
            {"status": "success", "output": "A", "message": "B"}
        )
        assert result == "A"


class TestActiveStatusResponses:
    def test_active_healthy_status(self):
        resp = {
            "status": "active",
            "health": "healthy",
            "document_title": "Test",
        }
        result = format_response(resp)
        assert "=== REVIT STATUS ===" in result
        assert "Document: Test" in result

    def test_active_revit_available(self):
        resp = {"status": "active", "revit_available": True}
        result = format_response(resp)
        assert "=== REVIT STATUS ===" in result
        assert "Revit Available: True" in result

    def test_active_healthy_with_api_name(self):
        resp = {
            "status": "active",
            "health": "healthy",
            "api_name": "RevitMCP",
        }
        result = format_response(resp)
        assert "API: RevitMCP" in result


class TestErrorResponses:
    def test_error_response(self):
        result = format_response({"status": "error", "error": "fail"})
        assert "=== ERROR DETAILS ===" in result
        assert "Error: fail" in result

    def test_error_with_traceback(self):
        result = format_response(
            {"error": "fail", "traceback": "line 1\nline 2"}
        )
        assert "=== TRACEBACK ===" in result
        assert "line 1" in result

    def test_error_with_details(self):
        result = format_response(
            {"status": "error", "error": "fail", "details": "more info"}
        )
        assert "Details: more info" in result

    def test_error_with_debug_fields(self):
        result = format_response(
            {
                "status": "error",
                "error": "fail",
                "code_attempted": "print(1)",
                "endpoint": "/test/",
            }
        )
        assert "Code Attempted: print(1)" in result
        assert "Endpoint: /test/" in result


class TestStringPassthrough:
    def test_string_passthrough(self):
        result = format_response("Error: connection refused")
        assert result == "Error: connection refused"

    def test_empty_string(self):
        result = format_response("")
        assert result == ""

    def test_non_string_non_dict(self):
        result = format_response(123)
        assert result == "123"
