"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { MapPin, Search } from "lucide-react";

// Mock data for polling stations since there might not be a backend endpoint for this yet
const MOCK_STATIONS = [
  { id: "PS-001", name: "North District Community Center", location: "123 Main St, North District", constituency: "North District", status: "ACTIVE" },
  { id: "PS-002", name: "North District High School", location: "456 School Ln, North District", constituency: "North District", status: "ACTIVE" },
  { id: "PS-003", name: "South District City Hall", location: "789 Civic Pl, South District", constituency: "South District", status: "ACTIVE" },
  { id: "PS-004", name: "East District Library", location: "101 Book St, East District", constituency: "East District", status: "ACTIVE" },
  { id: "PS-005", name: "West District Sports Complex", location: "202 Arena Blvd, West District", constituency: "West District", status: "ACTIVE" },
  { id: "PS-006", name: "Central District Square", location: "303 Center Ave, Central District", constituency: "Central District", status: "MAINTENANCE" }
];

const CONSTITUENCIES = [
  { value: "North District", label: "North District" },
  { value: "South District", label: "South District" },
  { value: "East District", label: "East District" },
  { value: "West District", label: "West District" },
  { value: "Central District", label: "Central District" }
];

export default function PollingStationPage() {
  const [constituency, setConstituency] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any[] | null>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!constituency) return;

    setLoading(true);
    setError(null);

    // Simulate API call
    setTimeout(() => {
      try {
        const filtered = MOCK_STATIONS.filter(s => s.constituency === constituency);
        setResults(filtered);
      } catch (err: any) {
        setError(err.message || "Failed to find polling stations.");
      } finally {
        setLoading(false);
      }
    }, 600);
  };

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Find Polling Station</h1>
        <p className="text-slate-600">Locate your designated polling station for election day.</p>
      </div>

      <Card className="mb-8">
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Select
                id="constituency"
                options={CONSTITUENCIES}
                value={constituency}
                onChange={(e) => setConstituency(e.target.value)}
                disabled={loading}
              />
            </div>
            <Button type="submit" disabled={loading || !constituency} loading={loading}>
              <Search className="h-4 w-4 mr-2" />
              Find Stations
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <ErrorState
          title="Search Failed"
          message={error}
          onRetry={() => setError(null)}
        />
      )}

      {results !== null && (
        <div>
          <h2 className="text-xl font-semibold mb-4">
            Polling Stations in {constituency} ({results.length})
          </h2>

          {results.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-slate-500">
                No polling stations found for this constituency.
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {results.map((station) => (
                <Card key={station.id}>
                  <CardContent className="p-5 flex items-start gap-4">
                    <div className="p-3 bg-rose-50 text-rose-500 rounded-full mt-1">
                      <MapPin className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start mb-1">
                        <h3 className="font-bold text-slate-900">{station.name}</h3>
                      </div>
                      <p className="text-sm text-slate-500 mb-3">{station.location}</p>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-400 font-mono">{station.id}</span>
                        <Badge variant={station.status === 'ACTIVE' ? 'success' : 'warning'}>
                          {station.status}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
