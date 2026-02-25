import React from "react";
import "@/styles/ui_components.css";

export const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="ui-card">{children}</div>
);

export const CardContent: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="ui-card-content">{children}</div>
);