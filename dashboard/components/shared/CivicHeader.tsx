import React from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function CivicHeader() {
  return (
    <header className="bg-civic-navy text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <ShieldCheck className="w-8 h-8 text-civic-saffron" />
              <span className="font-bold text-xl tracking-tight">SecureVOTE</span>
            </Link>
          </div>
          <nav className="hidden md:flex space-x-8">
            <Link href="/" className="text-sm font-medium hover:text-civic-saffron transition-colors">Home</Link>
            <Link href="/voter" className="text-sm font-medium hover:text-civic-saffron transition-colors">Voter Services</Link>
            <Link href="/transparency" className="text-sm font-medium hover:text-civic-saffron transition-colors">Transparency</Link>
            <Link href="/verify" className="text-sm font-medium hover:text-civic-saffron transition-colors">Verify Election</Link>
          </nav>
          <div className="flex items-center">
            <Link href="/login" className="text-sm font-medium bg-white/10 hover:bg-white/20 px-4 py-2 rounded-md transition-colors">
              Officer Login
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
