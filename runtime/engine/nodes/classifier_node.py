from __future__ import annotations
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path

from core.paths import DOMAIN_ROOT
from runtime.engine.state.state_schema import StateSchema
from llm.model_manager import ModelManager
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")


class AgentClassifier:

    def __init__(self, llm: ModelManager):

        self.llm = llm
        self.domain_root = DOMAIN_ROOT

        self.domains = self._load_domains()

        logger.info(f"Discovered domains: {list(self.domains.keys())}")

    async def __call__(self, state: StateSchema) -> Dict[str, Any]:

        logger.info("*********************************************************************************************************")
        logger.info("****                                AgentClassifier is being called                                ******")
        logger.info("*********************************************************************************************************")

        structured_intent = state.structured_intent

        if not structured_intent:
            return self._default_response()

        task = structured_intent.get("task", "").lower()

        domain = self._classify_domain(task)
        role = self._classify_role(domain, task)
        intent = self._classify_intent(domain, role, task)

        if not domain or not role or not intent:

            logger.info("Falling back to LLM classification")

            domain, role, intent = await self._llm_classification(task)

        if not domain or not role or not intent:

            return self._default_response()


        domain_meta = {
            "domain": domain,
            "role": role,
            "intent": intent,
            "classification_confidence": 0.9
        }

        logger.info(f"Domain Meta: {domain_meta}")

        return {
            "domain_name" : domain,
            "role_name" : role,
            "domain_meta" : domain_meta
        }


    def _load_domains(self):

        domains = {}

        for domain_dir in self.domain_root.iterdir():

            domain_file = domain_dir / "domain.yaml"

            if not domain_file.exists():
                continue

            with open(domain_file) as f:
                domain_config = yaml.safe_load(f)

            domain_name = domain_config["domain"]

            roles = self._load_roles(domain_dir)

            domains[domain_name] = {
                "keywords": domain_config.get("keywords", []),
                "roles": roles
            }

        return domains


    def _load_roles(self, domain_dir: Path):

        roles = {}

        roles_dir = domain_dir / "roles"

        if not roles_dir.exists():
            return roles

        for role_dir in roles_dir.iterdir():

            role_file = role_dir / "role.yaml"
            intents_file = role_dir / "intents.yaml"

            if not role_file.exists():
                continue

            with open(role_file) as f:
                role_config = yaml.safe_load(f)

            intents = {}

            if intents_file.exists():

                with open(intents_file) as f:
                    intent_config = yaml.safe_load(f)

                intents = intent_config.get("intents", {})

            roles[role_config["role"]] = {
                "keywords": role_config.get("keywords", []),
                "intents": intents
            }

        return roles

    def _classify_domain(self, task):

        for domain, data in self.domains.items():

            if any(word in task for word in data["keywords"]):
                return domain

        return None


    def _classify_role(self, domain, task):

        if not domain:
            return None

        roles = self.domains[domain]["roles"]

        for role, data in roles.items():

            if any(word in task for word in data["keywords"]):
                return role

        return None

    def _classify_intent(self, domain, role, task):

        if not role:
            return None

        intents = self.domains[domain]["roles"][role]["intents"]

        for intent, data in intents.items():

            keywords = data.get("keywords", [])

            if any(word in task for word in keywords):
                return intent

        return None

    async def _llm_classification(self, task):

        prompt = f"""
Classify the following user task.

Task:
{task}

Return JSON:

{{
 "domain": "",
 "role": "",
 "intent": ""
}}
"""

        response = await self.llm.ainvoke(prompt)

        raw = getattr(response, "content", str(response))

        parsed = self._safe_json_parse(raw)

        if not parsed:
            return None, None, None

        return (
            parsed.get("domain"),
            parsed.get("role"),
            parsed.get("intent")
        )

    def _default_response(self):

        return {
            "domain": "general",
            "role": "general_assistant",
            "intent": "general_query",
            "classification_confidence": 0.2
        }

    def resolve_entry_stage(intent):

        candidates = []

        for node in graph.nodes:

            if intent in node.intents:
                candidates.append(node)

        return select_highest_priority(candidates)


    def _safe_json_parse(self, raw: str) -> Dict[str, Any]:
        """
        Safely parse LLM JSON output.
        Handles markdown code blocks and malformed responses.
        """

        if not raw:
            return {}

        text = raw.strip()

        # Remove ```json blocks
        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json", "", 1).strip()

        try:
            return json.loads(text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.error(f"Raw response: {text}")

            return {}