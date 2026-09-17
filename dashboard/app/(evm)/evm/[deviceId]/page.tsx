"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import EvmTerminal from "@/components/evm/EvmTerminal";

function EvmTerminalWrapper({ deviceId }: { deviceId: string }) {
  const searchParams = useSearchParams();
  const electionId = searchParams.get("election");

  if (!electionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-amber-500">
        Missing election ID in URL
      </div>
    );
  }

  return <EvmTerminal deviceId={deviceId} electionId={electionId} />;
}

export default function EvmPage({ params }: { params: { deviceId: string } }) {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">Loading...</div>}>
      <EvmTerminalWrapper deviceId={params.deviceId} />
    </Suspense>
  );
}
