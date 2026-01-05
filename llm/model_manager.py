# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/model_manager.py
#
# Description:
#
#   ModelManager orchestrates LLMs and memory for production-grade use:
#     - Handles primary and fallback chat models
#     - Integrates with MemoryManager for semantic and episodic memories
#     - Supports optional schema validation
#     - Supports reward-based persistence, memory decay, summarization
#     - Self-reflection
#     - Async-first API
#
# User/Agent --> ModelManager.generate(prompt)
#    |
#    ├─> MemoryManager.retrieve_semantic()  # fetch context
#    ├─> LLM generates response
#    ├─> MemoryManager.save_semantic()      # save prompt+response, update reward/decay
#    └─> ModelManager._self_reflect()       # optional reflection, saves to episodic store
#
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Project: Agentic System
# File: llm/model_manager.py
#
# Description:
#
#   ModelManager orchestrates LLMs and memory for production-grade use:
#     - Handles primary and fallback chat models
#     - Integrates with MemoryManager for semantic and episodic memories
#     - Supports reward-based persistence, memory decay, summarization
#     - Self-reflection
#     - Async-first API
#
# Author: Raymond M.O. Ordona
# Created: 2026-01-01
# Copyright:
#   © 2026 Raymond M.O. Ordona. All rights reserved.
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Tuple, Any
from datetime import datetime

from llm.chatmodels.chatmodel_factory import ChatModelFactory
from llm.embeddings.embedding_factory import EmbeddingFactory
from llm.stores.store_factory import StoreFactory
from llm.memory_manager import MemoryManager
from langgraph.store.memory import InMemoryStore

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

class ModelManager:
    def __init__(
        self,
        chatmodel_provider: str,
        embedding_provider: str,
        store_provider: str,
        llm_config: str
    ):

        self.chatmodel_provider = chatmodel_provider
        self.embedding_provider = embedding_provider
        # -----------------------
        # 1. Embeddings
        # -----------------------
        logger.info("Loading Embedding Factory")
        EmbeddingFactory.load_config(llm_config / "embeddings/config.json")
        self.embedding_client = EmbeddingFactory.get(embedding_provider)

        # -----------------------
        # 2. Stores
        # -----------------------
        logger.info("Loading Store Factory")
        StoreFactory.load_config(llm_config / "stores/config.json")
        self.store = StoreFactory.get(store_provider, self.embedding_client) 

        logger.info(f"Loading reflection prompt")
        self.reflection_prompt = StoreFactory.load_reflection_prompt()

        # -----------------------
        # 3. MemoryManager
        # -----------------------
        logger.info("Initializing Memory Manager")
        self.memory_manager = MemoryManager(
            embedding_client = self.embedding_client,
            store = self.store
        )

        # -----------------------
        # 4. ChatModels
        # -----------------------
        # Load chatmodel config once at platform startup
        logger.info("Loading Chat Model Factory")
        ChatModelFactory.load_config(llm_config / "chatmodels/config.json")
        self.llm = ChatModelFactory.get(chatmodel_provider)


    # -----------------------
    # Get Memory Store
    # -----------------------
    def get_store(self):
        if self.memory_manager:
            return self.memory_manager
        raise RuntimeError("Memory Manager not initialized.")
        
    # -----------------------------------------------------------------------------
    # Generate a response from the LLM with optional memory augmentation and persistence.
    #
    # This function implements a production-grade, memory-aware LLM call in the Agentic System.
    # It handles the following steps:
    #
    # 1. Semantic Memory Retrieval
    #    - If `memory_key` is provided, retrieve the top-k relevant semantic memories 
    #      from the MemoryManager that match the current prompt.
    #    - This provides context for the LLM, ensuring multi-turn continuity and 
    #      informed responses.
    #
    # 2. Contextual Prompt Construction
    #    - Prepend the retrieved memories to the prompt.
    #    - The prompt now includes both prior relevant information and the user query, 
    #      allowing the LLM to generate consistent and contextually aware answers.
    #
    # 3. LLM Invocation
    #    - Call the underlying LLM asynchronously to generate a response based on 
    #      the augmented prompt.
    #    - Supports streaming or non-streaming models depending on the LLM implementation.
    #
    # 4. Memory Persistence (Optional)
    #    - If `persist` is True and a `memory_key` is provided, save the prompt + 
    #      response as a semantic memory in MemoryManager.
    #    - Optionally, include a `reward` parameter to indicate usefulness, correctness,
    #      or importance. This helps prioritize high-value memories during retrieval.
    #
    # 5. Self-Reflection (Optional)
    #    - After persisting, invoke the agent's self-reflection mechanism.
    #    - This can generate internal reasoning, summaries, or annotations to augment
    #      the stored memory for better future retrieval and reasoning.
    #
    # Parameters:
    # -----------
    # prompt : str
    #     The user input or query to generate a response for.
    # memory_key : Optional[str]
    #     Key under which to store/retrieve related semantic memories.
    # top_k : int
    #     Number of relevant memories to retrieve and prepend to the prompt.
    # persist : bool
    #     Whether to save the prompt + response to semantic memory.
    # reward : Optional[float]
    #     Numeric reward score for the memory entry, used for prioritization.
    #    
    # Returns:
    # --------
    # response : str
    #     The generated LLM output, possibly influenced by retrieved semantic memories.
    #
    # Usage Example:
    # --------------
    # response = await model_manager.generate(
    #     prompt="Explain agentic systems.",
    #     memory_key="user_123_session_01",
    #     top_k=5,
    #     persist=True,
    #     reward=0.9
    # )
    #
    # Notes:
    # ------
    # - Step 1 ensures the LLM has access to prior relevant knowledge, preventing 
    #   stateless, isolated responses.
    # - `metadata` in stored memory can include role, session, or topic, supporting 
    #   filtered retrieval.
    # - `document` in stored memory can capture LLM reasoning, self-reflection, or 
    #   auxiliary context after generation.
    # -----------------------------------------------------------------------------
    async def generate(
        self,
        prompt: str,
        namespace: Tuple[str, str] = None,
        metadata: Dict[str, Any] = None,
        persist: bool = True,
        top_k: int = 5,
        reward: Optional[float] = None,
    ) -> str:
        """
        Generate text from LLM while automatically:
        - Retrieving relevant semantic memories
        - Prepending context to prompt
        - Persisting new semantic memory (auto-embedding)
        - Reward tracking, decay, summarization
        - Self-reflection (stores reflection in episodic store)
        """

        logger.info("Performing  (RAG)")
        # 1. Retrieve relevant semantic memories
        logger.info(f"RAG: Start with Retrieval (using {self.embedding_provider})...")
        context_memories = []
        if namespace:
            context_memories = await self.memory_manager.retrieve_semantic(
                namespace=namespace,
                query=prompt,
                top_k=top_k,
                metadata_filter=None
            )

        # 2. Prepend retrieved memories to prompt
        logger.info("RAG: Now, augmenting retrieved context ...")
        if context_memories:
            context_text = "\n".join([m["text"] for m in context_memories])
            prompt = f"{context_text}\n\n{prompt}"

        # 3. Call LLM
        logger.info(f"RAG: Finally, generating response (using {self.chatmodel_provider})...")

        message = [ {"role" : "user", "content" : prompt } ]
        logger.info(f"Prompt: {message}")

        response = await self.llm.ainvoke(message)

        logger.info(f"LLM Response: {response}")

        # 4. Persist semantic memory (prompt + response)
        logger.info("Now saving response to memory ...")

        interaction_text = f"Prompt: {message}\nResponse: {response}"
        if persist and namespace:
            await self.memory_manager.save_semantic(
                namespace=namespace,
                key="last_query",
                text=interaction_text,
                metadata=metadata,
                reward=reward
            )

        # 5. Self-reflection on saved memory
        # This is combining user message and LLM response
        await self._self_reflect( namespace=namespace, key="last_query", text=interaction_text)


        return response

    # ----------------------------
    # Self-Reflection (ModelManager)
    # ----------------------------
    async def _self_reflect(
        self,
        namespace: Tuple[str, str],
        key: str,
        text: str,
    ):
        """
        Perform LLM-based self-reflection on generated content and persist
        the reflection as episodic memory.

        Reflection is treated as:
        - Non-semantic (raw episodic data)
        - Post-hoc analysis
        - Immutable historical record

        Args:
            namespace: Logical namespace (e.g. ("session", session_id))
            key: Base memory key being reflected on
            text: The text to reflect upon (prompt + response)
        """

        if not self.llm or not self.memory_manager:
            return

        try:
            # -----------------------------
            # 1. Invoke reflection prompt
            # -----------------------------
            messages = [
                {"role": "system", "content": self.reflection_prompt},
                {"role": "user", "content": text},
            ]

            logger.info("Invoking LLM to generate relflection")
            reflection = await self.llm.ainvoke(messages)

            # -----------------------------
            # 2. Persist as episodic memory
            # -----------------------------
            await self.memory_manager.save_episode(
                namespace=namespace,
                key=f"{key}:reflection",
                data={
                    "reflection": reflection,
                    "source_key": key,
                    "created_at": datetime.utcnow().isoformat(),
                },
                metadata={
                    "type": "self_reflection",
                    "origin": "model_manager",
                },
                document={
                    "reflected_text": text,
                },
            )

        except Exception as e:
            logger.warning(f"Self-reflection failed for {key}: {e}")
