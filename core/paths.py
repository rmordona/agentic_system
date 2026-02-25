from pathlib import Path

# This file lives inside agentic_system/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

RUNTIME_ROOT = PROJECT_ROOT / "runtime"
BOOTSTRAP_ROOT = RUNTIME_ROOT / "bootstrap"
WORKSPACES_ROOT = PROJECT_ROOT / "workspaces"
GLOBAL_CONFIG_PATH = BOOTSTRAP_ROOT / "config.json"

TEMPLATE_ROOT = RUNTIME_ROOT / "domain_repo" / "templates"

