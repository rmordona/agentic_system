import React, { useState } from "react";
import "@/styles/engineeringpanel.css"; // centralized CSS

const EngineeringPanel = () => {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tools, setTools] = useState("");
  const [notes, setNotes] = useState("");

  return (
    <div className="engineering-panel">
      <h2>Artifacts</h2>

      <label>System Prompt</label>
      <textarea
        placeholder="Define system behavior..."
        value={systemPrompt}
        onChange={(e) => setSystemPrompt(e.target.value)}
      />

      <label>Tools</label>
      <textarea
        placeholder="List tools..."
        value={tools}
        onChange={(e) => setTools(e.target.value)}
      />

      <label>Notes</label>
      <textarea
        placeholder="Add notes..."
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
    </div>
  );
};

export default EngineeringPanel;