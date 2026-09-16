"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Role, UserResponse } from "@/lib/types";
import { api, setUnauthorizedHandler } from "@/lib/api-client";

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Storage key documented in docs/limitations.md
const STORAGE_TOKEN_KEY = "securevote_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();
  const pathname = usePathname();

  const logout = () => {
    setToken(null);
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_TOKEN_KEY);
    } catch {}
    if (pathname !== "/login") {
      router.push("/login");
    }
  };

  useEffect(() => {
    // Intercept 401 to clear session and redirect to login cleanly
    setUnauthorizedHandler(() => {
      logout();
    });

    // Check existing stored session on mount
    const initAuth = async () => {
      try {
        const savedToken = localStorage.getItem(STORAGE_TOKEN_KEY);
        if (savedToken) {
          setToken(savedToken);
          const me = await api.getMe(savedToken);
          setUser(me);
        }
      } catch (err) {
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const tokenRes = await api.login(username, password);
      const accessToken = tokenRes.access_token;
      setToken(accessToken);
      try {
        localStorage.setItem(STORAGE_TOKEN_KEY, accessToken);
      } catch {}

      const me = await api.getMe(accessToken);
      setUser(me);
      router.push("/command");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role ?? null,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
