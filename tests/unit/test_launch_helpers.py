# -*- coding: utf-8 -*-
"""Tests for pure helper functions in tools.launch_tools"""
from tools.launch_tools import _select_revit, _build_launch_command


SAMPLE_INSTALLATIONS = [
    {"year": "2026", "path": "C:/Revit2026/Revit.exe"},
    {"year": "2025", "path": "C:/Revit2025/Revit.exe"},
    {"year": "2024", "path": "C:/Revit2024/Revit.exe"},
]


class TestSelectRevit:
    def test_select_latest(self):
        result = _select_revit(SAMPLE_INSTALLATIONS)
        assert result["year"] == "2026"

    def test_select_specific_version(self):
        result = _select_revit(SAMPLE_INSTALLATIONS, "2025")
        assert result["year"] == "2025"
        assert result["path"] == "C:/Revit2025/Revit.exe"

    def test_select_missing_version(self):
        result = _select_revit(SAMPLE_INSTALLATIONS, "2020")
        assert result is None

    def test_select_empty_list(self):
        result = _select_revit([])
        assert result is None

    def test_select_empty_list_with_version(self):
        result = _select_revit([], "2025")
        assert result is None

    def test_version_as_int_string(self):
        """Version param is cast to str internally."""
        result = _select_revit(SAMPLE_INSTALLATIONS, 2025)
        # The function compares inst["year"] == str(version)
        assert result["year"] == "2025"

    def test_single_installation(self):
        result = _select_revit([{"year": "2025", "path": "/r.exe"}])
        assert result["year"] == "2025"


class TestBuildLaunchCommand:
    def test_basic_command(self):
        result = _build_launch_command("C:/Revit.exe")
        assert result == ["C:/Revit.exe"]

    def test_with_file(self):
        result = _build_launch_command("C:/Revit.exe", file_path="test.rvt")
        assert result == ["C:/Revit.exe", "test.rvt"]

    def test_with_language(self):
        result = _build_launch_command("C:/Revit.exe", language="ENU")
        assert result == ["C:/Revit.exe", "/language", "ENU"]

    def test_with_all_params(self):
        result = _build_launch_command(
            "C:/Revit.exe", file_path="test.rvt", language="FRA"
        )
        assert result == ["C:/Revit.exe", "/language", "FRA", "test.rvt"]

    def test_none_file_and_language(self):
        result = _build_launch_command("C:/Revit.exe", None, None)
        assert result == ["C:/Revit.exe"]
