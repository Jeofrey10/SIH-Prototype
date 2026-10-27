import React, { useEffect, useState } from "react";
import { authApi, type User } from "../api";
import { AuthContext } from "./context";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = sessionStorage.getItem("aicte_user") || localStorage.getItem("aicte_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return sessionStorage.getItem("aicte_token") || localStorage.getItem("aicte_token");
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize and verify authentication state on mount
  useEffect(() => {
    let isMounted = true;
    const verifyAuth = async () => {
      const storedToken = sessionStorage.getItem("aicte_token") || localStorage.getItem("aicte_token");
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await authApi.getMe();
        if (isMounted) {
          setUser(currentUser);
          setToken(storedToken);
          sessionStorage.setItem("aicte_user", JSON.stringify(currentUser));
        }
      } catch {
        // Token expired or invalid
        if (isMounted) {
          sessionStorage.removeItem("aicte_token");
          sessionStorage.removeItem("aicte_user");
          localStorage.removeItem("aicte_token");
          localStorage.removeItem("aicte_user");
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    verifyAuth();

    // Listen for unauthorized 401 events dispatched from API client
    const handleUnauthorized = () => {
      sessionStorage.removeItem("aicte_token");
      sessionStorage.removeItem("aicte_user");
      localStorage.removeItem("aicte_token");
      localStorage.removeItem("aicte_user");
      setUser(null);
      setToken(null);
    };

    window.addEventListener("aicte:unauthorized", handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener("aicte:unauthorized", handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await authApi.login({ username: email, password });
      setToken(resp.access_token);
      setUser(resp.user);

      // Persist in session storage
      sessionStorage.setItem("aicte_token", resp.access_token);
      sessionStorage.setItem("aicte_user", JSON.stringify(resp.user));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    sessionStorage.removeItem("aicte_token");
    sessionStorage.removeItem("aicte_user");
    localStorage.removeItem("aicte_token");
    localStorage.removeItem("aicte_user");
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const currentUser = await authApi.getMe();
      setUser(currentUser);
      sessionStorage.setItem("aicte_user", JSON.stringify(currentUser));
    } catch {
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
