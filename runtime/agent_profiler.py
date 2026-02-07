import os
import logging
from pathlib import Path
from typing import List, Dict
import yaml
import mistune
from pydantic import BaseModel, Field, ValidationError

from runtime.artifact_factory import ArtifactSchema
from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


# --------------------------------------------------------------------------------------------------
# AgentOutput: Immutable compiled agent output
# --------------------------------------------------------------------------------------------------
class AgentOutput(BaseModel):
    agent: str
    task_id: str
    artifact_patch: Dict | None
    artifact_is_valid: bool
    issues: List[str] = []

# --------------------------------------------------------------------------------------------------
# AgentProfile: static properties of the agent: capabilities, roles, permissions, tools, expertise.
# --------------------------------------------------------------------------------------------------
class AgentProfile(BaseModel):
    name: str = Field(..., description="Unique agent identifier")
    role: str = Field(..., description="Human-readable role of the agent")
    description: str = Field(..., description="One-paragraph explanation of the agent")
    capabilities: List[str] = Field(default_factory=list)
    can_mutate_artifact: bool = False
    can_mutate_data: bool = False
    can_execute_tools: bool = False
    task_style: str = Field(..., description="Primary cognitive mode of the agent")
    expected_outputs: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    authority_notes: List[str] = Field(default_factory=list)
    max_iterations: int | None = None
    requires_human_approval: bool = False
    context_placeholder: str = "{conversation_history}"
    task_placeholder: str = "{task}"
    input_schema: dict = {}
    output_schema: dict = {}

    class Config:
        frozen = True  # Immutable at runtime


# -----------------------------------------------------------------------------
# AgentProfiler
# -----------------------------------------------------------------------------
class AgentProfiler:
    """
    Production-grade compiler of AGENT.md files into AgentProfile objects.

    Responsibilities:
    - Parses all AGENT.md files in a directory
    - Validates structure and types
    - Converts Markdown/YAML into Pydantic AgentProfile
    - Writes compiled `profile.py` for runtime import
    """

    # -------------------------------------------------------------------------
    # Parse a single AGENT.md and produce AgentProfile
    # -------------------------------------------------------------------------
    @staticmethod
    def _compile_md(md_text: str, input_schema: dict, output_schema: dict) -> AgentProfile:

        logger.info("About to compile md ...")

        # Convert Markdown to YAML-like structure using mistune
        md_ast = mistune.create_markdown(renderer=None)
        ast = md_ast(md_text)

        # Convert AST to dict (assume YAML frontmatter style or key: value blocks)
        data = AgentProfiler._ast_to_dict(ast)

        # Add Input and Output Schema
        data["input_schema"] = input_schema
        data["output_schema"] = output_schema

        logger.info(f"Raw Data parsed: {data}")

        # Validate using Pydantic
        try:
            profile = AgentProfile(**data)
        except ValidationError as e:
            raise ValueError(f"Validation failed for agent profile: {e}")

        return profile

    @staticmethod
    def _extract_text(node) -> str:
        """Helper to safely extract text from children or raw attributes."""
        # Check for 'raw' first as per your AST dump
        if "raw" in node:
            return node["raw"]
        # Fallback for other mistune versions
        if "text" in node:
            return node["text"]
        if "children" in node:
            return "".join([AgentProfiler._extract_text(child) for child in node["children"]])
        return ""

    # -------------------------------------------------------------------------
    # Convert Markdown AST into dict
    # -------------------------------------------------------------------------
    @staticmethod
    def _ast_to_dict(ast_nodes: list) -> dict:
        result: dict = {}
        current_key = None

        # Mapping of Markdown Header text to Pydantic Field Names
        header_map = {
            "name": "name",
            "role": "role",
            "description": "description",
            "capabilities": "capabilities",
            "judgement_/_task_style": "task_style",
            "expected_outputs": "expected_outputs",
            "forbidden_actions": "forbidden_actions",
            "max_iterations": "max_iterations",
            "human_approval_required": "requires_human_approval",
            # Add Authority if you want to map it to a specific field
            "authority": "authority_notes",
            "context_placeholder" : "context_placeholder",
            "task_placeholder" : "task_placeholder",
            "schema" : "schema"
        }

        for node in ast_nodes:
            ntype = node.get("type")
            text = AgentProfiler._extract_text(node).strip()
            
            # Skip the decoration lines (#######)
            if not text or text.startswith("#"):
                continue

            if ntype == "heading":
                raw_key = text.rstrip(":").lower().replace(" ", "_")
                # Map the header to the Pydantic field name
                current_key = header_map.get(raw_key)
                continue

            if current_key:
                if ntype == "paragraph":
                    val = text if text != "None" else None

                    # --- SPECIAL HANDLING FOR FIELDS WITH COMMENTS ---
                    # We want to strip out everything after the first word for specific fields
                    # This turns "2 (to ensure...)" -> "2" 
                    # And "True (for high risk)" -> "True"
                    fields_to_strip = ["requires_human_approval", "max_iterations"]

                    if current_key in fields_to_strip and val:
                        # Split by space and take the first part, then clean up punctuation
                        val = val.split()[0].strip().rstrip(',').rstrip(';').rstrip('.')

                        if not val or val.lower() == "none":
                            if current_key == "max_iterations":
                                result[current_key] = None
                            else:
                                result[current_key] = False
                            continue
                    
                    result[current_key] = AgentProfiler._convert_value(val) if val else None
                
                elif ntype == "list":
                    items = []
                    for item in node.get("children", []):
                        # List items in AST often have nested 'block_text' or 'text'
                        item_text = AgentProfiler._extract_text(item).strip()
                        if item_text:
                            items.append(item_text)
                    result[current_key] = items
                
                elif ntype == "block_code":
                    # Code blocks usually store the string in 'raw'
                    result[current_key] = node.get("raw", "").strip()

        return result

    # -------------------------------------------------------------------------
    # Convert string to bool/int if applicable
    # -------------------------------------------------------------------------
    @staticmethod
    def _convert_value(val: str):
        if not val:
            return None
        
        # Clean up the string for boolean check
        clean_val = val.lower().strip()
        
        if clean_val in ("true", "yes", "1"):
            return True
        if clean_val in ("false", "no", "0"):
            return False
            
        # Return as is for strings/numbers, or try numeric conversion
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    # -------------------------------------------------------------------------
    # Retrieve Schema
    # -------------------------------------------------------------------------
    @staticmethod
    def _load_schema(schema_path: str) -> dict:
        try:
            with open(schema_path, "r") as f:
                schema = yaml.safe_load(f)
                AgentProfiler.validate_schema_integrity(schema)

            return {
                "success": True,
                "schema": schema,
                "error": None,
            }

        except FileNotFoundError:
            return {
                "success": False,
                "schema": None,
                "error": f"Schema file not found: {schema_path}",
            }

        except Exception as e:
            return {
                "success": False,
                "schema": None,
                "error": f"Failed to load schema: {str(e)}",
            }

    # -------------------------------------------------------------------------
    # Validate Integrity of schema.
    # -------------------------------------------------------------------------
    @staticmethod
    def validate_schema_integrity(schema: Dict[str, Any], path: str = "root", definitions: Optional[Dict[str, Any]] = None):
        """
        Scans a YAML schema for broken $refs or missing 'type' keys 
        that cause Pydantic construction failures.
        """
        if definitions is None:
            definitions = schema.get("definitions", {})

        # 1. Check for missing type or ref at current level
        s_type = schema.get("type")
        s_ref = schema.get("$ref")

        if not s_type and not s_ref:
            logger.error(f"ERROR: Field at '{path}' has no 'type' and no '$ref'.")
            return False

        # 2. Validate $ref resolution
        if s_ref:
            ref_key = s_ref.split("/")[-1]
            if ref_key not in definitions:
                logger.error(f"ERROR: Broken Reference at '{path}'. '{ref_key}' not found in definitions.")
                return False
            # Recurse into the definition using the same definitions dict
            return AgentProfiler.validate_schema_integrity(definitions[ref_key], f"{path} -> {ref_key}", definitions)

        # 3. Recurse into Objects
        if s_type == "object":
            props = schema.get("properties", {})
            if not props and not schema.get("additionalProperties"):
                logger.warning(f"WARNING: Object at '{path}' has no properties defined.")

            for prop_name, prop_schema in props.items():
                AgentProfiler.validate_schema_integrity(prop_schema, f"{path}.{prop_name}", definitions)

        # 4. Recurse into Arrays
        elif s_type == "array":
            items = schema.get("items")
            if not items:
                logger.error(f"ERROR: Array at '{path}' is missing 'items' definition.")
                return False
            AgentProfiler.validate_schema_integrity(items, f"{path}[]", definitions)

        return True

