import React from "react";
import "@/styles/ui_components.css";

export const Tabs = ({ children }: { children: React.ReactNode }) => <div className="ui-tabs">{children}</div>;
export const TabsList = ({ children }: { children: React.ReactNode }) => <div className="ui-tabs-list">{children}</div>;
export const TabsTrigger = ({ children, active = false }: { children: React.ReactNode; active?: boolean }) => (
  <button className={`ui-tabs-trigger ${active ? "ui-tabs-trigger-active" : ""}`}>{children}</button>
);