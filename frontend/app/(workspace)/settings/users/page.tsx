"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Users,
  UserPlus,
  Shield,
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  Search,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Unlock,
  KeyRound,
  ArrowLeft,
  Loader2,
  Scale,
  X,
  AlertCircle,
  Clock,
  UserX,
  UserCheck,
} from "lucide-react";
import {
  getOrgUsers,
  updateUserStatus,
  unlockUserAccount,
  resetUserMfa,
} from "@/lib/api/client";
import { OrgMemberItem, OrgUserRole } from "@/lib/types/forensics";
import { InviteUserModal } from "@/components/users/InviteUserModal";
import { ChangeRoleModal } from "@/components/users/ChangeRoleModal";
import { RolePermissionMatrixModal } from "@/components/users/RolePermissionMatrixModal";

type FilterTab = "ALL" | "ADMINS" | "ANALYSTS" | "VIEWERS" | "DEACTIVATED";

interface ConfirmActionState {
  type: "status" | "unlock" | "reset_mfa";
  user: OrgMemberItem;
  nextStatus?: boolean;
}

export default function UsersAdministrationPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [members, setMembers] = useState<OrgMemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<FilterTab>("ALL");

  // Modals state
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [matrixModalOpen, setMatrixModalOpen] = useState(false);
  const [selectedMemberForRole, setSelectedMemberForRole] = useState<OrgMemberItem | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";

  const fetchRoster = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOrgUsers();
      setMembers(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load organization member directory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && isAuthenticated && isAdmin) {
      fetchRoster();
    }
  }, [authLoading, isAuthenticated, isAdmin]);

  // Derived metrics
  const totalCount = members.length;
  const activeCount = useMemo(() => members.filter((m) => m.is_active).length, [members]);
  const activeAnalysts = useMemo(
    () => members.filter((m) => m.role === "ANALYST" && m.is_active).length,
    [members]
  );
  const adminCount = useMemo(
    () => members.filter((m) => (m.role === "ADMIN" || m.role === "OWNER") && m.is_active).length,
    [members]
  );
  const mfaCount = useMemo(
    () => members.filter((m) => m.mfa_enabled && m.is_active).length,
    [members]
  );
  const mfaRate = activeCount > 0 ? Math.round((mfaCount / activeCount) * 100) : 0;

  // Filtered members list
  const filteredMembers = useMemo(() => {
    return members.filter((m) => {
      // Tab filter
      if (activeTab === "ADMINS" && !(m.role === "ADMIN" || m.role === "OWNER")) return false;
      if (activeTab === "ANALYSTS" && m.role !== "ANALYST") return false;
      if (activeTab === "VIEWERS" && m.role !== "VIEWER") return false;
      if (activeTab === "DEACTIVATED" && m.is_active) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const fullName = `${m.first_name} ${m.last_name}`.toLowerCase();
        const email = m.email.toLowerCase();
        const role = m.role.toLowerCase();
        return fullName.includes(q) || email.includes(q) || role.includes(q);
      }

      return true;
    });
  }, [members, activeTab, searchQuery]);

  // Handle Confirmed Action Execution
  const handleExecuteConfirmedAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    setActionNotice(null);
    setError(null);

    try {
      if (confirmAction.type === "status" && confirmAction.nextStatus !== undefined) {
        await updateUserStatus(confirmAction.user.id, confirmAction.nextStatus);
        const actionLabel = confirmAction.nextStatus ? "reactivated" : "suspended";
        setActionNotice(
          `Personnel clearance for ${confirmAction.user.first_name} ${confirmAction.user.last_name} (${confirmAction.user.email}) successfully ${actionLabel}.`
        );
      } else if (confirmAction.type === "unlock") {
        const res = await unlockUserAccount(confirmAction.user.id);
        setActionNotice(
          res.message || `Account unlocked for ${confirmAction.user.email}. Authentication restrictions cleared.`
        );
      } else if (confirmAction.type === "reset_mfa") {
        const res = await resetUserMfa(confirmAction.user.id);
        setActionNotice(
          res.message || `Two-factor authentication reset for ${confirmAction.user.email}. User must reconfigure 2FA upon next login.`
        );
      }
      setConfirmAction(null);
      await fetchRoster();
    } catch (err: any) {
      setError(err?.message || "Action execution failed. Please verify permissions.");
      setConfirmAction(null);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Authentication & RBAC Gatekeeper ─────────────────────────────────────
  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 font-mono">
        <Loader2 className="w-8 h-8 animate-spin text-ink-900 mb-3" />
        <span className="text-xs uppercase tracking-widest text-ink-600">
          Verifying Institutional Clearance...
        </span>
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-6 font-mono">
        <div className="bg-paper-0 border-2 border-rose-900 shadow-2xl p-8">
          <div className="flex items-center gap-3 border-b-2 border-rose-900 pb-4 mb-6">
            <div className="p-2.5 bg-rose-100 border border-rose-900 text-rose-900">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-rose-700 block">
                Access Denied [HTTP 403]
              </span>
              <h1 className="text-lg font-bold uppercase tracking-wider text-rose-950">
                Institutional Administrator Clearance Required
              </h1>
            </div>
          </div>

          <div className="space-y-3 text-xs text-ink-700 leading-relaxed mb-8">
            <p>
              Access to Personnel & Clearance Administration is strictly restricted to
              designated Institutional Compliance Officers and System Administrators (
              <span className="font-bold text-ink-900">ADMIN</span> or{" "}
              <span className="font-bold text-ink-900">OWNER</span> roles).
            </p>
            <p>
              Your active session is authenticated as{" "}
              <span className="font-bold text-ink-900">{user?.email || "Unknown User"}</span> with
              assigned clearance{" "}
              <span className="font-bold text-rose-900">[{user?.role || "UNAUTHORIZED"}]</span>.
            </p>
            <div className="p-3 bg-paper-2 border border-ink-900/30 text-[11px] text-ink-600">
              Under SBP Cybersecurity Guidelines (BPRD/2020), unauthorized attempts to alter user roles,
              unlock accounts, or inspect personnel rosters are recorded in the immutable compliance audit trail.
            </div>
          </div>

          <div className="flex items-center gap-4 pt-4 border-t border-ink-900/20">
            <Link
              href="/investigations"
              className="px-4 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 text-xs uppercase font-bold tracking-wider transition-colors inline-flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Forensic Dockets</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Main Administrative View ─────────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto py-8 px-6 font-mono space-y-6">
      {/* Page Header */}
      <div className="border-b-2 border-ink-900 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-ink-500 mb-1">
              <Link href="/investigations" className="hover:text-ink-900 transition-colors">
                Workspace
              </Link>
              <span>/</span>
              <span>Settings</span>
              <span>/</span>
              <span className="text-ink-900 font-bold">Personnel & Roles</span>
            </div>
            <h1 className="text-2xl font-serif text-ink-900 tracking-tight">
              Personnel & Clearance Administration
            </h1>
            <p className="text-xs text-ink-600 mt-1 max-w-2xl">
              Institutional Role Delegation, Security Credentials & SBP BPRD/2020 Compliance Governance.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <button
              type="button"
              onClick={() => setMatrixModalOpen(true)}
              className="px-3 py-2 border border-ink-900/40 bg-paper-1 hover:bg-paper-2 text-ink-800 text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Scale className="w-4 h-4 text-ink-700" />
              <span>Clearance Matrix</span>
            </button>

            <button
              type="button"
              onClick={fetchRoster}
              disabled={loading}
              className="p-2 border border-ink-900/40 hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer"
              title="Refresh Member Roster"
            >
              <RotateCcw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>

            <button
              type="button"
              onClick={() => setInviteModalOpen(true)}
              className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 border border-ink-900 cursor-pointer shadow-sm"
            >
              <UserPlus className="w-4 h-4" />
              <span>Onboard Personnel</span>
            </button>
          </div>
        </div>
      </div>

      {/* Action Notice Alert */}
      {actionNotice && (
        <div className="p-4 bg-emerald-50 border-2 border-emerald-600 text-emerald-950 text-xs flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{actionNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionNotice(null)}
            className="text-emerald-800 hover:text-emerald-950 p-1 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-rose-50 border-2 border-rose-600 text-rose-950 text-xs flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-700 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-rose-800 hover:text-rose-950 p-1 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Institutional Metric Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Members */}
        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Total Personnel Roster
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {totalCount}
            </span>
            <span className="text-[10px] text-ink-500 uppercase font-semibold">
              ({activeCount} Active)
            </span>
          </div>
          <span className="text-[10px] text-ink-500 mt-2 block">
            Across All Clearance Tiers
          </span>
        </div>

        {/* Active Analysts */}
        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Operational Analysts
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {activeAnalysts}
            </span>
            <span className="text-[10px] text-emerald-700 uppercase font-semibold">
              Investigating
            </span>
          </div>
          <span className="text-[10px] text-ink-500 mt-2 block">
            Authorized for Document Assessment
          </span>
        </div>

        {/* Administrators */}
        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Institutional Administrators
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {adminCount}
            </span>
            <span className="text-[10px] text-ink-700 uppercase font-semibold">
              Clearance Level 3+
            </span>
          </div>
          <span className="text-[10px] text-ink-500 mt-2 block">
            Owner & Admin Clearance Holders
          </span>
        </div>

        {/* 2FA Compliance Rate */}
        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            2FA Security Compliance
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {mfaRate}%
            </span>
            <span
              className={`text-[10px] uppercase font-semibold ${
                mfaRate >= 100 ? "text-emerald-700" : "text-amber-700"
              }`}
            >
              {mfaRate >= 100 ? "SBP Compliant" : "Mandatory 2FA Target"}
            </span>
          </div>
          <span className="text-[10px] text-ink-500 mt-2 block">
            {mfaCount} of {activeCount} active members protected
          </span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-ink-900/30 pb-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {[
            { id: "ALL", label: "All Personnel" },
            { id: "ADMINS", label: "Administrators" },
            { id: "ANALYSTS", label: "Analysts" },
            { id: "VIEWERS", label: "Auditors / Viewers" },
            { id: "DEACTIVATED", label: "Deactivated" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as FilterTab)}
              className={`px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer border ${
                activeTab === tab.id
                  ? "bg-ink-900 text-paper-0 border-ink-900"
                  : "bg-paper-0 text-ink-700 border-ink-900/20 hover:border-ink-900/60"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by name, email, or role..."
            className="w-full pl-9 pr-8 py-1.5 bg-paper-0 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs placeholder:text-ink-400 font-mono"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-900"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Personnel Roster Table */}
      <div className="bg-paper-0 border-2 border-ink-900 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead>
              <tr className="bg-ink-900 text-paper-0 border-b border-ink-900">
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-[28%]">
                  Personnel Identity
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-[14%]">
                  Clearance Level
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-[18%]">
                  Security Status
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-[16%]">
                  Last Authentication
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-[12%]">
                  Clearance Issued
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] text-right w-[12%]">
                  Governance
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/20">
              {loading && members.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-ink-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-ink-900" />
                    <span>Retrieving institutional member roster...</span>
                  </td>
                </tr>
              ) : filteredMembers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-ink-500">
                    <Users className="w-6 h-6 mx-auto mb-2 text-ink-400" />
                    <span>No personnel records match the specified criteria.</span>
                  </td>
                </tr>
              ) : (
                filteredMembers.map((member) => {
                  const isSelf = member.id === user?.id;
                  const initials = `${member.first_name?.[0] || ""}${member.last_name?.[0] || ""}`.toUpperCase() || "U";

                  return (
                    <tr
                      key={member.id}
                      className={`hover:bg-paper-1/60 transition-colors ${
                        !member.is_active ? "opacity-60 bg-paper-2/40" : ""
                      }`}
                    >
                      {/* Personnel Identity */}
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-ink-900 text-paper-0 flex items-center justify-center font-bold text-xs shrink-0">
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-ink-900 truncate">
                                {member.first_name} {member.last_name}
                              </span>
                              {isSelf && (
                                <span className="px-1.5 py-0.2 bg-paper-2 border border-ink-900/30 text-[9px] uppercase font-bold text-ink-700">
                                  You
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-ink-500 block truncate">
                              {member.email}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Clearance Level */}
                      <td className="p-3">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
                              member.role === "OWNER"
                                ? "bg-ink-900 text-paper-0 border-ink-900"
                                : member.role === "ADMIN"
                                ? "bg-ink-800 text-paper-0 border-ink-800"
                                : member.role === "ANALYST"
                                ? "bg-paper-1 text-ink-900 border-ink-900/40"
                                : "bg-paper-2 text-ink-600 border-ink-900/20"
                            }`}
                          >
                            {member.role}
                          </span>
                        </div>
                      </td>

                      {/* Security Status */}
                      <td className="p-3">
                        <div className="space-y-1">
                          {/* Active / Inactive Badge */}
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`inline-block w-2 h-2 shrink-0 ${
                                member.is_active ? "bg-emerald-600" : "bg-rose-600"
                              }`}
                            />
                            <span
                              className={`text-[10px] uppercase font-bold ${
                                member.is_active ? "text-emerald-800" : "text-rose-800"
                              }`}
                            >
                              {member.is_active ? "Active Clearance" : "Suspended"}
                            </span>
                          </div>

                          {/* Lockout Badge */}
                          {member.is_locked && (
                            <div className="flex items-center gap-1 text-rose-700 text-[10px] font-bold">
                              <Lock className="w-3 h-3 shrink-0" />
                              <span>Locked (Failed Attempts: {member.failed_login_count})</span>
                            </div>
                          )}

                          {/* MFA Badge */}
                          <div className="flex items-center gap-1 text-[10px] text-ink-600">
                            {member.mfa_enabled ? (
                              <>
                                <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                                <span className="text-emerald-800">2FA Enforced</span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
                                <span className="text-amber-700">2FA Pending</span>
                              </>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Last Authentication */}
                      <td className="p-3 text-ink-700 text-[11px]">
                        {member.last_login_at ? (
                          <div>
                            <span>
                              {new Date(member.last_login_at).toLocaleDateString("en-GB", {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                              })}
                            </span>
                            <span className="text-[10px] text-ink-500 block">
                              {new Date(member.last_login_at).toLocaleTimeString("en-GB", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                        ) : (
                          <span className="text-ink-400 italic">Never authenticated</span>
                        )}
                      </td>

                      {/* Clearance Issued Date */}
                      <td className="p-3 text-ink-700 text-[11px]">
                        {new Date(member.created_at).toLocaleDateString("en-GB", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>

                      {/* Governance Actions */}
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5 flex-wrap">
                          {/* Modify Role */}
                          <button
                            type="button"
                            onClick={() => setSelectedMemberForRole(member)}
                            className="px-2 py-1 border border-ink-900/30 bg-paper-1 hover:bg-paper-2 text-ink-800 text-[10px] uppercase font-bold transition-colors cursor-pointer"
                            title="Modify Clearance Role"
                          >
                            Role
                          </button>

                          {/* Lockout Unlock */}
                          {(member.is_locked || member.failed_login_count > 0) && (
                            <button
                              type="button"
                              onClick={() =>
                                setConfirmAction({
                                  type: "unlock",
                                  user: member,
                                })
                              }
                              className="px-2 py-1 bg-amber-100 border border-amber-400 text-amber-900 hover:bg-amber-200 text-[10px] uppercase font-bold transition-colors flex items-center gap-1 cursor-pointer"
                              title="Unlock account login"
                            >
                              <Unlock className="w-3 h-3" />
                              <span>Unlock</span>
                            </button>
                          )}

                          {/* Reset 2FA */}
                          {member.mfa_enabled && (
                            <button
                              type="button"
                              onClick={() =>
                                setConfirmAction({
                                  type: "reset_mfa",
                                  user: member,
                                })
                              }
                              className="px-2 py-1 border border-ink-900/20 bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-rose-800 text-[10px] uppercase font-bold transition-colors flex items-center gap-1 cursor-pointer"
                              title="Reset Two-Factor Authentication"
                            >
                              <KeyRound className="w-3 h-3" />
                              <span>2FA</span>
                            </button>
                          )}

                          {/* Suspend / Reactivate Status */}
                          {!isSelf && (
                            <button
                              type="button"
                              onClick={() =>
                                setConfirmAction({
                                  type: "status",
                                  user: member,
                                  nextStatus: !member.is_active,
                                })
                              }
                              className={`px-2 py-1 text-[10px] uppercase font-bold border transition-colors cursor-pointer ${
                                member.is_active
                                  ? "border-rose-300 text-rose-800 hover:bg-rose-50"
                                  : "border-emerald-300 text-emerald-800 hover:bg-emerald-50"
                              }`}
                              title={member.is_active ? "Suspend access" : "Reactivate access"}
                            >
                              {member.is_active ? "Suspend" : "Activate"}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Action Dialog Modal */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
          <div className="w-full max-w-lg bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative">
            <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-4">
              <div className="p-2 bg-ink-900 text-paper-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
                  Security Protocol Confirmation
                </span>
                <h3 className="text-base font-bold uppercase tracking-wider text-ink-900">
                  {confirmAction.type === "status"
                    ? confirmAction.nextStatus
                      ? "Reactivate Personnel Clearance"
                      : "Suspend Personnel Clearance"
                    : confirmAction.type === "unlock"
                    ? "Unlock Account Credentials"
                    : "Reset Two-Factor Authentication"}
                </h3>
              </div>
            </div>

            <div className="space-y-3 text-xs text-ink-700 mb-6">
              <p>
                Target Personnel:{" "}
                <strong className="text-ink-900">
                  {confirmAction.user.first_name} {confirmAction.user.last_name}
                </strong>{" "}
                ({confirmAction.user.email})
              </p>

              {confirmAction.type === "status" && !confirmAction.nextStatus && (
                <div className="p-3 bg-rose-50 border border-rose-300 text-rose-900 text-xs">
                  Suspending this clearance will immediately revoke the user's active sessions and prevent
                  any forensic docket access. This action will be audited under SBP compliance guidelines.
                </div>
              )}

              {confirmAction.type === "status" && confirmAction.nextStatus && (
                <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs">
                  Reactivating this clearance restores platform access with the user's existing permissions.
                </div>
              )}

              {confirmAction.type === "unlock" && (
                <div className="p-3 bg-paper-1 border border-ink-900/30 text-ink-800 text-xs">
                  This action clears the failed login attempt counter and unlocks the account immediately,
                  allowing the user to authenticate again.
                </div>
              )}

              {confirmAction.type === "reset_mfa" && (
                <div className="p-3 bg-amber-50 border border-amber-300 text-amber-950 text-xs">
                  This action disarms the current TOTP secret key for this personnel member. The member will be
                  required to configure a new authenticator app upon next sign-in.
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-ink-900/20">
              <button
                type="button"
                onClick={() => setConfirmAction(null)}
                disabled={actionLoading}
                className="px-4 py-2 border border-ink-900/30 text-ink-700 hover:bg-paper-2 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteConfirmedAction}
                disabled={actionLoading}
                className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 text-xs font-bold uppercase tracking-wider transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {actionLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Protocol...</span>
                  </>
                ) : (
                  <span>Confirm & Commit</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invite Personnel Modal */}
      <InviteUserModal
        isOpen={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        onSuccess={() => {
          fetchRoster();
        }}
      />

      {/* Change Clearance Level Modal */}
      <ChangeRoleModal
        isOpen={selectedMemberForRole !== null}
        member={selectedMemberForRole}
        currentUserId={user?.id || null}
        onClose={() => setSelectedMemberForRole(null)}
        onSuccess={() => {
          setSelectedMemberForRole(null);
          setActionNotice("Personnel clearance role updated successfully.");
          fetchRoster();
        }}
      />

      {/* Clearance Permission Matrix Modal */}
      <RolePermissionMatrixModal
        isOpen={matrixModalOpen}
        onClose={() => setMatrixModalOpen(false)}
      />
    </div>
  );
}
