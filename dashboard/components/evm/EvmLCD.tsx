"use client";

import React from "react";

export default function EvmLCD({ message }: { message: string }) {
  return (
    <div className="w-full bg-[#1a2e1e] border-4 border-[#0f1c12] rounded p-6 shadow-inner relative overflow-hidden">
      {/* LCD glare effect */}
      <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/5 to-transparent pointer-events-none"></div>

      <div className="font-mono text-2xl text-[#39ff14] text-center tracking-widest drop-shadow-[0_0_8px_rgba(57,255,20,0.8)]">
        {message}
      </div>
    </div>
  );
}
