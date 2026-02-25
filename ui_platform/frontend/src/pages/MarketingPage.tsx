import React from "react";
import Topbar from "@/components/topbar/Topbar";
import "@/styles/marketingpage.css";

const MarketingPage: React.FC = () => {
  return (
    <div className="marketing-page">
      <Topbar showAuthButtonsOnly />

      <main className="marketing-main">
        <h1>Welcome to Context Engineering Platform</h1>
        <p>
          Build, test, and manage your AI context engineering projects seamlessly.
        </p>

        <div className="marketing-buttons">
          <a href="/login" className="sign-in">
            Sign In
          </a>
          <a href="/signup" className="sign-up">
            Sign Up
          </a>
        </div>
      </main>

      <footer className="marketing-footer">
        © 2026 Raymond M.O Ordona. All rights reserved.
      </footer>
    </div>
  );
};

export default MarketingPage;