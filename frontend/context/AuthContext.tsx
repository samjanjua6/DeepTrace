"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  UserProfile,
  OrganizationOption,
  TokenResponse,
  getAuthToken,
  loginUser,
  verifyMfaLogin,
  logoutUser,
  getCurrentUser,
  getOrganizations,
  switchOrganization,
} from "@/lib/api/client";

interface AuthContextType {
  user: UserProfile | null;
  activeOrg: OrganizationOption | null;
  organizations: OrganizationOption[];
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
    mfaCode?: string,
    rememberDevice?: boolean
  ) => Promise<TokenResponse>;
  verifyMfa: (
    tempToken: string,
    mfaCode: string,
    rememberDevice?: boolean
  ) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  switchOrg: (organizationId: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeOrg, setActiveOrg] = useState<OrganizationOption | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationOption[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshProfile = useCallback(async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        setUser(null);
        setActiveOrg(null);
        return;
      }
      const profile = await getCurrentUser();
      setUser(profile);
      if (profile.organization_id) {
        setActiveOrg({
          id: profile.organization_id,
          name: profile.organization_name || "Meezan Bank Ltd",
          slug: profile.organization_slug || "meezan-bank",
        });
      }
      const orgs = await getOrganizations().catch(() => []);
      setOrganizations(orgs);
    } catch {
      setUser(null);
      setActiveOrg(null);
    }
  }, []);

  // Hydrate on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const token = getAuthToken();
        if (token) {
          await refreshProfile();
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [refreshProfile]);

  const login = async (
    email: string,
    password: string,
    mfaCode?: string,
    rememberDevice: boolean = true
  ): Promise<TokenResponse> => {
    const res = await loginUser({
      email,
      password,
      mfa_code: mfaCode,
      remember_me: rememberDevice,
    });
    if (!res.mfa_required) {
      await refreshProfile();
    }
    return res;
  };

  const verifyMfa = async (
    tempToken: string,
    mfaCode: string,
    rememberDevice: boolean = true
  ): Promise<TokenResponse> => {
    const res = await verifyMfaLogin(tempToken, mfaCode, rememberDevice);
    await refreshProfile();
    return res;
  };

  const logout = async () => {
    await logoutUser();
    setUser(null);
    setActiveOrg(null);
  };

  const switchOrg = async (organizationId: string) => {
    const res = await switchOrganization(organizationId);
    setActiveOrg(res.organization);
    await refreshProfile();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        organizations,
        isAuthenticated: !!user,
        isLoading,
        login,
        verifyMfa,
        logout,
        switchOrg,
        refreshProfile,
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
