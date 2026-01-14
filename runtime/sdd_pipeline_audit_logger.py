###########################################################################
# HITL / Audit Layer
###########################################################################

import json
from datetime import datetime

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(  component="system")

class PipelineAuditLogger:
    def __init__(self, audit_path: str):
        self.audit_path = audit_path
        self.log = []

    def record_change(self, change_summary: dict):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "change_summary": change_summary
        }
        self.log.append(entry)
        self._persist()

    def _persist(self):
        with open(self.audit_path, "w") as f:
            json.dump(self.log, f, indent=2)

