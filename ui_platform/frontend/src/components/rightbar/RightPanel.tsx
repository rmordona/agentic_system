import React, { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import "@/styles/rightpanel.css";

const RightPanel = () => {
  const [artifacts, setArtifacts] = useState("");
  const [memory, setMemory] = useState("");
  const [metadata, setMetadata] = useState("");

  return (
    <div className="rightpanel">
      <div className="rightpanel-section">
        <h3>Artifacts</h3>
        <Textarea
          value={artifacts}
          onChange={(e) => setArtifacts(e.target.value)}
          placeholder="System prompts, tools, schemas..."
        />
      </div>

      <div className="rightpanel-section">
        <h3>Memory</h3>
        <Textarea
          value={memory}
          onChange={(e) => setMemory(e.target.value)}
          placeholder="Persistent memory..."
        />
      </div>

      <div className="rightpanel-section">
        <h3>Metadata</h3>
        <Textarea
          value={metadata}
          onChange={(e) => setMetadata(e.target.value)}
          placeholder="Request metadata, tracing, tags..."
        />
      </div>
    </div>
  );
};

export default RightPanel;
