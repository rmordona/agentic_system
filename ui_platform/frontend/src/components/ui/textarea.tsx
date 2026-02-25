import React from "react";
import "@/styles/ui_components.css";

export const Textarea: React.FC<React.TextareaHTMLAttributes<HTMLTextAreaElement>> = (props) => (
  <textarea className="ui-textarea" {...props} />
);