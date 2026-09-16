import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "SecureVOTE — Dashboard",
  description: "Educational Secure Embedded Voting & Audit System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
        <AuthProvider>
          <Navbar />
          <div className="flex flex-1 overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-6 bg-slate-950 text-slate-100">
              <div className="max-w-7xl mx-auto">{children}</div>
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
