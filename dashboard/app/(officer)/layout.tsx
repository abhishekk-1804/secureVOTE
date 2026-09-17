import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import React from "react";
import { ElectionProvider } from "@/context/ElectionContext";

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  return (
    <ElectionProvider>
      <div className="dark bg-slate-950 text-slate-100 min-h-screen flex flex-col">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">{children}</div>
          </main>
        </div>
      </div>
    </ElectionProvider>
  );
}
