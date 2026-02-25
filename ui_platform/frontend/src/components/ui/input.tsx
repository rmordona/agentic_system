import React from "react";
import "@/styles/ui_components.css";

export const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = (props) => (
  <input className="ui-input" {...props} />
);