"use client";

import React from "react";
import Link from "next/link";
import { Shield, Server, Search, CheckCircle, Database } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans">
      {/* Hero Section */}
      <section className="bg-civic-navy text-white py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6">
            SECUREVOTE
          </h1>
          <p className="text-xl md:text-2xl text-slate-200 mb-8 max-w-3xl mx-auto">
            Election Integrity, From Ballot to Verification
          </p>
          <div className="bg-white/10 rounded-lg p-4 max-w-3xl mx-auto mb-10 text-sm md:text-base border border-white/20">
            <p>
              Independent educational/research prototype. Not affiliated with the Election Commission of India and not intended for production elections.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link href="/voter" className="w-full sm:w-auto block">
              <Button as="span" size="lg" className="w-full bg-civic-saffron text-slate-900 hover:bg-amber-400 font-bold">
                ENTER VOTER PORTAL
              </Button>
            </Link>
            <Link href="/evm" className="w-full sm:w-auto block">
              <Button as="span" size="lg" variant="outline" className="w-full border-white text-white hover:bg-white/10 dark:border-white dark:text-white dark:hover:bg-white/10">
                OPEN EVM SIMULATOR
              </Button>
            </Link>
            <Link href="/login" className="w-full sm:w-auto block">
              <Button as="span" size="lg" variant="secondary" className="w-full bg-slate-800 hover:bg-slate-700">
                OPEN OFFICER CONSOLE
              </Button>
            </Link>
            <Link href="/verify" className="w-full sm:w-auto block">
              <Button as="span" size="lg" variant="ghost" className="w-full text-white hover:bg-white/10 dark:text-white dark:hover:bg-white/10">
                VERIFY ELECTION
              </Button>
            </Link>
          </div>

          <div className="mt-8 flex gap-6 justify-center">
            <Link href="/transparency" className="text-sm text-slate-300 hover:text-white underline underline-offset-4">
              VIEW TRANSPARENCY
            </Link>
            <Link href="#" className="text-sm text-slate-300 hover:text-white underline underline-offset-4">
              VIEW DOCUMENTATION
            </Link>
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12 text-slate-900">System Architecture</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">Physical Arduino EVM</h3>
              <p className="text-slate-600">Hardware device that records votes with cryptographic signing and tamper-evident storage.</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center mb-4">
                <Server className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">Digital EVM Twin</h3>
              <p className="text-slate-600">Software simulator bridging the hardware device to the central backend infrastructure.</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center mb-4">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">SecureVOTE Backend</h3>
              <p className="text-slate-600">Core system managing election data, cryptographic verification, and the tamper-evident audit chain.</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-lg flex items-center justify-center mb-4">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">Election Management</h3>
              <p className="text-slate-600">Officer console for configuring elections, monitoring devices, and managing security.</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center mb-4">
                <CheckCircle className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">Independent Verifier</h3>
              <p className="text-slate-600">Tools allowing anyone to mathematically prove their vote was recorded without exposing their choice.</p>
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-4">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold mb-2">Transparency Portal</h3>
              <p className="text-slate-600">Public dashboard showing real-time statistics, audit logs, and election metadata.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
