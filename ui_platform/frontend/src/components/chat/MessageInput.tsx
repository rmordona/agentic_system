import React, { useState } from "react";
import "@/styles/messageinput.css"; // centralized CSS

interface Props {
  onSend: (message: string) => Promise<void>;
  disabled?: boolean;
}

const MessageInput: React.FC<Props> = ({ onSend, disabled = false }) => {
  const [input, setInput] = useState("");

  const handleSend = async () => {
    if (!input.trim()) return;
    console.log("handleSend fired", input);
    await onSend(input);
    setInput("");
  };

  return (
    <div className="message-input-container">
      <input
        className="message-input-field"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your message..."
        disabled={disabled}
      />
      <button
        className="message-input-button"
        onClick={handleSend}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  );
};

export default MessageInput;