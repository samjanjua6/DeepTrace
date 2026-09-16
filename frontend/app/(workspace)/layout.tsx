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

  // /investigations/sample is an explicitly public demonstration exhibit
  const isPublicRoute = pathname === "/investigations/sample" || pathname === "/investigations/sample/";

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
      <div className="min-h-screen bg-paper-0 flex flex-col items-center justify-center p-6 font-mono text-ink-900 select-none">
        <Loader2 className="w-8 h-8 animate-spin text-ink-900 mb-3" />
        <span className="text-xs uppercase tracking-widest text-ink-600 font-semibold">
          Verifying Institutional Clearance Credentials...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    const loginUrl = `/login?redirect=${encodeURIComponent(pathname)}`;
    return (
      <div className="min-h-screen bg-paper-0 flex flex-col items-center justify-center p-6 font-mono text-ink-900 select-none">
        <div className="max-w-md w-full bg-paper-0 border-2 border-ink-900 p-8 shadow-2xl space-y-4">
          <div className="flex items-center gap-3 border-b border-rule pb-3">
            <ShieldAlert className="w-6 h-6 text-forensic-amber shrink-0" />
            <div>
              <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold block">
                Access Restricted • Clearance Required
              </span>
              <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight">
                Authentication Required
              </h2>
            </div>
          </div>

          <p className="text-xs text-ink-700 leading-relaxed">
            Document intake and forensic case registers require verified institutional
            clearance under State Bank of Pakistan (SBP BPRD) compliance standards.
          </p>

          <div className="pt-2">
            <Link href={loginUrl} className="w-full block">
              <Button
                variant="primary"
                size="lg"
                className="w-full"
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
