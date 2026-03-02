import React, { useState } from "react";
import "@/styles/messageinput.css";

interface Props {
  onSend: (message: string) => void;
  onApprove?: () => void;
  onReject?: () => void;
  disabled?: boolean;
  isWaitingForHuman?: boolean;
}

const MessageInput: React.FC<Props> = ({
  onSend,
  onApprove,
  onReject,
  disabled = false,
  isWaitingForHuman = false,
}) => {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput("");
  };

  return (
    <div className="message-input-container">
      {/* ========================================
          HITL Approval Mode
         ======================================== */}
      {isWaitingForHuman ? (
        <div className="hitl-actions">
          <button
            className="approve-button"
            onClick={onApprove}
            disabled={disabled}
          >
            Approve
          </button>
          <button
            className="reject-button"
            onClick={onReject}
            disabled={disabled}
          >
            Reject
          </button>
        </div>
      ) : (
        <>
          <input
            className="message-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={disabled}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />
          <button
            className="message-input-button"
            onClick={handleSend}
            disabled={disabled}
          >
            Send
          </button>
        </>
      )}
    </div>
  );
};

export default MessageInput;