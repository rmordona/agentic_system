# runtime/reload_manager.py

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict
from runtime.workspace_loader import WorkspaceLoader
from runtime.graph_manager import GraphManager
from runtime.logger import AgentLogger

class ReloadManager:
    """
    Watches for workspace artifact changes and reloads dynamically.
    Supports single or multi-workspace setups.
    """

    def __init__(
        self,
        workspace_loaders: Dict[str, WorkspaceLoader],
        graph_manager: GraphManager,
        interval_seconds: int = 30,
    ):
        """
        Args:
            workspace_loaders: dict of workspace_name -> WorkspaceLoader
            graph_manager: GraphManager instance for invalidation
            interval_seconds: polling interval for reload check
        """
        self.workspace_loaders = workspace_loaders
        self.graph_manager = graph_manager
        self.interval_seconds = interval_seconds
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False

        # Initialize loggers per workspace
        self.loggers = {
            ws_name: AgentLogger.get_logger(
                workspace=ws_name,
                component="reload_manager"
            )
            for ws_name in workspace_loaders.keys()
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_periodic_reload(self):
        """Starts periodic monitoring of workspace artifacts."""
        if self._running:
            return
        self._running = True
        for ws_name in self.workspace_loaders.keys():
            task = asyncio.create_task(self._watch_workspace(ws_name))
            self._tasks[ws_name] = task

    def stop_periodic_reload(self):
        """Stops monitoring and cancels all tasks."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    # -------------------------------------------------------------------------
    # Internal watchers
    # for this to be effective, we take the checksum hash of the
    # static directory. thus the reason, logs should be outside the workspace
    # -------------------------------------------------------------------------

    async def _watch_workspace(self, ws_name: str):
        """Watches a single workspace for changes."""
        loader = self.workspace_loaders[ws_name]
        logger = self.loggers[ws_name]

        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                new_hash = loader._compute_version_hash()
                if loader.version_hash != new_hash:
                    logger.info(f"Detected changes in workspace '{ws_name}', reloading...")
                    await self._reload_workspace(ws_name, loader)
                    loader.version_hash = new_hash
            except asyncio.CancelledError:
                logger.info(f"Stopping workspace watcher for '{ws_name}'")
                break
            except Exception as e:
                logger.error(f"Error while watching workspace '{ws_name}': {e}")

    async def _reload_workspace(self, ws_name: str, loader: WorkspaceLoader):
        """Performs the actual reload of a workspace and invalidates the graph."""
        logger = self.loggers[ws_name]
        try:
            await loader.load()
            logger.info(f"Workspace '{ws_name}' reloaded successfully.")
            self.graph_manager.invalidate(ws_name)
            logger.info(f"Graph invalidated for workspace '{ws_name}'.")
        except Exception as e:
            logger.error(f"Failed to reload workspace '{ws_name}': {e}")
