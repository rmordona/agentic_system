import React, { useState } from "react";
import "@/styles/engineeringpanel.css"; // centralized CSS

const EngineeringPanel = () => {
  // Assuming these are your state handlers
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tools, setTools] = useState("");
  const [notes, setNotes] = useState("");

  const handleGenerate = (type, content) => {
    console.log(`Generating .md for ${type}...`);
    // Logic to format content as Markdown and trigger download/save
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${type.replace(/\s+/g, '_').toLowerCase()}.md`;
    link.click();
  };

  return (
    <div className="engineering-panel">
      <h2>Artifacts</h2>

      <div className="artifact-section">
        <div className="label-row">
          <label>Stage Pipelines</label>
          <button 
            className="gen-btn" 
            onClick={() => handleGenerate("Stage Pipelines", systemPrompt)}
          >
            Generate .md
          </button>
        </div>
        <textarea
          placeholder="Generate Stage Pipeline"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
        />
      </div>

      <div className="artifact-section">
        <div className="label-row">
          <label>Stage Agents</label>
          <button 
            className="gen-btn" 
            onClick={() => handleGenerate("Stage Agents", tools)}
          >
            Generate .md
          </button>
        </div>
        <textarea
          placeholder="Generate Agents per Stage"
          value={tools}
          onChange={(e) => setTools(e.target.value)}
        />
      </div>

      <div className="artifact-section">
        <div className="label-row">
          <label>MCP Tools & Predicates</label>
          <button 
            className="gen-btn" 
            onClick={() => handleGenerate("MCP Tools", notes)}
          >
            Generate .md
          </button>
        </div>
        <textarea
          placeholder="Generate MCP Tools, Predicates, etc."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
    </div>
  );
};

export default EngineeringPanel;