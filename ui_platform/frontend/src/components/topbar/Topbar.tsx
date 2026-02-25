import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import "@/styles/topbar.css";

interface TopbarProps {
  activeTab?: string;
  setActiveTab?: (tab: string) => void;
  mode?: "engineering" | "production";
  setMode?: (mode: "engineering" | "production") => void;
  onSignoutClick: () => void; // parent clears auth
}

const Topbar: React.FC<TopbarProps> = ({
  activeTab,
  setActiveTab,
  mode,
  setMode,
  onSignoutClick,
}) => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <div className="topbar-container">
        {/* Left tabs */}
        <div className="topbar-left">
          {setActiveTab && activeTab && (
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="home">Home</TabsTrigger>
                <TabsTrigger value="category">Category</TabsTrigger>
                <TabsTrigger value="mode">Mode</TabsTrigger>
              </TabsList>
            </Tabs>
          )}
        </div>

        {/* Center mode buttons */}
        <div className="topbar-center">
          {mode && setMode && (
            <>
              <Button
                variant={mode === "engineering" ? "default" : "outline"}
                onClick={() => setMode("engineering")}
              >
                Engineering
              </Button>
              <Button
                variant={mode === "production" ? "default" : "outline"}
                onClick={() => setMode("production")}
              >
                Production
              </Button>
            </>
          )}
        </div>

        {/* Right sign out */}
        <div className="topbar-right">
          <Button
            onClick={() => setShowDialog(true)}
            className="bg-red-600 hover:bg-red-700"
          >
            Sign Out
          </Button>
        </div>
      </div>

      {/* Modal */}
      {showDialog && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Confirm Sign Out</h3>
            <p>Are you sure you want to sign out?</p>
            <div className="modal-buttons flex justify-center gap-4 mt-4">
              <Button
                onClick={() => {
                  setShowDialog(false);
                  onSignoutClick(); // PlatformLayout handles clearing auth
                }}
                className="bg-red-600 hover:bg-red-700"
              >
                Yes, Sign Out
              </Button>
              <Button
                onClick={() => setShowDialog(false)}
                className="bg-gray-300 hover:bg-gray-400"
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Topbar;