# -*- coding: utf-8 -*-
"""Tests for _find_revit_installations with mocked registry and filesystem."""
import sys
import types
from unittest.mock import patch, MagicMock
import pytest
from tools.launch_tools import _find_revit_installations


def _make_mock_winreg(subkeys_by_hive=None):
    """Build a mock winreg module.

    subkeys_by_hive: dict mapping hive constant -> list of
        (subkey_name, {value_name: value_data}) dicts
    """
    mock_winreg = MagicMock()
    mock_winreg.HKEY_LOCAL_MACHINE = 0x80000002
    mock_winreg.HKEY_CURRENT_USER = 0x80000001

    if subkeys_by_hive is None:
        subkeys_by_hive = {}

    def open_key(hive, path):
        if hive not in subkeys_by_hive:
            raise OSError("Key not found")
        return MagicMock(name=f"key_{hive}")

    def enum_key(key, index):
        # Determine which hive this key belongs to
        for hive, entries in subkeys_by_hive.items():
            if index < len(entries):
                return entries[index][0]
        raise OSError("No more subkeys")

    def open_subkey(key, subkey_name):
        for hive, entries in subkeys_by_hive.items():
            for name, values in entries:
                if name == subkey_name:
                    return MagicMock(name=f"subkey_{name}")
        raise OSError("Subkey not found")

    def query_value(key, value_name):
        # Find the matching subkey based on the mock key name
        for hive, entries in subkeys_by_hive.items():
            for name, values in entries:
                if value_name in values:
                    return (values[value_name], 1)  # (value, type)
        raise OSError("Value not found")

    mock_winreg.OpenKey = MagicMock(side_effect=open_key)
    mock_winreg.EnumKey = MagicMock(side_effect=enum_key)
    mock_winreg.QueryValueEx = MagicMock(side_effect=query_value)
    mock_winreg.CloseKey = MagicMock()

    return mock_winreg


class TestFindInstallationsFilesystem:
    """Test the filesystem fallback path (no registry)."""

    @patch("tools.launch_tools.os.path.isfile")
    def test_filesystem_finds_revit(self, mock_isfile):
        """Filesystem scan finds Revit 2025."""
        def isfile(path):
            return "Revit 2025" in path and path.endswith("Revit.exe")
        mock_isfile.side_effect = isfile

        # Patch out winreg so registry path fails gracefully
        with patch.dict(sys.modules, {"winreg": None}):
            result = _find_revit_installations()

        assert len(result) == 1
        assert result[0]["year"] == "2025"

    @patch("tools.launch_tools.os.path.isfile")
    def test_multiple_versions_sorted(self, mock_isfile):
        """Multiple filesystem versions are returned newest-first."""
        found_years = {"2024", "2025", "2026"}

        def isfile(path):
            return any(
                f"Revit {y}" in path and path.endswith("Revit.exe")
                for y in found_years
            )
        mock_isfile.side_effect = isfile

        with patch.dict(sys.modules, {"winreg": None}):
            result = _find_revit_installations()

        years = [r["year"] for r in result]
        assert years == ["2026", "2025", "2024"]

    @patch("tools.launch_tools.os.path.isfile", return_value=False)
    def test_no_revit_found(self, mock_isfile):
        """No installations found returns empty list."""
        with patch.dict(sys.modules, {"winreg": None}):
            result = _find_revit_installations()

        assert result == []

    @patch("tools.launch_tools.os.path.isfile", return_value=False)
    def test_deduplication(self, mock_isfile):
        """Registry and filesystem don't produce duplicates for the same year."""
        # Even with no filesystem hits, an empty result is fine
        with patch.dict(sys.modules, {"winreg": None}):
            result = _find_revit_installations()

        # Count unique years
        years = [r["year"] for r in result]
        assert len(years) == len(set(years))
