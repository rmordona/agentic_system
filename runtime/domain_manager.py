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
from jsonschema import validate, ValidationError

from pathlib import Path
from datetime import datetime, UTC
from typing import Any, TypedDict, Dict, Optional, List, Generic, TypeVar, get_args, get_origin, Union
from typing_extensions import Literal

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, create_model
from pydantic_core import PydanticUndefined
from functools import wraps

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

from runtime.tools.mcp_client import MCPClient
from runtime.tools.mcp_manager import MCPManager

from runtime.artifact_factory import ArtifactSchema

from runtime.agent_manager import AgentManager
from runtime.agent_profiler import AgentOutput, AgentProfiler



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

##################################################################
# DATA ENVELOPE
##################################################################


class DataEnvelope(BaseModel, Generic[DomainType]):
    agent: str
    type: str
    version: str
    producer: str
    stage: str
    created_at: datetime
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
                agent_name: str, 
                schema_class: type[DomainType]):
        self.agent_name = agent_name
        self.payload_schema = schema_class
        logger.info(f"DataAdapter initialized for agent '{agent_name}'")

    def create_envelope(
        self,
        payload:  Union[DomainType, dict],
        producer: str,
        stage: str
    ) -> DataEnvelope[DomainType]:
        logger.info(
            f"Creating DataEnvelope | domain={self.agent_name} producer={producer} stage={stage}"
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
            agent=self.agent_name,
            type=self.payload_schema.__name__.lower(),
            version="1.0",
            producer=producer,
            stage=stage,
            created_at=datetime.now(UTC),
            payload=payload_model,   
            checksum=checksum
        )

        logger.info(
            f"DataEnvelope created | domain={envelope.agent} checksum={checksum}"
        )
        return envelope

class DataManager:
    def __init__(self, agent_manager: AgentManager):

        self.agent_manager = agent_manager

        self.domain_map: Dict[str, DataAdapter] = {}
        logger.info(f"DataManager initialized")

    def scan_and_register_schema(self):
        logger.info("Scanning schema domains for registered agents")

        agents = self.agent_manager.list_agents()

        for agent_name in agents:
            logger.info(f"Agent name: {agent_name}")
            profile = self.agent_manager.get_agent_profile(agent_name)
            logger.info(f"Agent Profile: name={profile.name}, role={profile.role}")
            logger.info(f"Agent Input Schema: {profile.input_schema}")

            schema = {
                "type": "object",
                "required": ["input", "output"],
                "properties": {
                    "input": profile.input_schema,
                    "output": profile.output_schema,
                },
                "definitions": {
                    **profile.input_schema.get("definitions", {}),
                    **profile.output_schema.get("definitions", {}),
                },
                "additionalProperties": False,
            }

            definitions = profile.input_schema.get("definitions", {})  # <-- extract definitions here

            logger.info(f"Definition exists: {definitions}")

            try:

                # 1. Usage in your Pipeline
                DynamicAgentSchema: Type[DomainType] = SchemaFactory.create_class_from_json(f"{agent_name}Schema", schema, schema.get("definitions, {})"))

                logger.info(f"Dynamic Agent Model: {DynamicAgentSchema}")

                if not DynamicAgentSchema:
                    logger.warning(f"Schema class '{DynamicAgentSchema}'")
                    continue

                self.domain_map[agent_name] = DataAdapter(
                    agent_name=agent_name,
                    schema_class=DynamicAgentSchema # This is a schema class [type(DomainType)]
                )

                logger.info(f"Successfully registered data schema for '{agent_name}'")

            except Exception as e:
                logger.exception(f"Failed to load data for agent '{agent_name}': {e}")


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
        adapter = self.domain_map.get(agent_name)
        if not adapter:
            logger.error(f"DataAdapter not found for agent '{agent_name}'")
        return adapter

    def get_initial_envelope(self, agent_name: str) -> DataEnvelope:
        """
        Leverages the registered DataAdapter to create a type-safe starting envelope.
        """
        # 1. Retrieve the adapter we found during scan_and_register
        adapter = self.domain_map.get(agent_name)

        logger.info(f"Data Adapter for the given agent '{agent_name}': {adapter}")

        if not adapter:
            raise ValueError(f"Critical Error: Data agent '{agent_name}' is not registered.")

        # 2. Use the adapter to create the envelope.
        # Passing an empty dict {} triggers the Pydantic schema's default values.
        # Producer is 'system' because this is the mission's 'Genesis' block.
        instantiated_schema = self.instantiate_with_defaults(adapter.payload_schema)
        initial_payload_dict = instantiated_schema.model_dump() # converts into a dict

        logger.info(
            f"Instantiated default payload | "
            f"type={type(instantiated_schema)} "
            f"values={initial_payload_dict}"
        )

        try:
            initial_envelope = adapter.create_envelope(
                payload=initial_payload_dict, 
                producer="system/genesis", 
                stage="init"
            )
            return initial_envelope
        except ValueError as e:
            logger.error(f"Critical Error: Data domain '{agent_name}' schema, {e}")


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
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None
    success: bool = False
    validation_rules: Optional[List[str]] = None
    stage_exit_trigger: Optional[str] = None


class ToolAdapter:
    def __init__(self, name: str, description: str, schema: dict, tool_file: Path):
        self.name = name
        self.description = description
        self.parameters = schema  # The MCP inputSchema (e.g., ticker, qty)
        self.tool_file = tool_file
        # self.mcp_caller = mcp_caller # The logic to run the MCP command

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
        mcp_payload = instruction.get("payload", {}) 
  
        logger.info(f"Tool Adapter Parameters: {self.parameters}")

        try:
            # We call the mcp_caller (the bridge we built) 
            # using the arguments extracted from the instruction
            _input, output = await self.mcp_caller(self.tool_file, tool_name, mcp_payload)
            success = True
            error = None
        except Exception as e:
            output = None
            success = False
            error = str(e)
            logger.exception(f"Tool execution failed: {e}")

        logger.info(f"Execution Completed ...")


        logger.info(f"Wrapping output into a ToolEnvelope")
        logger.info(f"Tool Adapter parameter: {self.parameters}")

        props = self.parameters.get("properties", {})
        validation_rules = props.get("validation_rules")
        stage_exit_trigger = props.get("stage_exit_trigger")

        logger.info(f"Validation Rules: {validation_rules}")
        logger.info(f"Stage Exit Trigger: {stage_exit_trigger}")
        return ToolEnvelope(
            id=generate_uuid(),
            tool_name=tool_name,
            agent_role=agent_role,
            stage=stage,
            intent=instruction.get("task_description", self.description),
            input=_input, # We log the specific tool args, not the whole instruction
            output=output,
            error=error,
            started_at=start_time,
            completed_at=datetime.now(UTC).isoformat(),
            success=success,
            validation_rules=validation_rules,
            stage_exit_trigger=stage_exit_trigger
        )

    async def mcp_caller(self, tool_file: Path, tool_name: str, payload: dict):
        """
        The bridge logic. Now with session persistence to keep 
        the 'Agnostic OS' snappy.
        """
        logger.info(f"Entering the mcp caller: {tool_name} for {tool_file}")
        logger.info(f"Arguments: {payload}")

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

        # Validate and Reconstruct Payload
        input_args = self.construct_and_validate_mcp_payload(self.parameters, payload)

        logger.info(f"Payload: {payload}")
        logger.info(f"Input Args: {input_args}")
        # 3. Call the tool.  This finally executes the function inside your script 
        # and returns the list of content (text, images, or JSON) back to your ToolAdapter.
        logger.info(f"Now Calling the tool {tool_name} with the following payload: {input_args}")
        result = await session.call_tool(tool_name, arguments=input_args)
        logger.info(f"Received result: {result.content}")
        return input_args, result.content

    # --- Application in your code ---
    # Suppose the Agent only provides: {"ticker": "AAPL"}
    # And the contract for 'execute_trade' has a default order_type: "LIMIT"
    # Usage:
    #    final_args = construct_and_validate_mcp_payload(trade_contract, {"ticker": "AAPL", "qty": 10, "side": "BUY"})
    #
    # Now the call is safe and complete:
    # result = await session.call_tool("execute_trade", arguments=final_args)
    def construct_and_validate_mcp_payload(self, schema_node: dict, payload: dict = None) -> dict:
        if payload is None:
            payload = {}
            
        # NORMALIZE SCHEMA: Handle the nesting issue
        # If we are looking at the root contract, dive into properties -> input_schema
        if "properties" in schema_node and "input_schema" in schema_node["properties"]:
            schema_node = schema_node["properties"]["input_schema"]
        # Or if we were passed the input_schema wrapper directly
        elif "input_schema" in schema_node:
            schema_node = schema_node["input_schema"]

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
            # The core of the issue: ensure we are looking at the 'properties' of the schema object
            if node.get("type") == "object":
                obj = {}
                props = node.get("properties", {})
                required = node.get("required", [])

                for key, sub_schema in props.items():
                    current_path = f"{path}.{key}"
                    
                    # Extraction
                    val = data.get(key) if isinstance(data, dict) else None
                    if val is None:
                        val = sub_schema.get("default")
                    
                    # Validation
                    if val is None and key in required:
                        raise ValueError(f"Missing required field: '{current_path}'")

                    if val is not None:
                        validate_constraints(val, sub_schema, current_path)
                        
                        if sub_schema.get("type") == "object":
                            # Recurse with the nested data slice
                            obj[key] = build(sub_schema, val or {}, current_path)
                        else:
                            obj[key] = val
                return obj
            return {} # Return empty dict instead of None

        return build(schema_node, payload)

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

    async def scan_and_register_tools(self, workspace_path: Path) -> None:
        self.tools_dir = workspace_path / "tools" / "mcp"

        logger.info(f"Scanning for agents tools {self.tools_dir}")

        if not self.tools_dir.exists() or not self.tools_dir.is_dir():
            raise ValueError(f"Invalid agent base path: {self.tools_dir}")

        for tool_file in self.tools_dir.iterdir():
            if tool_file.suffix != ".py": # Avoid temp files or __pycache__
                continue

            try:
                logger.info(f"Reading tools from {tool_file}")
                # Registry is the list of dicts we just got working
                registry = await self.extract_tools_via_protocol(tool_file)

                for tool_data in registry:
                    # Create the adapter
                    adapter = ToolAdapter(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        schema=tool_data["arguments"],
                        tool_file=tool_file,
                        # mcp_caller=self.call_mcp_tool
                    )
                    
                    # Register in the map
                    self.tool_map[adapter.name] = adapter
                    
                logger.info(f"Successfully registered {len(registry)} tools from {tool_file.name}")

            except Exception as e:
                logger.error(f"Failed to register tools from {tool_file.name}: {e}", exc_info=True)

        logger.info(f"Agent scan complete. Total registered tools: {len(self.tool_map)}")

    async def scan_and_register_tools_spec(self, workspace_path: Path) -> None:
        self.tools_spec_dir = workspace_path / "tools" / "spec"

        logger.info(f"Scanning for agents tools spec {self.tools_spec_dir}")

        if not self.tools_spec_dir.exists() or not self.tools_spec_dir.is_dir():
            raise ValueError(f"Invalid agent base path: {self.tools_spec_dir}")

        for tool_spec_file in self.tools_spec_dir.iterdir():
            if tool_spec_file.suffix != ".yaml": # Avoid temp files or __pycache__
                continue
            try:
                tool_name = tool_spec_file.stem
                logger.info(f"Reading tools spec ({tool_name}) from {tool_spec_file}") 
                schema_result = AgentProfiler._load_schema(tool_spec_file)
                logger.info(f"Schema Result: {schema_result}")
                if schema_result.get("success"):
                    self.input_schema = schema_result.get("schema")
                    self.tool_map[tool_name].parameters = self.input_schema
                    logger.info(f"Tool Adapter: {self.tool_map[tool_name]}")
                else:
                    raise Exception(schema_result.get("error"))

            except Exception as e:
                logger.error(f"Failed to register tools from {tool_spec_file.name}: {e}", exc_info=True)

        logger.info(f"Tool Spec scan complete. Total registered tools spec: {len(self.tool_map)}")

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

    def list_available_tools(self):
        keys = self.tool_map.keys()
        result = ", ".join(keys)
        return result

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

    def get_initial_envelope(self, agent_name: str) -> ToolEnvelope:
        """
        Leverages the registered DataAdapter to create a type-safe starting envelope.
        """
        # 1. Retrieve the adapter we found during scan_and_register
        adapter = self.tool_map.get(agent_name)


##################################################################
# SYSTEM CONTEXT
##################################################################

class SystemContext:
    def __init__(self, template_repo: str, workspace_path: str, agent_manager: AgentManager):
        # Only setup synchronous variables here
        self.template_repo = Path(template_repo)
        self.workspace_path = Path(workspace_path)
        self.agent_manager = agent_manager
        self.data_manager = DataManager(agent_manager)
        self.tool_manager = ToolManager(agent_manager)

    @classmethod
    async def create(cls, template_repo: str, workspace_path: str, agent_manager: AgentManager):
        """
        The proper way to instantiate SystemContext asynchronously.
        """
        logger.info("Initializing SystemContext via Async Factory")
        instance = cls(template_repo, workspace_path, agent_manager)
        
        # 1. Sync registration For Data
        instance.data_manager.scan_and_register_schema()
        
        # 2. Async registration For Tool 
        await instance.tool_manager.scan_and_register_tools(instance.workspace_path)

        # 3. Async registration For Tool Spec
        await instance.tool_manager.scan_and_register_tools_spec(instance.workspace_path)
        
        logger.info("SystemContext initialization complete")
        return instance

    def get_runtime_tools(self):
        logger.debug("Collecting runtime tool schemas for LLM binding")
        schemas = [adapter.get_schema() for adapter in self.tool_manager.tool_map.values()]
        logger.info(f"Exposed {len(schemas)} tools to runtime")
        return schemas