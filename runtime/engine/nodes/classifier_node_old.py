################################################################################
# AgentClassifier
################################################################################
# Hierarchical Task Router
#
# Responsible for classifying the refined user intent into one or more
# workspaces (capabilities). This enables the system to route tasks to the
# correct pipeline, planner, or specialized agent stack already defined
# in the workspace folder structure.
#
# Core Responsibilities
# ---------------------
#
# 1. Workspace Classification
#    Map refined user intent to an existing workspace folder (capability).
#
# 2. Deterministic Rule + LLM Fallback
#    Uses rules first; if uncertain, uses LLM classification.
#
# 3. Multi-Workspace Support
#    Handles tasks that span multiple workspaces (e.g., research + trading).
#
# 4. Workspace Metadata Resolution
#    Returns the workspace folder, agent stack, pipeline template, and env vars.
#
################################################################################
from __future__ import annotations
from core.paths import WORKSPACES_ROOT
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path

from runtime.engine.state.state_schema import StateSchema
from runtime.domain_manager import SystemContext
from llm.model_manager import ModelManager
from runtime.engine.stage.stage_manager import StageManager
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class AgentClassifier:

    def __init__(self, llm: ModelManager):

        self.workspace_root = WORKSPACES_ROOT
        self.llm = llm

        # Load all workspace manifests
        self.workspaces = self._discover_workspaces()
        logger.info(f"Discovered workspaces: {list(self.workspaces.keys())}")

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                  AgentClassifier is being called                                ****")
        logger.info("*********************************************************************************************************")

        logger.info(f"Incoming state: {state}")

        try:

            structured_intent = state.structured_intent
            if not structured_intent:
                logger.warning("No structured_intent found. Defaulting to 'general' workspace.")
                return self._default_response()

            task = structured_intent.get("task", "")
            logger.info(f"Task detected: {task}")

            # -----------------------------------------------------------------
            # 1. Deterministic Rule-Based Workspace Classification
            # -----------------------------------------------------------------
            workspace_name = self._rule_based_classification(structured_intent)

            # -----------------------------------------------------------------
            # 2. LLM Fallback if rules fail
            # -----------------------------------------------------------------
            if not workspace_name:
                logger.info("Falling back to LLM classification...")
                workspace_name = await self._llm_classification(state)

            if not workspace_name:
                logger.warning("Workspace classification failed. Using 'general'.")
                return self._default_response()

            # -----------------------------------------------------------------
            # 3. Return workspace metadata
            # -----------------------------------------------------------------
            workspace_meta = self.workspaces.get(workspace_name)
            if not workspace_meta:
                logger.warning(f"Workspace '{workspace_name}' not found. Defaulting to general.")
                return self._default_response()

            logger.info(f"Assigned Workspace: {workspace_name}")
            return {
                "workspace_name": workspace_name,
                "workspace_meta": workspace_meta,
                "classification_confidence": 0.9
            }

        except Exception as e:
            logger.exception("AgentClassifier failed")
            return self._default_response(error=str(e))

    # -------------------------------------------------------------------------
    # Discover all workspaces from workspace_root
    # -------------------------------------------------------------------------
    def _discover_workspaces(self) -> Dict[str, Dict[str, Any]]:
        workspaces = {}
        for folder in self.workspace_root.glob("*_assistant"):
            manifest_path = folder / "workspace.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    try:
                        data = json.load(f)
                        workspaces[data["name"]] = data
                    except Exception as e:
                        logger.error(f"Failed to load workspace manifest {manifest_path}: {e}")
        return workspaces

    # -------------------------------------------------------------------------
    # Rule-based classification
    # -------------------------------------------------------------------------
    def _rule_based_classification(self, intent: Dict[str, Any]) -> Optional[str]:
        task = intent.get("task", "").lower()

        # Deterministic mapping
        if "ticker" in task or "stock" in task or "price" in task:
            return "stockticker_assistant"
        if "portfolio" in task or "risk" in task:
            return "riskmanager_assistant"
        if "news" in task or "sentiment" in task:
            return "sentiment_assistant"

        return None

    # -------------------------------------------------------------------------
    # LLM fallback classification
    # -------------------------------------------------------------------------
    async def _llm_classification(self, state: StateSchema) -> Optional[str]:

        try:
            prompt = f"""
Classify the following structured task intent into one or more available workspaces.
Available workspaces: {list(self.workspaces.keys())}

Structured Task Intent:
{json.dumps(state.structured_intent, indent=2)}

Return JSON:
{{ "workspace_name": "" }}
"""

            response = await self.llm.ainvoke(prompt)
            raw_output = getattr(response, "content", str(response))
            parsed = self._safe_json_parse(raw_output)

            if not parsed:
                return None

            return parsed.get("workspace_name")

        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Default response
    # -------------------------------------------------------------------------
    def _default_response(self, error: Optional[str] = None) -> Dict[str, Any]:
        default_workspace = "general_assistant"
        default_meta = self.workspaces.get(default_workspace, {})
        return {
            "workspace_name": default_workspace,
            "workspace_meta": default_meta,
            "classification_confidence": 0.2,
            "classification_error": error
        }

    # -------------------------------------------------------------------------
    # Safe JSON parse
    # -------------------------------------------------------------------------
    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == -1:
                return None
            return json.loads(text[start:end])
        except Exception:
            return None