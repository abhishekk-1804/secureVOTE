"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { ElectionResponse, DeviceResponse } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import { Activity, ShieldCheck } from "lucide-react";

export default function EvmLauncher() {
  const router = useRouter();
  const { token } = useAuth();
  const [elections, setElections] = useState<ElectionResponse[]>([]);
  const [selectedElectionId, setSelectedElectionId] = useState("");
  const [devices, setDevices] = useState<DeviceResponse[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchElections = async () => {
      try {
        const data = await api.getElections(token || undefined);
        setElections(data.filter(e => e.state === "OPEN"));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchElections();
  }, [token]);

  useEffect(() => {
    if (!selectedElectionId) {
      setDevices([]);
      return;
    }
    const fetchDevices = async () => {
      try {
        const data = await api.getDevices(selectedElectionId, token || undefined);
        setDevices(data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchDevices();
  }, [selectedElectionId, token]);

  const handleLaunch = () => {
    if (selectedDeviceId && selectedElectionId) {
      router.push(`/evm/${selectedDeviceId}?election=${selectedElectionId}`);
    }
  };

  const selectedDevice = devices.find(d => d.id === selectedDeviceId);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-slate-950">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-amber-400"></div>
        <div className="flex items-center gap-3 mb-6">
          <ShieldCheck className="w-8 h-8 text-amber-500" />
          <h1 className="text-2xl font-bold text-slate-100">EVM Launcher</h1>
        </div>

        <div className="mb-6 inline-block bg-amber-500/10 text-amber-500 text-xs font-semibold px-3 py-1 rounded-full border border-amber-500/20">
          EVM DIGITAL TWIN - SIMULATION
        </div>

        {loading ? (
          <div className="text-slate-400 flex items-center gap-2 py-4">
            <Activity className="w-4 h-4 animate-spin" /> Loading elections...
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Select Election</label>
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-slate-100 outline-none focus:border-amber-500 transition-colors"
                value={selectedElectionId}
                onChange={e => { setSelectedElectionId(e.target.value); setSelectedDeviceId(""); }}
              >
                <option value="">-- Choose Election --</option>
                {elections.map(e => (
                  <option key={e.id} value={e.id}>{e.title}</option>
                ))}
              </select>
            </div>

            {selectedElectionId && (
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Select Device</label>
                <select
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-slate-100 outline-none focus:border-amber-500 transition-colors"
                  value={selectedDeviceId}
                  onChange={e => setSelectedDeviceId(e.target.value)}
                >
                  <option value="">-- Choose Device --</option>
                  {devices.map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.status})</option>
                  ))}
                </select>
              </div>
            )}

            {selectedDevice && (
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-sm">
                <div className="flex justify-between mb-2">
                  <span className="text-slate-500">Device ID:</span>
                  <span className="text-slate-200 font-mono">{selectedDevice.id}</span>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-slate-500">Status:</span>
                  <span className={`font-mono ${selectedDevice.status === 'ACTIVE' ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {selectedDevice.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Last Sequence:</span>
                  <span className="text-slate-200 font-mono">{selectedDevice.last_sequence_number}</span>
                </div>
              </div>
            )}

            <button
              onClick={handleLaunch}
              disabled={!selectedDeviceId || !selectedElectionId}
              className="w-full py-4 mt-4 bg-slate-100 hover:bg-white text-slate-900 font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              LAUNCH EVM TERMINAL
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
