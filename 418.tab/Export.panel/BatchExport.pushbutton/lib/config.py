# -*- coding: utf-8 -*-
"""Facade: expose UserConfigStore from core.config for backward compatibility."""

from .core.config import UserConfigStore  # re-export

__all__ = ["UserConfigStore"]


