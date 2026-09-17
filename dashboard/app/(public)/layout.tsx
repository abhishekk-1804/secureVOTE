import { CivicHeader } from "@/components/shared/CivicHeader";
import { CivicFooter } from "@/components/shared/CivicFooter";
import React from "react";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col">
      <CivicHeader />
      <main className="flex-1">{children}</main>
      <CivicFooter />
    </div>
  );
}
