"use client";
import React, { useState, useEffect } from "react";
import { useElection } from "@/context/ElectionContext";
import { api } from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/format-error";
import { MessageSquare, RefreshCcw, Filter, PenTool } from "lucide-react";

export default function ComplaintsPage() {
  const { selectedElection } = useElection();
  const { token } = useAuth();
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedComplaint, setSelectedComplaint] = useState<any>(null);
  const [updateStatus, setUpdateStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notes, setNotes] = useState("");

  const [filterStatus, setFilterStatus] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getComplaints(token);
      // Backend might return all or just for election. Filter if needed.
      const filtered = selectedElection ? data.filter((c: any) => c.election_id === selectedElection.id) : data;
      setComplaints(filtered);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedElection]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint) return;
    setLoading(true);
    try {
      await api.updateComplaintStatus(selectedComplaint.id, {
        status: updateStatus,
        assigned_officer: assignee || undefined,
        resolution_notes: notes || undefined
      }, token);
      setSelectedComplaint(null);
      await loadData();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!selectedElection) {
    return <div className="p-8 text-center text-slate-400">Select an election to view complaints.</div>;
  }

  const filteredComplaints = filterStatus ? complaints.filter(c => c.status === filterStatus) : complaints;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-blue-500" />
          Complaint Management
        </h1>
        <button onClick={loadData} disabled={loading} className="text-slate-400 hover:text-white p-2">
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/50 text-rose-400 p-4 rounded-lg text-sm">
          {error}
        </div>
      )}

      {selectedComplaint && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium mb-4 flex items-center gap-2"><PenTool className="w-5 h-5 text-blue-400" /> Update Complaint: {selectedComplaint.reference_number}</h2>
          <form onSubmit={handleUpdate} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
              <select value={updateStatus} onChange={e => setUpdateStatus(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200">
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="UNDER_REVIEW">UNDER REVIEW</option>
                <option value="INVESTIGATING">INVESTIGATING</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="DISMISSED">DISMISSED</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Assignee</label>
              <input type="text" value={assignee} onChange={e => setAssignee(e.target.value)} placeholder="Officer ID or Name" className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Resolution Notes</label>
              <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Actions taken..." className="w-full bg-slate-950 border border-slate-700 rounded-md py-2 px-3 text-sm text-slate-200" />
            </div>
            <div className="md:col-span-3 flex justify-end gap-3 mt-2">
              <button type="button" onClick={() => setSelectedComplaint(null)} className="text-slate-400 hover:text-white px-4 py-2 text-sm">Cancel</button>
              <button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded-md font-medium text-sm">Update Complaint</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-3 border-b border-slate-800 bg-slate-950 flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Filter className="w-4 h-4" /> Filter by Status:
          </div>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300">
            <option value="">All</option>
            <option value="SUBMITTED">SUBMITTED</option>
            <option value="UNDER_REVIEW">UNDER REVIEW</option>
            <option value="INVESTIGATING">INVESTIGATING</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-6 py-3 font-medium">Reference</th>
              <th className="px-6 py-3 font-medium">Category</th>
              <th className="px-6 py-3 font-medium w-1/3">Description</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Assigned To</th>
              <th className="px-6 py-3 font-medium">Created</th>
              <th className="px-6 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {filteredComplaints.length ? (
              filteredComplaints.map(c => (
                <tr key={c.id} className="hover:bg-slate-800/20">
                  <td className="px-6 py-3 font-mono text-xs">{c.reference_number}</td>
                  <td className="px-6 py-3 text-xs">{c.category}</td>
                  <td className="px-6 py-3 text-xs text-slate-400 truncate max-w-[200px]" title={c.description}>{c.description}</td>
                  <td className="px-6 py-3">
                    <span className="text-[10px] font-bold bg-slate-800 text-slate-300 px-2 py-1 rounded">
                      {c.status}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-xs">{c.assigned_officer || '-'}</td>
                  <td className="px-6 py-3 text-xs text-slate-500">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-3 text-right">
                    <button
                      onClick={() => {
                        setSelectedComplaint(c);
                        setUpdateStatus(c.status);
                        setAssignee(c.assigned_officer || "");
                        setNotes(c.resolution_notes || "");
                      }}
                      className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                    >
                      Update
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-slate-500">No complaints found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
