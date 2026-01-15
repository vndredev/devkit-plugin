"""Pytest configuration and shared fixtures."""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project structure with config."""
    # Create .claude/.devkit directory
    config_dir = tmp_path / ".claude" / ".devkit"
    config_dir.mkdir(parents=True)

    # Create minimal config
    config = {
        "project": {"name": "test-project", "type": "python"},
        "hooks": {"session": {"enabled": True}},
        "git": {"protected_branches": ["main"]},
        "arch": {"layers": {"core": {"tier": 0}, "lib": {"tier": 1}}},
    }
    (config_dir / "config.json").write_text(json.dumps(config, indent=2))

    return tmp_path


@pytest.fixture
def sample_config():
    """Return a sample config dict for testing."""
    return {
        "project": {
            "name": "test-project",
            "type": "python",
            "slogan": "Test slogan",
        },
        "hooks": {
            "session": {"enabled": True, "show_git_status": True},
            "validate": {"enabled": True, "block_force_push": True},
        },
        "git": {
            "protected_branches": ["main", "develop"],
            "conventions": {
                "types": ["feat", "fix", "chore"],
                "scopes": {
                    "mode": "strict",
                    "allowed": ["core", "lib"],
                    "internal": ["internal", "ci"],
                },
            },
        },
        "arch": {
            "layers": {
                "core": {"tier": 0},
                "lib": {"tier": 1},
                "events": {"tier": 2},
            }
        },
    }


@pytest.fixture
def mock_git_status():
    """Return sample git status output."""
    return """## main...origin/main
M  src/lib/config.py
 M src/events/validate.py
?? new_file.py
A  staged_file.py"""


@pytest.fixture
def python_source_code():
    """Return sample Python source for import testing."""
    return '''"""Sample module."""

from pathlib import Path
import json
import os

from lib.config import get, load_config
from core.types import ProjectType


def example_function():
    """Example function."""
    pass
'''


@pytest.fixture
def clear_config_cache():
    """Clear config cache before and after test."""
    from lib.config import clear_cache

    clear_cache()
    yield
    clear_cache()
