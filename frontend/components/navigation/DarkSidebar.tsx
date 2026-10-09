"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard,
  FileSearch,
  UploadCloud,
  Settings,
  Shield,
  LogOut,
} from "lucide-react";

interface DarkSidebarProps {
  currentRoute?: string;
}

export function DarkSidebar({ currentRoute }: DarkSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, activeOrg, logout } = useAuth();

  const activePath = currentRoute || pathname;

  const navItems = [
    {
      label: "Overview",
      href: "/dashboard",
      icon: LayoutDashboard,
      active: activePath === "/dashboard" || activePath.startsWith("/dashboard"),
    },
    {
      label: "Investigations",
      href: "/investigations",
      icon: FileSearch,
      active: activePath === "/investigations" && !activePath.includes("/new"),
    },
    {
      label: "Intake",
      href: "/investigations/new",
      icon: UploadCloud,
      active: activePath.includes("/investigations/new"),
    },
    {
      label: "Settings",
      href: "/settings/users",
      icon: Settings,
      active: activePath.startsWith("/settings"),
    },
  ];

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // ignore
    }
    router.push("/login");
  };

  const userInitials = user?.first_name && user?.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : "AK";

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 w-[76px] z-50 bg-[#0B1019] border-r border-[#1C2635] flex flex-col items-center justify-between py-5 select-none hidden md:flex"
      aria-label="Forensic Operations Navigation"
    >
      {/* Top Brand Reticle Icon */}
      <div className="flex flex-col items-center gap-6">
        <Link
          href="/dashboard"
          className="relative group p-2 rounded-lg transition-transform hover:scale-105"
          title="DeepTrace Institutional Forensics"
        >
          {/* Cyan geometric stacked reticle mark from Figma */}
          <div className="w-10 h-10 rounded-lg bg-gradient-to-b from-[#141E2B] to-[#0D131D] border border-[#273449] flex items-center justify-center relative shadow-lg shadow-cyan-950/40">
            <div className="relative w-5 h-5">
              <div className="absolute inset-0 rounded-[3px] border-[1.8px] border-[#06B6D4] opacity-90 transform -rotate-3 transition-transform group-hover:rotate-0" />
              <div className="absolute inset-0 rounded-[3px] border-[1.8px] border-[#22C5DF] opacity-60 transform rotate-6 scale-95 transition-transform group-hover:rotate-0" />
              <div className="absolute inset-[3px] bg-[#06B6D4]/20 rounded-[2px] flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-[#22C5DF] shadow-[0_0_6px_#06B6D4]" />
              </div>
            </div>
          </div>
        </Link>

        {/* Navigation Items */}
        <nav className="flex flex-col items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                className={`relative w-11 h-11 rounded-lg flex items-center justify-center transition-all ${
                  item.active
                    ? "bg-[#111925] text-[#06B6D4] border border-[#273449] shadow-sm shadow-cyan-950/30"
                    : "text-[#708095] hover:text-[#CBD5E1] hover:bg-[#141E2B]/60"
                }`}
              >
                {/* Active Cyan Left Indicator */}
                {item.active && (
                  <div className="absolute -left-[14px] top-1/2 -translate-y-1/2 w-1 h-5 rounded-r bg-[#06B6D4] shadow-[0_0_8px_#06B6D4]" />
                )}
                <Icon className="w-5 h-5 stroke-[1.8]" />
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom Controls & User Avatar */}
      <div className="flex flex-col items-center gap-4">
        {/* Compliance Status Dot */}
        <div
          className="relative flex items-center justify-center p-2 rounded-md hover:bg-[#111925] text-[#708095] transition-colors cursor-pointer"
          title={`SBP BPRD 05/2020 Active • ${activeOrg?.name || "Meezan Bank Ltd"}`}
        >
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
          </span>
        </div>

        {/* User Avatar */}
        <div className="relative group">
          <div
            className="w-9 h-9 rounded-full bg-[#182333] border border-[#273449] flex items-center justify-center text-xs font-mono font-bold text-[#E5EBF4] shadow-inner cursor-pointer hover:border-[#06B6D4] transition-colors"
            title={`${user?.email || "analyst@deeptrace.io"} (${activeOrg?.name || "Institutional"})`}
          >
            {userInitials}
          </div>

          {/* Quick Tooltip / Logout on Click */}
          <button
            type="button"
            onClick={handleLogout}
            title="Sign Out"
            className="hidden group-hover:flex absolute -right-8 bottom-0 p-1.5 rounded bg-[#111925] border border-[#273449] text-[#708095] hover:text-[#EF4444] transition-colors shadow-lg"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
