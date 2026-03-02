import React from "react";
import "@/styles/dialog.css";

interface Props {
  message: string | null;
  onClose: () => void;
}

const ErrorDialog: React.FC<Props> = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div className="dialog-overlay">
      <div className="dialog-box">
        <h3>Something went wrong</h3>
        <p>{message}</p>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
};

export default ErrorDialog;
