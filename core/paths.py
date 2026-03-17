import os
from pathlib import Path


# This file lives inside agentic_system/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

############### BOOTSTRAP and RUNTIME  ###############
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
BOOTSTRAP_ROOT = RUNTIME_ROOT / "bootstrap"
GLOBAL_CONFIG_PATH = BOOTSTRAP_ROOT / "config.json"

############### DOMAIN CLASSIFICATION  ###############

DOMAIN_ROOT = PROJECT_ROOT / "domain"
WORKSPACES_ROOT = PROJECT_ROOT / "workspaces"
TEMPLATE_ROOT = RUNTIME_ROOT / "domain_repo" / "templates"

############### PROMPT TEMPLATES ############### 

PLAN_TEMPLATE = TEMPLATE_ROOT / "PLAN_TEMPLATE.md"
HITL_TEMPLATE = TEMPLATE_ROOT / "HITL_TEMPLATE.md"
REFINER_TEMPLATE = TEMPLATE_ROOT / "REFINER_TEMPLATE.md"
ARCHITECT_TEMPLATE = TEMPLATE_ROOT / "ARCHITECT_TEMPLATE.md"
SKILL_TEMPLATE = TEMPLATE_ROOT / "SKILL_TEMPLATE.md"


############### LOAD TEMPLATES ############### 

def load_template(template: Path):

    if not os.path.exists(template):
        logger.debug(f"Template: {template} not found.")
        raise FileNotFoundError(f"Template: {template} not found.")

    with open(template, 'r') as f:
        content = f.read()

    return content

