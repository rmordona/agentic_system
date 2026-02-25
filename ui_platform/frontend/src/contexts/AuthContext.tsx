import { createContext, useContext, useState, useEffect } from "react";

interface AuthContextType {
  accessToken: string | null;
  refreshToken: string | null;
  role: "user" | "admin" | null;
  login: (tokens: { access: string; refresh: string; role: string }) => void;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [role, setRole] = useState<"user" | "admin" | null>(null);

  useEffect(() => {
    const access = localStorage.getItem("access_token");
    const refresh = localStorage.getItem("refresh_token");
    const storedRole = localStorage.getItem("role") as any;
    if (access) setAccessToken(access);
    if (refresh) setRefreshToken(refresh);
    if (storedRole) setRole(storedRole);
  }, []);

  const login = ({ access, refresh, role }: any) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    localStorage.setItem("role", role);
    setAccessToken(access);
    setRefreshToken(refresh);
    setRole(role);
  };

  const logout = () => {
    localStorage.clear();
    setAccessToken(null);
    setRefreshToken(null);
    setRole(null);
  };

  const refreshAccessToken = async () => {
    if (!refreshToken) return logout();
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return logout();
    const data = await res.json();
    localStorage.setItem("access_token", data.access_token);
    setAccessToken(data.access_token);
  };

  return (
    <AuthContext.Provider
      value={{ accessToken, refreshToken, role, login, logout, refreshAccessToken, isAuthenticated: !!accessToken }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
