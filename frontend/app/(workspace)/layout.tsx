"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ShieldAlert, Loader2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  // /dashboard and /investigations/sample are accessible for review/preview
  const isPublicRoute =
    pathname === "/dashboard" ||
    pathname.startsWith("/dashboard") ||
    pathname === "/investigations/sample" ||
    pathname === "/investigations/sample/";

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isPublicRoute) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, isPublicRoute, pathname, router]);

  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#080C13] flex flex-col items-center justify-center p-6 font-mono text-[#F1F5F9] select-none">
        <Loader2 className="w-8 h-8 animate-spin text-[#06B6D4] mb-3" />
        <span className="text-xs uppercase tracking-widest text-[#708095] font-semibold">
          Verifying Institutional Clearance Credentials...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    const loginUrl = `/login?redirect=${encodeURIComponent(pathname)}`;
    return (
      <div className="min-h-screen bg-[#080C13] flex flex-col items-center justify-center p-6 font-mono text-[#F1F5F9] select-none">
        <div className="max-w-md w-full bg-[#0B1019] border border-[#273449] p-8 rounded-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-3 border-b border-[#1C2635] pb-3">
            <ShieldAlert className="w-6 h-6 text-[#F59E0B] shrink-0" />
            <div>
              <span className="text-[10px] text-[#708095] uppercase tracking-widest font-bold block">
                Access Restricted • Clearance Required
              </span>
              <h2 className="text-xl font-bold text-[#F4F7FB] tracking-tight">
                Authentication Required
              </h2>
            </div>
          </div>

          <p className="text-xs text-[#AAB5C4] leading-relaxed">
            Document intake and forensic case registers require verified institutional
            clearance under State Bank of Pakistan (SBP BPRD) compliance standards.
          </p>

          <div className="pt-2">
            <Link href={loginUrl} className="w-full block">
              <Button
                variant="primary"
                size="lg"
                className="w-full bg-[#0891B2] hover:bg-[#06B6D4] text-white"
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Sign In to Continue
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
