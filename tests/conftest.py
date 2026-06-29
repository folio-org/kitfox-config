"""Shared test fixtures. CONFIG_ROOT is the kitfox-config repo; PLATFORM_LSP is
the sibling descriptor source. Both are located WITHOUT resolving symlinks so the
workspace symlinks (kitfox-config, platform-lsp) are followed correctly."""

from pathlib import Path

import pytest

# tests/conftest.py -> parents[1] = kitfox-config, parents[2] = workspace root.
CONFIG_ROOT = Path(__file__).parents[1]
WORKSPACE = Path(__file__).parents[2]
PLATFORM_LSP = WORKSPACE / "platform-lsp"
PLATFORM_DESCRIPTOR = PLATFORM_LSP / "platform-descriptor.json"
APP_DESCRIPTORS = PLATFORM_LSP / "local-dev" / "appDescriptors"


@pytest.fixture
def config_root() -> Path:
    return CONFIG_ROOT


@pytest.fixture
def platform_descriptor() -> Path:
    return PLATFORM_DESCRIPTOR


@pytest.fixture
def app_descriptors_dir() -> Path:
    return APP_DESCRIPTORS
