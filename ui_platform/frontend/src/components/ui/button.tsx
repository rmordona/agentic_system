import React from "react";
import "@/styles/ui_components.css";

export const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" }> = ({
  children,
  variant = "default",
  className = "",
  ...props
}) => (
  <button
    className={`ui-button ${variant === "outline" ? "ui-button-outline" : ""} ${className}`}
    {...props}
  >
    {children}
  </button>
);