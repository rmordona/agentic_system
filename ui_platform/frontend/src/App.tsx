import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import PlatformLayout from "@/layouts/PlatformLayout";
import MarketingPage from "@/pages/MarketingPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import { useAuth } from "@/contexts/AuthContext";

const App = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Router>
      <Routes>
        {/* Landing / marketing page if not logged in */}
        <Route path="/" element={isAuthenticated ? <Navigate to="/app" /> : <MarketingPage />} />

        {/* Login / signup pages */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Full platform for logged-in users */}
        <Route
          path="/app/*"
          element={isAuthenticated ? <PlatformLayout /> : <Navigate to="/login" replace />}
        />

        {/* fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

export default App;