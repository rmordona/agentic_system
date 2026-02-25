import { useAuth } from "@/contexts/AuthContext";
import { api as rawApi } from "@/services/api";
import { useCallback } from "react";

export const useApi = () => {
  const { accessToken } = useAuth();

  const callApi = useCallback(
    (endpoint: string, options: RequestInit = {}) => {
      const headers = {
        ...options.headers,
        Authorization: accessToken ? `Bearer ${accessToken}` : "",
        "Content-Type": "application/json",
      };
      return rawApi(endpoint, { ...options, headers }, accessToken);
    },
    [accessToken] // ✅ stable unless accessToken changes
  );

  return callApi;
};