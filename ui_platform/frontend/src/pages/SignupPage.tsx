import React, { useState } from "react";
import { api } from "@/services/api";
import { useNavigate } from "react-router-dom";
import "@/styles/signuppage.css";

const SignUpPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors(null);

    if (password !== confirmPassword) {
      setErrors("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await api("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      });

      navigate("/login");
    } catch (err: any) {
      setErrors(err.message || "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <form onSubmit={handleSubmit} className="signup-card">
        <h2>Sign Up</h2>

        {errors && <div className="error">{errors}</div>}

        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? "Signing Up..." : "Sign Up"}
        </button>

        <div className="login-link">
          Already have an account?{" "}
          <button type="button" onClick={() => navigate("/login")}>
            Log In
          </button>
        </div>
      </form>
    </div>
  );
};

export default SignUpPage;