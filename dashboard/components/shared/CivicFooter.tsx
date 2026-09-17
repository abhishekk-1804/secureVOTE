import React from "react";
import Link from "next/link";

export function CivicFooter() {
  return (
    <footer className="bg-slate-50 border-t border-slate-200 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-slate-500">
            <p className="font-semibold text-slate-700">SecureVOTE 2.0</p>
            <p>Independent educational/research prototype. Not affiliated with the Election Commission of India and not intended for production elections.</p>
          </div>
          <div className="flex gap-6 text-sm font-medium text-slate-600">
            <Link href="/transparency" className="hover:text-civic-navy">Transparency</Link>
            <Link href="https://github.com/example/securevote" className="hover:text-civic-navy">Documentation</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
