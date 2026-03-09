"""Test configuration for local unit tests.

This avoids importing the integration package __init__ (which requires
Home Assistant runtime dependencies) when testing pure helper modules.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
INTEGRATION_DIR = CUSTOM_COMPONENTS / "tech_recuperation"


if "custom_components" not in sys.modules:
    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [str(CUSTOM_COMPONENTS)]
    sys.modules["custom_components"] = custom_components_pkg

if "custom_components.tech_recuperation" not in sys.modules:
    integration_pkg = types.ModuleType("custom_components.tech_recuperation")
    integration_pkg.__path__ = [str(INTEGRATION_DIR)]
    sys.modules["custom_components.tech_recuperation"] = integration_pkg
