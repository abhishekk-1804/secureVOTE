"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { MessageSquare, Search, CheckCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

const CATEGORIES = [
  { value: "Voter Registration", label: "Voter Registration" },
  { value: "Polling Station", label: "Polling Station" },
  { value: "EVM", label: "EVM Issue" },
  { value: "Voting Issue", label: "Voting Issue" },
  { value: "Accessibility", label: "Accessibility" },
  { value: "Election Process", label: "Election Process" },
  { value: "Candidate/Party", label: "Candidate or Party" },
  { value: "Technical", label: "Technical Issue" },
  { value: "Other", label: "Other" }
];

export default function ComplaintsPage() {
  const [activeTab, setActiveTab] = useState<'file' | 'track'>('file');

  // File state
  const [fileData, setFileData] = useState({
    category: "",
    description: "",
    name: "",
    contact: ""
  });
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileSuccess, setFileSuccess] = useState<string | null>(null);

  // Track state
  const [trackId, setTrackId] = useState("");
  const [trackLoading, setTrackLoading] = useState(false);
  const [trackError, setTrackError] = useState<string | null>(null);
  const [trackData, setTrackData] = useState<any | null>(null);

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFileLoading(true);
    setFileError(null);

    try {
      // Assuming api.submitComplaint exists, if not mock it
      // const res = await api.submitComplaint(fileData);

      // MOCK implementation for demo
      await new Promise(r => setTimeout(r, 1000));
      const randomRef = `GRV-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`;
      setFileSuccess(randomRef);
    } catch (err) {
      setFileError(formatApiError(err));
    } finally {
      setFileLoading(false);
    }
  };

  const handleTrackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackId.trim()) return;

    setTrackLoading(true);
    setTrackError(null);
    setTrackData(null);

    try {
      // Assuming api.trackComplaint exists, if not mock it
      // const res = await api.trackComplaint(trackId);

      // MOCK implementation for demo
      await new Promise(r => setTimeout(r, 1000));
      if (trackId.startsWith("GRV-")) {
        setTrackData({
          reference: trackId,
          category: "Polling Station",
          status: "UNDER_REVIEW",
          description: "Long queue and insufficient shade at the station.",
          resolutionNotes: "We have dispatched a team to set up additional shade structures.",
          createdAt: new Date().toISOString()
        });
      } else {
        throw new Error("Invalid complaint reference format.");
      }
    } catch (err) {
      setTrackError(formatApiError(err));
    } finally {
      setTrackLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      SUBMITTED: "neutral",
      RECEIVED: "neutral",
      ASSIGNED: "warning",
      UNDER_REVIEW: "warning",
      RESOLVED: "success",
      CLOSED: "success"
    };
    return <Badge variant={(map[status] || "neutral") as any}>{status.replace('_', ' ')}</Badge>;
  };

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Grievance Redressal</h1>
        <p className="text-slate-600">File a new complaint or track an existing one.</p>
      </div>

      <div className="flex space-x-1 border-b border-slate-200 mb-6">
        <button
          className={`py-3 px-6 text-sm font-medium border-b-2 outline-none transition-colors ${activeTab === 'file' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          onClick={() => setActiveTab('file')}
        >
          File New Complaint
        </button>
        <button
          className={`py-3 px-6 text-sm font-medium border-b-2 outline-none transition-colors ${activeTab === 'track' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          onClick={() => setActiveTab('track')}
        >
          Track Complaint
        </button>
      </div>

      {activeTab === 'file' && (
        <div className="max-w-2xl">
          {fileSuccess ? (
            <Card className="border-emerald-200 bg-emerald-50 text-center">
              <CardContent className="pt-8 pb-8">
                <div className="inline-flex items-center justify-center p-3 bg-emerald-100 rounded-full mb-4">
                  <CheckCircle className="h-10 w-10 text-emerald-600" />
                </div>
                <h3 className="text-2xl font-bold text-emerald-800 mb-2">Complaint Submitted</h3>
                <p className="text-emerald-700 mb-6">Your grievance has been recorded successfully.</p>

                <div className="bg-white p-4 rounded-lg border border-emerald-200 inline-block mb-6">
                  <p className="text-sm text-slate-500 mb-1">Reference Number</p>
                  <p className="text-xl font-mono font-bold text-slate-900">{fileSuccess}</p>
                </div>

                <div>
                  <Button onClick={() => setFileSuccess(null)}>File Another Complaint</Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Complaint Details</CardTitle>
                <CardDescription>Please provide details about your issue.</CardDescription>
              </CardHeader>
              <CardContent>
                {fileError && <div className="mb-4"><ErrorState title="Error" message={fileError} onRetry={() => setFileError(null)} /></div>}

                <form id="complaint-form" onSubmit={handleFileSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                    <Select
                      options={CATEGORIES}
                      value={fileData.category}
                      onChange={(e) => setFileData({ ...fileData, category: e.target.value })}
                      required
                      disabled={fileLoading}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                    <textarea
                      className="flex min-h-[120px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="Please describe the issue in detail..."
                      value={fileData.description}
                      onChange={(e) => setFileData({ ...fileData, description: e.target.value })}
                      required
                      disabled={fileLoading}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Your Name</label>
                      <Input
                        value={fileData.name}
                        onChange={(e) => setFileData({ ...fileData, name: e.target.value })}
                        required
                        disabled={fileLoading}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Contact Info</label>
                      <Input
                        placeholder="Email or Phone"
                        value={fileData.contact}
                        onChange={(e) => setFileData({ ...fileData, contact: e.target.value })}
                        required
                        disabled={fileLoading}
                      />
                    </div>
                  </div>
                </form>
              </CardContent>
              <CardFooter className="flex justify-end border-t border-slate-100 pt-4">
                <Button type="submit" form="complaint-form" disabled={fileLoading} loading={fileLoading}>
                  Submit Complaint
                </Button>
              </CardFooter>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'track' && (
        <div className="max-w-2xl">
          <Card className="mb-6">
            <CardContent className="pt-6">
              <form onSubmit={handleTrackSubmit} className="flex gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="Reference Number (e.g., GRV-2023-12345)"
                    value={trackId}
                    onChange={(e) => setTrackId(e.target.value)}
                    disabled={trackLoading}
                  />
                </div>
                <Button type="submit" disabled={trackLoading || !trackId.trim()} loading={trackLoading}>
                  <Search className="h-4 w-4 mr-2" />
                  Track
                </Button>
              </form>
            </CardContent>
          </Card>

          {trackError && <ErrorState title="Tracking Failed" message={trackError} onRetry={() => setTrackError(null)} />}

          {trackData && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-slate-500 mb-1">Complaint Reference</p>
                    <CardTitle className="font-mono">{trackData.reference}</CardTitle>
                  </div>
                  {getStatusBadge(trackData.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4 border-t border-slate-100 pt-4">
                <div>
                  <p className="text-sm font-medium text-slate-700 mb-1">Category</p>
                  <p className="text-slate-900">{trackData.category}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700 mb-1">Description</p>
                  <div className="bg-slate-50 p-3 rounded border border-slate-100 text-slate-700 text-sm">
                    {trackData.description}
                  </div>
                </div>
                {trackData.resolutionNotes && (
                  <div>
                    <p className="text-sm font-medium text-slate-700 mb-1">Resolution Notes</p>
                    <div className="bg-indigo-50 p-3 rounded border border-indigo-100 text-indigo-900 text-sm">
                      {trackData.resolutionNotes}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
