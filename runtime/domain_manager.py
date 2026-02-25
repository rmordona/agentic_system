############################################################
#                   AGENTIC SYSTEM ARCHITECTURE           #
#                                                          #
# This diagram illustrates how multi-domain agentic       #
# systems operate using Artifacts, Predicates, and Skills.#
# Domains provide raw data; predicates translate it into  #
# boolean/state checks; the Artifact stores state; Skills #
# operate on the Artifact; the Agent evaluates and acts.  #
############################################################
#
#          ┌────────────────────────────┐
#          │        DOMAIN LOGIC        │
#          │  (raw data, APIs, services)│
#          │                            │
#          │  - Market data             │
#          │  - Order book / trades     │
#          │  - External signals        │
#          └─────────────┬──────────────┘
#                        │
#                        │ Domain provides
#                        ▼
#          ┌──────────────────────────────────────┐
#          │       PREDICATES                     │
#          │  (boolean / yes-no checks)           │
#          │                                      │
#          │ Examples:                            │
#          │  is_market_open(ctx)                 │
#          │  is_bullish(ctx)                     │
#          │  order_is_terminal(ctx)              │
#          │  risk_metrics_within_guardrails(ctx) │
#          └─────────────┬────────────────────────┘
#                        │ Evaluated
#                        ▼
#          ┌────────────────────────────┐
#          │        ARTIFACT            │
#          │  (state + domain values)   │
#          │                            │
#          │ Fields:                    │
#          │  market_open               │
#          │  trade_permission          │
#          │  risk_index                │
#          │  key_drivers               │
#          │  order_status              │
#          └─────────────┬──────────────┘
#                        │ Used by
#                        ▼
#          ┌────────────────────────────┐
#          │          SKILLS            │
#          │ (operations / instructions │
#          │   on the Artifact)         │
#          │                            │
#          │ - Analyze Artifact state   │
#          │ - Plan next tasks          │
#          │ - Trigger HITL if needed   │
#          └─────────────┬──────────────┘
#                        │ Executes
#                        ▼
#          ┌────────────────────────────┐
#          │         AGENTIC SYSTEM     │
#          │  (domain-agnostic)         │
#          │                            │
#          │ - Receives predicates      │
#          │ - Evaluates conditions     │
#          │ - Chooses next skill/action│
#          │ - Updates artifact         │
#          └────────────────────────────┘
############################################################
from __future__ import annotations
from core.paths import WORKSPACES_ROOT

import re
import os
import sys
import uuid
import hashlib
import json
import inspect
import importlib.util
import asyncio
import yaml
import copy
from jsonschema import validate, ValidationError

from pathlib import Path
from datetime import datetime, UTC
from typing import Any, TypedDict, Dict, Optional, List, Generic, TypeVar, get_args, get_origin, Union
from typing_extensions import Literal

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, create_model
from pydantic_core import PydanticUndefined
from functools import wraps

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from runtime.tools.mcp_client import MCPClient
from runtime.tools.mcp_manager import MCPManager
from runtime.artifact_factory import ArtifactSchema
from runtime.agent_manager import AgentManager
from runtime.agent_profiler import AgentOutput, AgentProfiler

import logging
# SILENCE THE NOISE
logging.basicConfig(level=logging.WARNING) # Set global default
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


def generate_checksum(payload: dict) -> str:
    logger.debug("Generating checksum for payload")
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    logger.debug(f"Checksum generated: {checksum}")
    return checksum


def generate_uuid() -> str:
    uid = str(uuid.uuid4())
    logger.debug(f"Generated UUID: {uid}")
    return uid


DomainType = TypeVar("DomainType", bound=BaseModel)

##################################################################
# Schema Factory
##################################################################
NODEFAULT = "<NODEFAULT>"

class SchemaFactory:

    @staticmethod
    def create_class_from_json(
        class_name: str,
        schema: Dict[str, Any],
        definitions: Dict[str, Any] | None = None
    ) -> Type:
        # Capture root definitions if not provided
        if definitions is None:
            definitions = schema.get("definitions", {})

        if schema.get("type") != "object":
            raise ValueError(
                f"Top-level schema must be an object, got {schema.get('type')}"
            )

        fields = {}
        required = set(schema.get("required", []))

        for prop_name, prop_schema in schema.get("properties", {}).items():
            field_type, default = SchemaFactory._infer_field(
                prop_schema,
                definitions,
                prop_name
            )
            fields[prop_name] = (
                field_type,
                ... if prop_name in required else default
            )

        return create_model(class_name, **fields)

    @staticmethod
    def _infer_field(
        schema: Dict[str, Any],
        definitions: Dict[str, Any],
        prop_name: str
    ):
        # --- Resolve $ref ---
        if "$ref" in schema:
            ref_key = schema["$ref"].split("/")[-1]
            actual_schema = definitions.get(ref_key)
            if not actual_schema:
                raise ValueError(f"Definition {ref_key} not found in schema")
            # Pass definitions forward recursively
            return SchemaFactory._infer_field(actual_schema, definitions, prop_name)

        schema_type = schema.get("type")

        # --- Standard types ---
        if schema_type == "string":
            if "enum" in schema:
                enum_values = list(schema["enum"])
                return Literal[tuple(enum_values)], None
            return str, None

        if schema_type == "integer":
            return int, None
        if schema_type == "number":
            return float, None
        if schema_type == "boolean":
            return bool, None

        # --- Array ---
        if schema_type == "array":
            item_schema = schema.get("items", {})
            return List[SchemaFactory._infer_field(item_schema, definitions, prop_name)[0]], None

        # --- Object ---
        if schema_type == "object":
            # Pass definitions recursively for nested objects
            return SchemaFactory.create_class_from_json(f"{prop_name.title()}Model", schema, definitions), None

        raise ValueError(f"Unsupported schema type: {schema_type}")

    @staticmethod
    def class_to_json_schema(model_class: type) -> str:
        """
        Convert a dynamically generated Pydantic model class into a JSON Schema string.
        
        Args:
            model_class: The Pydantic model class (created by create_class_from_json)
        
        Returns:
            JSON string representing the schema
        """
        if not issubclass(model_class, BaseModel):
            raise ValueError("model_class must be a subclass of pydantic.BaseModel")

        # Use Pydantic's built-in method to get JSON schema dict
        schema_dict = model_class.model_json_schema()
        
        # Convert dict to JSON string
        return json.dumps(schema_dict, indent=2)

    @staticmethod
    def class_to_payload(model_class: type) -> dict:
        """
        Convert a Pydantic model class into a payload dictionary template.
        Recursively handles nested models, enums, defaults, arrays, and $refs.
        """
        if not issubclass(model_class, BaseModel):
            raise ValueError("model_class must be a subclass of pydantic.BaseModel")

        schema = model_class.model_json_schema()
        defs = schema.get("$defs", {})

        def _resolve(node):
            if isinstance(node, dict):
                if "$ref" in node:
                    ref_path = node["$ref"]
                    if ref_path.startswith("#/$defs/"):
                        ref_name = ref_path.split("/")[-1]
                        if ref_name not in defs:
                            raise ValueError(f"Reference {ref_name} not found in $defs")
                        return _resolve(copy.deepcopy(defs[ref_name]))
                if "properties" in node:
                    return {k: _resolve(v) for k, v in node["properties"].items()}
                elif "enum" in node:
                    return node["enum"][0] if node["enum"] else None
                elif "default" in node:
                    return node["default"]
                elif node.get("type") == "array":
                    items = node.get("items", {})
                    return [_resolve(items)]
                else:
                    return None
            elif isinstance(node, list):
                return [_resolve(item) for item in node]
            else:
                return None

        schema_copy = copy.deepcopy(schema)
        schema_copy.pop("$defs", None)
        return _resolve(schema_copy)

    # --- Application in your code ---
    # Suppose the Agent only provides: {"ticker": "AAPL"}
    # And the contract for 'execute_trade' has a default order_type: "LIMIT"
    # Usage:
    #    final_args = construct_and_validate_payload(trade_contract, {"ticker": "AAPL", "qty": 10, "side": "BUY"})
    #
    # Now the call is safe and complete:
    # result = await session.call_tool("execute_trade", arguments=final_args)
    @staticmethod
    def construct_and_validate_payload(schema_node: dict, payload: dict = None, branch: str = "input") -> dict:

        logger.info(f"Schema Node: {schema_node}")
        if not isinstance(schema_node, dict):
            raise TypeError(
                f"schema_node must be dict, got {type(schema_node).__name__}: {schema_node}"
            )

        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise TypeError(
                f"payload must be dict, got {type(payload).__name__}"
            )

        defs = schema_node.get("$defs", {})

        # Select the correct schema branch
        if ( "properties" in schema_node  and branch in schema_node["properties"]):
            schema_node = SchemaFactory._resolve_ref( schema_node["properties"][branch], defs)


        def resolve_ref(node):
            return SchemaFactory._resolve_ref(node, defs)

        def validate_constraints(val, sub_schema, path):
            if isinstance(val, (int, float)):
                if "minimum" in sub_schema and val < sub_schema["minimum"]:
                    raise ValueError(f"Range Error at '{path}': {val} < {sub_schema['minimum']}")
                if "maximum" in sub_schema and val > sub_schema["maximum"]:
                    raise ValueError(f"Range Error at '{path}': {val} > {sub_schema['maximum']}")

            if "enum" in sub_schema and val not in sub_schema["enum"]:
                raise ValueError(f"Enum Error at '{path}': '{val}' not in {sub_schema['enum']}")

            if "pattern" in sub_schema and isinstance(val, str):
                if not re.match(sub_schema["pattern"], val):
                    raise ValueError(f"Pattern Error at '{path}': Fails regex {sub_schema['pattern']}")

        def build(node, data, path="root"):

            node = resolve_ref(node)

            if node.get("type") == "object":
                obj = {}
                props = node.get("properties", {})
                required = node.get("required", [])

                for key, sub_schema in props.items():
                    current_path = f"{path}.{key}"

                    sub_schema = resolve_ref(sub_schema)

                    val = data.get(key) if isinstance(data, dict) else None
                    if val is None:
                        val = sub_schema.get("default")

                    if val is None and key in required:
                        raise ValueError(f"Missing required field: '{current_path}'")

                    if val is not None:
                        validate_constraints(val, sub_schema, current_path)

                        if sub_schema.get("type") == "object":
                            obj[key] = build(sub_schema, val or {}, current_path)
                        elif sub_schema.get("type") == "array":
                            if not isinstance(val, list):
                                raise ValueError(f"Type Error at '{current_path}': Expected array")
                            obj[key] = val
                        else:
                            obj[key] = val

                return obj

            return {}

        return build(schema_node, payload)

    @staticmethod
    def _resolve_ref(node, defs):
        if not isinstance(node, dict):
            raise TypeError(f"_resolve_ref expected dict, got {type(node).__name__}")

        if "$ref" not in node:
            return node

        ref = node["$ref"]

        if not ref.startswith("#/$defs/"):
            raise ValueError(f"Unsupported $ref format: {ref}")

        def_name = ref.split("/")[-1]

        if def_name not in defs:
            raise ValueError(f"$ref target not found in $defs: {def_name}")

        return defs[def_name]



# --------------------------------------------------------------------------------------------------
# AgentContext: dynamic, per-turn ownership: control, data, stage, artifacts, and history.
# --------------------------------------------------------------------------------------------------

@dataclass
class AgentContext:
        agent_name: str        # identity of the agent in this turn
        stage: str             # current stage
        # ------------------------------------------------------------------
        # Control Plane (required, immutable intent)
        # ------------------------------------------------------------------
        control_raw: ArtifactSchema = None # artifact.md / plan / contract

        # ------------------------------------------------------------------
        # Data Plane (append-only, domain governed)
        # ------------------------------------------------------------------
        data_raw:  DataEnvelope[DomainType]  = None # Field(default_factory=DataEnvelope)

        # ------------------------------------------------------------------
        # Tool Plane (append-only execution records)
        # ------------------------------------------------------------------
        tool_raw: List[ToolEnvelope[DomainType]] = field(default_factory=list)
        # ------------------------------------------------------------------
        timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
        result_summary: str | None = None          # optional result / status

########################################################################################
# DATA ENVELOPE
########################################################################################
# What the Envelope adds to the Raw Tool Output:
#     Traceability: request_id, parent_agent_id.
#         Performance: latency_ms, token_usage.
#         Reliability: confidence_score (crucial for your "Low Confidence" HITL trigger).
#         Security: digital_signature to ensure the tool data wasn't tampered with.
# ---------------------------------------------------------------------------------------
# Note: To have a contract-centric architecture, and not agent-centric architecture,
#       we bind DataAdapter and DataEnvelopt to a tool not an agent, specially when
#       agents are replaceable but not tools. 
# ---------------------------------------------------------------------------------------
# Imagine you are running the get_market_regime_data tool:
#
#    AgentPlanner: Looks at the Manifest and says, "I need market data for $AAPL."
#    DataAdapter (Input): Takes the Agent's state and formats it into the specific URL/JSON 
#                required by the external AlphaVantage or Bloomberg API.
#    External Tool: Returns messy, raw JSON.
#    DataAdapter (Output): Cleans that JSON so it perfectly matches the output_schema defined 
#                in your YAML.
#    DataEnvelope: Wraps that clean data with a confidence_score and a timestamp.
#    AgentValidator: Receives the Envelope. It reads the Manifest (YAML). It sees the data matches 
#                the schema and checks the hitl_policy against the metadata in the envelope.
########################################################################################
################################################################################
# DataAdapter / ToolManager vs DataEnvelope / ToolEnvelope Architecture
#
#                        ┌──────────────────────────────┐
#                        │        Initialization        │
#                        └──────────────────────────────┘
#                                   │
#           ┌───────────────────────┴───────────────────────┐
#           │                                               │
#  ┌──────────────────────┐                         ┌───────────────────────┐
#  │     DataAdapter      │                         │      ToolManager      │
#  │ (per tool, singleton)│                         │ (per tool, singleton) │
#  │----------------------│                         │---------------------- │
#  │ input_schema         │                         │ governance_policy     │
#  │ output_schema        │                         │  - validation_rules   │
#  │ validate_input()     │                         │  - hitl_policy        │
#  │ validate_output()    │                         │  - stage_exit_trigger │
#  └──────────────────────┘                         └───────────────────────┘
#           │                                               │
#           │                                               │
#           ▼                                               ▼
# ┌──────────────────────┐                             ┌───────────────────────┐
# │   DataEnvelope       │                             │   ToolEnvelope        │
# │ (per execution)      │                             │ (per execution)       │
# │----------------------│                             │---------------------- │
# │ input_data           │◀── validated by DataAdapter │ tool_name             │
# │ output_data          │                             │ input_reference       │
# │ runtime flags (opt)  │                             │ output_reference      │
# │                      │                             │ runtime_state:        │
# │                      │                             │  - hitl_required      │
# │                      │                             │  - stage_complete     │
# │                      │                             │  - validation_results │
# │                      │                             │ governance_policy_ref │◀─── references ToolManager
# └──────────────────────┘                             └───────────────────────┘
#           │                                               │
#           ▼                                               ▼
#                 ┌───────────────────────────────┐
#                 │         Execution             │
#                 │ ToolAdapter.execute(input)    │
#                 │ ToolManager.evaluate_governance│
#                 └───────────────────────────────┘
#
# Key Points:
# - DataAdapter: schemas, input/output validation
# - ToolManager: static governance metadata loaded once
# - DataEnvelope: per-execution validated input/output data
# - ToolEnvelope: per-execution runtime state, references governance
# - ToolAdapter: executes tool logic using envelope data
################################################################################

class DataEnvelope(BaseModel, Generic[DomainType]):
    tool: str
    type: str
    version: str
    producer: str # The Agent
    stage: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: DomainType
    checksum: Optional[str]
    references: List[str] = []

class DataBridge:
    def __init__(self, agent_md_content: str):
        self.raw_schema = self._extract_json_from_md(agent_md_content)
        self.validator_class = SchemaFactory.create_class_from_json("AgentContract", self.raw_schema)

    def validate_and_save(self, agent_response_string: str, db_session):
        # 1. Convert string to JSON
        data_dict = json.loads(agent_response_string)
        
        # 2. Automatically validate against the Dynamic Class
        validated_data = self.validator_class(**data_dict)
        
        # 3. Map to Database (Generic Upsert)
        # This part interacts with your SQLAlchemy/SQLModel
        return db_session.merge(validated_data.dict())

class DataAdapter(Generic[DomainType]):
    def __init__(self, 
                tool_name: str, 
                schema_class: type[DomainType]):
        self.tool_name = tool_name
        self.payload_schema = schema_class
        logger.info(f"DataAdapter initialized for agent '{tool_name}'")

    def create_envelope(
        self,
        payload:  Union[DomainType, dict],
        producer: str,  # The Agent
        stage: str
    ) -> DataEnvelope[DomainType]:
        logger.info(
            f"Creating DataEnvelope | domain={self.tool_name} producer={producer} stage={stage}"
        )
        logger.debug(f"Validating payload against {self.payload_schema}")

        # 1. Validate + materialize typed payload
        #    If payload is already a Pydantic model, use it directly
        if isinstance(payload, self.payload_schema):
            payload_model = payload
        else:
            payload_model: DomainType = self.payload_schema(**payload)

        checksum = generate_checksum(payload_model.model_dump())

        # 2. Create typed envelope
        envelope = DataEnvelope[DomainType](
            tool=self.tool_name,
            type=self.payload_schema.__name__.lower(),
            version="1.0",
            producer=producer,
            stage=stage,
            # created_at=datetime.now(UTC),
            payload=payload_model,   
            checksum=checksum
        )

        logger.info(
            f"DataEnvelope created | domain={envelope.tool} checksum={checksum}"
        )
        return envelope

class DataManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.data_map: Dict[str, DataAdapter] = {}
        logger.info(f"DataManager initialized")

    async def register_schema(self, manifests: dict):
        logger.info("Scanning schema for tools")

        for tool_name in manifests:

            contract = manifests.get(tool_name)

            properties = contract.get("properties")
            if not isinstance(properties, dict):
                raise ValueError("Invalid contract: missing 'properties' object")

            input_schema = properties.get("input_schema")
            output_schema = properties.get("output_schema")

            if input_schema is None:
                raise ValueError("Invalid contract: missing 'input_schema'")

            if output_schema is None:
                raise ValueError("Invalid contract: missing 'output_schema'")

            validation_rules = contract.get("validation_rules", [])

            hitl_policy = contract.get("hitl_policy", {})

            stage_exit_trigger = contract.get("stage_exit_trigger", {})


            schema = {
                "type": "object",
                "required": ["input", "output"],
                "properties": {
                    "input": input_schema,
                    "output": output_schema
                }
            }

            logger.info(f"Input/Output Schema for tool name ({tool_name}): {schema}")  

            try:

                # 1. Usage in your Pipeline
                DynamicDataSchema: Type[DomainType] = SchemaFactory.create_class_from_json(f"{tool_name}Schema", schema, None)

                logger.info(f"Dynamic Data Model: {DynamicDataSchema}")

                if not DynamicDataSchema:
                    logger.warning(f"Schema class '{DynamicDataSchema}'")
                    continue

                self.data_map[tool_name] = DataAdapter(
                    tool_name=tool_name,
                    schema_class=DynamicDataSchema # This is a schema class [type(DomainType)]
                )

                logger.info(f"Successfully registered data schema for tool name: '{tool_name}'")

            except Exception as e:
                logger.exception(f"Failed to load data for tool name: '{tool_name}': {e}")


    def get_default_for_type(self, field_type: Any) -> Any:
        origin = get_origin(field_type)

        # 1. Lists
        if origin is list:
            return []

        # 2. Nested Pydantic models (THIS fixes input/output)
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return self.instantiate_with_defaults(field_type)

        # 3. Literals
        if origin is Literal:
            args = getattr(field_type, "__args__", [])
            return args[0] if args else NODEFAULT

        # 4. Primitives
        if field_type is str:
            return NODEFAULT
        if field_type is int:
            return 0
        if field_type is float:
            return 0.0
        if field_type is bool:
            return False
        if field_type is dict:
            return {}

        # 5. Fallback
        return NODEFAULT


    def get_adapter(self, agent_name: str) -> DataAdapter:
        adapter = self.data_map.get(agent_name)
        if not adapter:
            logger.error(f"DataAdapter not found for agent '{agent_name}'")
        return adapter

    async def process_input(self, tool_name: str, agent_name: str, stage: str, user_intent: str) -> DataEnvelope:
        logger.info(f"To process input data, we need the tool to Run: {tool_name} by agent ({agent_name}) in stage ({stage})")

        # For now, use a SAMPLE PAYLOAD for DEMO purposes
        execution_payload = await get_sample_payload(tool_name, user_intent)

        logger.info(f"Execution Payload: {execution_payload}")

        data_adapter = self.data_map[tool_name]

        # 2. Use the adapter to create the envelope.
        # Passing an empty dict {} triggers the Pydantic schema's default values.
        # Producer is 'system' because this is the mission's 'Genesis' block.
        instantiated_schema = self.instantiate_with_defaults(data_adapter.payload_schema)
        instantiated_payload_dict = instantiated_schema.model_dump() # converts into a dict

        logger.info(
            f"Instantiated default payload | "
            f"type={type(instantiated_schema)} "
            f"values={instantiated_payload_dict}"
        )

        payload_schema = data_adapter.payload_schema
        logger.info(f"Payload Schema {payload_schema}")

        json_schema  = SchemaFactory.class_to_json_schema(payload_schema)

        # Validate and Reconstruct Payload
        if isinstance(json_schema, str):
            json_schema = json.loads(json_schema)

        # Extract only the Input Structure form the Input Schema and populate it with Input Data
        input_args = SchemaFactory.construct_and_validate_payload(json_schema, execution_payload, "input")
        logger.info(f"Input Args: {input_args}")
        instantiated_payload_dict["input"] = input_args
        try:
            data_env = data_adapter.create_envelope(
                payload=instantiated_payload_dict, 
                producer=agent_name, 
                stage=stage
            )
            return data_env
        except ValueError as e:
            logger.error(f"Critical Error: creating data envelope: agent '{agent_name}', stage '{stage}', tool '{tool_name}', {e}")


    async def process_output(self, tool_name: str, tool_output: list, data_env: DataEnvelope) -> DataEnvelope:
        logger.info(f"Tool Output: {tool_output}")

        output_dict = {}
        if tool_output and isinstance(tool_output, list):
            first = tool_output[0]

            logger.info(f"Text Output: {first.text}")
            if isinstance(first.text, str):
                output_dict = json.loads(first.text)
        elif tool_output and isinstance(tool_output, dict):
            output_dict = tool_output
        logger.info(f"Output Dict: {output_dict}")

        data_adapter = self.data_map[tool_name]
        json_schema  = SchemaFactory.class_to_json_schema(data_adapter.payload_schema)

        if isinstance(json_schema, str):
            json_schema = json.loads(json_schema)
        logger.info(f"json_schema: {json_schema}")

        # Extract only the Input Structure form the Input Schema and populate it with Output Data
        output_args = SchemaFactory.construct_and_validate_payload(json_schema, output_dict, "output")
        logger.info(f"Output Args: {output_args}")

        # Now update payload with the output
        payload_dict = data_env.payload.model_dump()
        payload_dict["output"] = output_args
        data_env.payload = data_adapter.payload_schema(**payload_dict) 

        data_env.checksum = generate_checksum(data_env.payload.model_dump())
        logger.info(f"Payload dict: {data_env.payload.model_dump()}")
        return data_env

    def validate_output(self, raw_output: Any) -> BaseModel:
        """
        Validates tool execution output against the configured output_schema.

        Supports:
        - Pydantic model
        - dict
        - JSON string
        - List[TextContent]
        """



        if raw_output is None:
            raise ValueError("Tool returned None output")

        #  Already validated model
        if isinstance(raw_output, self.output_schema):
            return raw_output

        # If list (LLM-style output)
        if isinstance(raw_output, list):
            if not raw_output:
                raise ValueError("Tool returned empty output list")

            first = raw_output[0]

            if not hasattr(first, "text"):
                raise TypeError("Expected TextContent with .text field")

            raw_output = first.text  # extract JSON string

        # If JSON string
        if isinstance(raw_output, str):
            try:
                raw_output = json.loads(raw_output)
            except json.JSONDecodeError as e:
                raise ValueError(f"Output is not valid JSON: {e}") from e

        # If dict → validate with schema
        if isinstance(raw_output, dict):
            try:
                return self.output_schema(**raw_output)
            except ValidationError as e:
                raise ValueError(
                    f"Output validation failed: {e.errors()}"
                ) from e

        raise TypeError(
            f"Invalid output type: expected dict, JSON string, "
            f"TextContent list, or {self.output_schema.__name__}, "
            f"got {type(raw_output).__name__}"
        )

    def list_available_input_schemas(self, tools: list) -> list:
        schemas = []
        for tool in tools:
            logger.info(f"Loading schema for tool {tool}")
            data_adapter = self.data_map.get(tool)
            try:
                json_payload  = SchemaFactory.class_to_payload(data_adapter.payload_schema)
                schema = json_payload.get("input")
                schemas.append(schema)
            except Exception as e:
                logger.info(f"- No Schema provided for tool {tool}")
        return schemas


    def instantiate_with_defaults(self, model_class: Type[DomainType]) -> DomainType:
        payload = {}

        for name, field_info in model_class.model_fields.items():
            field_type = field_info.annotation

            # REQUIRED fields must NEVER be None
            payload[name] = self.get_default_for_type(field_type)

        return model_class(**payload)





##################################################################
# TOOL ENVELOPE
##################################################################
_URL_XHTTP = "http://127.0.0.1:8080/mcp"

class ToolCall(TypedDict):
    agent: str
    tool: str
    args: Dict[str, Any]
    result: Any

class ToolEnvelope(BaseModel, Generic[DomainType]):
    id: str
    tool_name: str
    tool_version: Optional[str] = None
    agent_role: str
    stage: str
    intent: str 
    input: Dict[str, Any] = Field(default_factory=dict)
    #output: Optional[Dict[AgentOutput, Any]] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None
    success: bool = False
    governance_policy: Dict[str, Any] = Field(default_factory=dict)

class ToolAdapter:

    def __init__(self, name: str, description: str, schema: dict, tool_file: Path):
        self.name = name
        self.description = description
        self.parameters = schema  # The MCP inputSchema (e.g., ticker, qty)
        self.tool_file = tool_file
        # self.mcp_caller = mcp_caller # The logic to run the MCP command

        self.governance_policy: Dict[str, Any] = None 

        # This keeps the connections alive
        self._session_cache: Dict[Path, ClientSession] = {}
        self._exit_stack: Dict[Path, AsyncExitStack] = {}
        
        logger.info(f"ToolAdapter initialized | tool={name}")

    def get_schema(self) -> dict:
        """
        Returns the OpenAI-compatible schema so the LLM knows HOW to call the tool.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    async def execute(self, tool_name: str, instruction: dict) -> ToolEnvelope:
        """
        Receives the standardized instruction block and executes the MCP call.
        """
        logger.info(f"Executing tool '{tool_name}' via instruction block")
        start_time = datetime.now(UTC).isoformat()

        # Extract values from the instruction dictionary for the Envelope
        agent_role = instruction.get("agent", "unknown")
        stage = instruction.get("stage", "unknown")

        # The actual arguments for the MCP tool are inside 'execution'
        payload_schema = instruction.get("payload", {}) 
        logger.info(f"Payload Schema: {payload_schema}")
        payload_dict = payload_schema.model_dump() # Turn into a dict
        logger.info(f"Payload Dict: {payload_dict}")
        mcp_payload = payload_dict.get("input")  
        logger.info(f"MCP Payload: {mcp_payload}")

        # We call the mcp_caller (the bridge we built) 
        # using the arguments extracted from the instruction
        #_input, _output = await self.mcp_caller(self.tool_file, tool_name, mcp_payload)
        _input  = mcp_payload
        result = await ToolAdapter.mcp_xhttp_caller(_URL_XHTTP, tool_name, mcp_payload)

        if result.get("status") == "success":
            success = True
            error = None
            _output = result.get("output")
        else:
            _output = None
            success = False
            error = result.get("message")
            logger.exception(f"Tool execution failed: {error}")

        logger.info(f"Execution Completed ...")

        logger.info(f"Wrapping output into a ToolEnvelope")
        logger.info(f"Tool Adapter Governance Policy: {self.governance_policy}")

        return ToolEnvelope(
            id=generate_uuid(),
            tool_name=tool_name,
            agent_role=agent_role,
            stage=stage,
            intent=instruction.get("task_description", self.description),
            input=_input, # We log the specific tool args, not the whole instruction
            output=_output,
            error=error,
            started_at=start_time,
            completed_at=datetime.now(UTC).isoformat(),
            success=success,
            governance_policy = self.governance_policy
        )

    async def mcp_caller(self, tool_file: Path, tool_name: str, payload: dict):
        """
        The bridge logic. Now with session persistence to keep 
        the 'Agnostic OS' snappy.
        """
        logger.info(f"Entering the mcp caller: {tool_name} for {tool_file}")
        logger.info(f"Payload: {payload}")

        # 1. Check if we already have a live session (if we have an open pipe with an mcp server) for this file
        if tool_file in self._session_cache:
            session = self._session_cache[tool_file]
            result = await session.call_tool(tool_name, arguments=payload) # Makes a JSON-RPC call
            return result.content

        # 2. If not, spin it up (Your original logic)
        logger.info(f"Starting persistent session for {tool_file.name}")
        
        # We use AsyncExitStack to keep the 'async with' contexts alive
        # This is a "cleanup bucket." MCP uses async with blocks. Normally, when that block ends, 
        # the process dies. By putting the context into a stack and saving it to self, we prevent the process from closing.
        stack = AsyncExitStack()
        self._exit_stack[tool_file] = stack

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(tool_file.absolute())],
            env=None
        )

        # Entering the contexts
        # This spawns the sub-process. read and write are the STDIN and STDOUT streams (the pipes).
        logger.info(f"Spawning sub-process for mcp server")
        read, write = await stack.enter_async_context(stdio_client(server_params))
        # This "pins" the connection open so it stays alive after this function finishes.
        session = await stack.enter_async_context(ClientSession(read, write))
        
        # The "Handshake." The engine says "Hello," and mcp_server.py replies with "I am MCP Server, and I have these 3 tools."
        logger.info(f"Session Initialization")
        await session.initialize()
        # We save this session. Next time this tool is called, we will stop at Step 1.
        self._session_cache[tool_file] = session

        logger.info(f"Payload: {payload}")
        # 3. Call the tool.  This finally executes the function inside your script 
        # and returns the list of content (text, images, or JSON) back to your ToolAdapter.
        logger.info(f"Now Calling the tool {tool_name} with the following payload: {payload}")
        result = await session.call_tool(tool_name, arguments=payload)
        logger.info(f"Received result: {result.content}")
        return payload, result.content

    @classmethod
    async def mcp_xhttp_caller(cls, url: str = _URL_XHTTP, tool_name: str = None, payload: dict = {}):

        logger.info(f"Entering the mcp xhttp caller: tool call ({tool_name}) for mcp endpoint ({url})")
        logger.info(f"Payload: {payload}")



        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                try:
                    result = await session.call_tool(tool_name, payload)
                    logger.info(f"Received xhttp result: {result}")

                    if result.isError:
                        return {
                            "status": "error",
                            "tool": tool_name,
                            "message": result.content
                        }

                    # 1️⃣ Prefer structuredContent (best option)
                    if getattr(result, "structuredContent", None):
                        return {
                            "status": "success",
                            "tool": tool_name,
                            "output": result.structuredContent
                        }

                    # 2️⃣ Handle content safely (could be single object or iterable)
                    content = getattr(result, "content", None)

                    if content:
                        outputs = []

                        # If it's iterable (list-like), iterate
                        if isinstance(content, (list, tuple)):
                            items = content
                        else:
                            # Single content block case
                            items = [content]

                        for item in items:
                            if hasattr(item, "text"):
                                outputs.append(item.text)
                            elif hasattr(item, "json"):
                                outputs.append(item.json)
                            else:
                                outputs.append(str(item))

                        return {
                            "status": "success",
                            "tool": tool_name,
                            "output": outputs
                        }

                    # 3️⃣ Fallback
                    return {
                        "status": "success",
                        "tool": tool_name,
                        "output": None
                    }

                except Exception as e:
                    return {
                        "status": "error",
                        "tool": tool_name,
                        "message": str(e)
                    }




    # Invoked from ToolManager.shutdown
    async def shutdown(self):
        """Cleanly close all MCP processes at engine stop."""
        for path, stack in self._exit_stack.items():
            logger.info(f"Closing MCP server: {path.name}")
            await stack.aclose()
        self._session_cache.clear()
        self._exit_stack.clear()


class ToolManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.tool_map: Dict[str, ToolAdapter] = {}

        logger.info(f"ToolManager initialized")

        # This keeps the connections alive
        self._session_cache: Dict[Path, ClientSession] = {}
        self._exit_stack: Dict[Path, AsyncExitStack] = {}

    async def scan_and_register_tools(self) -> None:

        logger.info(f"Extracting agents tools from MCP endpoints ... ")
        registry = await self.extract_tools_via_xhttp()
        logger.info(f"Registration: {registry}")

        for tool_data in registry:
            adapter = ToolAdapter(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    schema=tool_data["arguments"],
                    tool_file="",
                    # mcp_caller=self.call_mcp_tool
                )
            # Register in the map
            self.tool_map[adapter.name] = adapter
                    
        logger.info(f"Agent tool scan complete. Total registered tools: {len(self.tool_map)}")

    async def extract_tools_via_protocol(self, tool_file: Path) -> list[dict]:
        import sys
        import subprocess

        # Using sys.executable ensures we use the exact same Python environment
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(tool_file.absolute())],
            env=None
        )

        registry = []
        try:
            # Short timeout - it should be near-instant
            async with asyncio.timeout(5):
                # stderr=subprocess.DEVNULL is the default; 
                # changing to None can sometimes help see output in the main console
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        response = await session.list_tools()
                        for tool in response.tools:
                            logger.info(f"tool: {tool}")
                            registry.append({
                                "name": tool.name,
                                "description": tool.description or "",
                                "arguments": tool.inputSchema # Capture this for later!
                            })
        except Exception as e:
            # LOG THE CRASH DETAIL
            logger.error(f"Handshake failed for {tool_file.name}.")
            logger.error(f"Error Detail: {repr(e)}")
            
            # PRO-TIP: Try to run it once manually via subprocess to catch the traceback
            result = subprocess.run(
                [sys.executable, str(tool_file)], 
                capture_output=True, 
                text=True, 
                timeout=2
            )
            if result.stderr:
                logger.error(f"Captured Traceback from {tool_file.name}:\n{result.stderr}")
            
        return registry


    async def extract_tools_via_xhttp(self, url: str = _URL_XHTTP ) -> list[dict]:
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Get the list of tools
                tools_list = await session.list_tools()

                registry = []

                for tool in tools_list.tools:
                    # Get the original Python function for introspection
                    func = getattr(tool, "func", None)
                    params = []

                    if func is not None:
                        sig = inspect.signature(func)
                        for name, param in sig.parameters.items():
                            params.append({
                                "name": name,
                                "type": str(param.annotation) if param.annotation != inspect._empty else "Any",
                                "default": param.default if param.default != inspect._empty else None
                            })

                    registry.append({
                        "name" : tool.name,
                        "description": getattr(tool, "description", ""),
                        "arguments": params
                    })
                return registry

    async def register_governance_policy(self, manifests: dict):
        logger.info("Scanning schema for tools")

        for tool_name in manifests:

            contract = manifests.get(tool_name)

            validation_rules = contract.get("validation_rules", [])

            hitl_policy = contract.get("hitl_policy", {})

            stage_exit_trigger = contract.get("stage_exit_trigger", {})

            governance_policy = {
                "validation_rules": validation_rules,
                "hitl_policy": hitl_policy,
                "stage_exit_trigger": stage_exit_trigger
            }

            logger.info(f"Governance Policy for tool name ({tool_name}): {governance_policy}")  

            self.tool_map[tool_name].governance_policy = governance_policy

            logger.info(f"Successfully registered governance policy for tool name: '{tool_name}'")

    async def get_adapter(self, tool_name: str) -> ToolAdapter:
        tool_adapter = self.tool_map[tool_name]
        if tool_adapter:
            return tool_adapter
        return None

    # Invoked from CoreEngine.shutdown
    async def shutdown(self):
        """Cleanly close all MCP processes at engine stop."""
        for path, stack in self._exit_stack.items():
            logger.info(f"Closing MCP server: {path.name}")
            await stack.aclose()
        self._session_cache.clear()
        self._exit_stack.clear()

        for tool in self.tool_map:
            await tool.shutdown()

    def get_llm_tool_definitions(self):
        """
        Converts the internal MCP registry into standard LLM tool format.
        """
        llm_tools = []
        for tool in self.all_discovered_tools: # your registry list
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["arguments"] # Rename 'arguments' to 'parameters'
                }
            })
        return llm_tools

    def list_available_tools(self) -> list:
        keys = self.tool_map.keys()
        return list(keys)

    def auto_envelope_wrapper(func, agent_role: str, stage: str):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(
                f"Auto-enveloped tool execution | tool={func.__name__} stage={stage}"
            )

            envelope = ToolEnvelope(
                id=str(uuid.uuid4()),
                tool_name=func.__name__,
                agent_role=agent_role,
                stage=stage,
                intent=func.__doc__ or "Executing atomic tool",
                input=kwargs,
                started_at=datetime.now(UTC).isoformat()
            )

            try:
                result = await func(*args, **kwargs)
                envelope.output = result
                envelope.success = True
                logger.info(f"Tool '{func.__name__}' completed successfully")

            except Exception as e:
                envelope.error = str(e)
                envelope.success = False
                logger.exception(f"Tool '{func.__name__}' failed: {e}")

            finally:
                envelope.completed_at = datetime.now(UTC).isoformat()

            return envelope

        return wrapper


##################################################################
# SYSTEM CONTEXT
##################################################################
class SystemContext:
    def __init__(self, template_repo: str, workspace_name: str, agent_manager: AgentManager):
        # Only setup synchronous variables here
        self.template_repo = Path(template_repo)
        self.workspace_path = WORKSPACES_ROOT / workspace_name
        self.agent_manager = agent_manager
        self.data_manager = DataManager(agent_manager)
        self.tool_manager = ToolManager(agent_manager)

        self.manifests: Dict[str, Any] = {}

    @classmethod
    async def create(cls, template_repo: str, workspace_name: str, agent_manager: AgentManager):
        """
        The proper way to instantiate SystemContext asynchronously.
        """
        logger.info("Initializing SystemContext via Async Factory")
        instance = cls(template_repo, workspace_name, agent_manager)

        # 1. Load Manifest
        await cls.load_manifest(instance)
                
        # 2. Async registration For Tool
        await instance.tool_manager.scan_and_register_tools()

        # 3. ASync registration For Data Schema
        await instance.data_manager.register_schema(instance.manifests)

        # 4. Async registration For Governance
        await instance.tool_manager.register_governance_policy(instance.manifests)


        return instance

    async def load_manifest(self) -> None:

        self.manifest_dir = self.workspace_path / "tools" / "spec"

        logger.info(f"Scanning Manifest {self.manifest_dir}")

        if not self.manifest_dir.exists() or not self.manifest_dir.is_dir():
            raise ValueError(f"Invalid agent base path: {self.manifest_dir}")

        for manifest_file in self.manifest_dir.iterdir():
            if manifest_file.suffix != ".yaml": # Avoid temp files or __pycache__
                continue
            try:
                tool_name = manifest_file.stem
                logger.info(f"Reading manifest for tool ({tool_name}) from {manifest_file}") 
                manifest_result = AgentProfiler._load_manifest(manifest_file) 
                if manifest_result.get("success"):
                    self.manifests[tool_name] = manifest_result.get("manifest")
                    logger.info(f"Tool Manifest: { self.manifests[tool_name]}")
                else:
                    raise Exception(manifest_result.get("error"))

            except Exception as e:
                logger.error(f"Failed to load manifest for tool ({tool_name}) from {manifest_file.name}: {e}", exc_info=True)

        logger.info(f"Tool Manifest scan complete. Total loaded manifests: {len(self.manifests)}")

    def get_runtime_tools(self):
        logger.debug("Collecting runtime tool schemas for LLM binding")
        schemas = [adapter.get_schema() for adapter in self.tool_manager.tool_map.values()]
        logger.info(f"Exposed {len(schemas)} tools to runtime")
        return schemas



################################## SAMPLE INPUT PAYLOAD FOR MCP TOOLS
from llm.model_manager import ModelManager

async def get_sample_payload(tool_name: str, user_intent: str):
    if tool_name == "get_market_regime_data":
        _output = await ToolAdapter.mcp_xhttp_caller(_URL_XHTTP, 'fetch_alpaca_market')
        logger.info(f"Result: {_output}")
        if _output.get("status") == "success":
            success = True
            error = None
            market_data =  _output.get("output")
        else:
            market_data = None
            success = False
            error = _output.get("message")
            logger.exception(f"Tool execution failed: {error}")

        logger.info(f"Result: {market_data}")
        return market_data
    if tool_name == "analyze_earnings_call":
        return {
        "ticker": "NVDA"
        }
    if tool_name == "calculate_var":
        return {
        "ticker": "NVDA",
        "position_size": 25000.00
        }
    if tool_name == "execute_trade":    
        return {
        "ticker": "NVDA",
        "side": "BUY",
        "qty": 135,
        "order_type": "LIMIT"
        }
    if tool_name == "get_gas_fees":  
        return {
        "network": "polygon"
        }
    if tool_name == "get_ticker_stats":  
        return {
        "ticker": "AAPL"
        }
    if tool_name == "search_macro_news":  
        return {
        "query": "CPI Inflation Data"
        }
    if tool_name == "search_ticker_news":  
        logger.info(f"[Search Ticker News] fetch input ticker first (extract_ticker), with payload: {user_intent}")
        _output = await ToolAdapter.mcp_xhttp_caller(_URL_XHTTP, 'extract_ticker', { "user_intent" : user_intent } )
        logger.info(f"Result: {_output}")
        if _output.get("status") == "success":
            success = True
            error = None
            ticker = _output.get("output")
        else:
            ticker = None
            success = False
            error = _output.get("message")
            logger.exception(f"Tool execution failed: {error}")

        logger.info(f"Result: {ticker}")
        return ticker

        #articles = search_ticker_news("TSLA")
        #return await classify_news(articles)
        #ticker = await extract_ticker(user_intent)
        #logger.info(f"Ticker: {ticker}")
        #return ticker


    return ""


'''
from runtime.config_api_manager import ConfigApiManager

cfg = ConfigApiManager()
_API_KEY = cfg.api_key
_API_SECRET = cfg.api_secret



from macro_services.macro_market import  HTTPMarketDataProvider, MacroMarketDataService
def fetch_alpaca_market():
    provider = HTTPMarketDataProvider(
        api_key=_API_KEY,
        api_secret=_API_SECRET
    )
    
    macro_service = MacroMarketDataService(provider)

    macro_payload = macro_service.fetch_macro_market_data()

    logger.info(f"Macro Payload: {macro_payload}")

    logger.info("SystemContext initialization complete")     

    return macro_payload

from macro_services.alpaca_news_provider import  AlpacaNewsProvider
def search_ticker_news(ticker: str):
    # To Call: asyncio.run(run_news_analysis("AAPL"))

    # 1. Instantiate the class (creates the connection)
    provider = AlpacaNewsProvider( api_key=_API_KEY, api_secret=_API_SECRET)
    
    # 2. Invoke the specific method
    # This returns the DataEnvelope we designed earlier
    envelope = provider.get_ticker_news(ticker, limit=3)
    logger.info(f"Completed News Search: {envelope}")
    # 3. Use the data
    if envelope["metadata"]["status"] == "success":
        articles = envelope["payload"]["articles"]
        for news in articles:
            logger.info(f"Found: {news['headline']} ({news['timestamp']})")
        return articles
    else:
        logger.info(f"Error: {envelope['metadata']['details']}")

    return []

from macro_services.sentiment_classifiers import  SentimentClassifier, MarketSentiment, EmotionSentiment
async def classify_news(articles: list) -> list:

    llm = ModelManager.spin_model()

    classifier = SentimentClassifier(llm_client=llm)

    sentiments = []

    for article in articles:

        content = classifier.fetch_content(article["url"])

        result = await classifier.classify(
            headline=article["headline"],
            content=content,
            sentiment_enum=MarketSentiment
        )
        content = { 'headline': article["headline"], 'sentiment' : result.content }
        logger.info(f"Classified header: {content}")
        sentiments.append(content)

    return { 'headlines' : sentiments }

from macro_services.ticker_extractor import  TickerExtractor
async def extract_ticker(user_intent: str):
    llm = ModelManager.spin_model()
    extractor = TickerExtractor(llm)
    result = await extractor.extract(user_intent)
    return { 'ticker' : result.content }
'''