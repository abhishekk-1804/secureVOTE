"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { MapPin, Search, Building2, User, Cpu, Info } from "lucide-react";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

interface PollingStationItem {
  id: string;
  station_code: string;
  name: string;
  constituency: string;
  location: string;
  status: string;
  officer_name?: string | null;
  assigned_devices?: number;
  registered_voters?: number;
}

const REFERENCE_CONSTITUENCIES = [
  { value: "Bengaluru Central", label: "Bengaluru Central (PC-25, Karnataka)" },
  { value: "Bengaluru South", label: "Bengaluru South (PC-26, Karnataka)" },
  { value: "Bengaluru North", label: "Bengaluru North (PC-24, Karnataka)" },
  { value: "Mumbai South", label: "Mumbai South (PC-31, Maharashtra)" },
  { value: "New Delhi", label: "New Delhi (PC-04, NCT of Delhi)" },
  { value: "Varanasi", label: "Varanasi (PC-77, Uttar Pradesh)" },
  { value: "Kolkata Uttar", label: "Kolkata Uttar (PC-24, West Bengal)" },
  { value: "Chennai Central", label: "Chennai Central (PC-04, Tamil Nadu)" },
];

export default function PollingStationPage() {
  const [constituency, setConstituency] = useState("Bengaluru Central");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<PollingStationItem[] | null>(null);

  const fetchStations = async (selectedConst: string) => {
    setLoading(true);
    setError(null);
    try {
      const demoStations = await api.getPollingStations("EV-2026-001");
      const matched = demoStations.filter(
        (s: any) =>
          s.constituency?.toLowerCase().includes(selectedConst.toLowerCase()) ||
          selectedConst.toLowerCase().includes(s.constituency?.toLowerCase() || "")
      );

      if (matched.length > 0) {
        setResults(
          matched.map((s: any) => ({
            id: s.id,
            station_code: s.station_code || `PS-${s.id.slice(-3)}`,
            name: s.name,
            constituency: s.constituency,
            location: s.location,
            status: s.status || "ACTIVE",
            officer_name: s.officer_name || "Presiding Officer",
            assigned_devices: s.assigned_devices || 2,
            registered_voters: s.registered_voters || 850,
          }))
        );
      } else {
        const syntheticStations: PollingStationItem[] = [
          {
            id: `${selectedConst}-PS01`,
            station_code: "PS-001",
            name: `Govt Higher Secondary School, Room No. 1`,
            constituency: selectedConst,
            location: `Main Civic Center, Sector 4, ${selectedConst}`,
            status: "ACTIVE",
            officer_name: "R. K. Sharma, Sector Officer",
            assigned_devices: 2,
            registered_voters: 920,
          },
          {
            id: `${selectedConst}-PS02`,
            station_code: "PS-002",
            name: `Community Welfare Center, Ground Floor`,
            constituency: selectedConst,
            location: `Near Town Hall, ${selectedConst}`,
            status: "ACTIVE",
            officer_name: "Priya V., Presiding Officer",
            assigned_devices: 2,
            registered_voters: 845,
          },
        ];
        setResults(syntheticStations);
      }
    } catch (err: any) {
      setResults([
        {
          id: "PS-001",
          station_code: "PS-001",
          name: "Govt Higher Primary School, MG Road",
          constituency: "Bengaluru Central",
          location: "Shivajinagar, Bengaluru",
          status: "ACTIVE",
          officer_name: "Rajesh Sharma",
          assigned_devices: 2,
          registered_voters: 500,
        },
        {
          id: "PS-002",
          station_code: "PS-002",
          name: "Community Center, Indiranagar 100ft Rd",
          constituency: "Bengaluru Central",
          location: "Indiranagar, Bengaluru",
          status: "ACTIVE",
          officer_name: "Priya Sundaram",
          assigned_devices: 2,
          registered_voters: 500,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStations(constituency);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!constituency) return;
    fetchStations(constituency);
  };

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Find Polling Station</h1>
        <p className="text-slate-600 text-sm">
          Search your Parliamentary Constituency (PC) to view designated Polling Stations and Booth Level Officer (BLO) details.
        </p>
      </div>

      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-8 flex items-start text-xs text-amber-900">
        <Info className="h-4 w-4 text-amber-600 mr-2.5 mt-0.5 flex-shrink-0" />
        <div>
          <span className="font-bold">Electoral Hierarchy Reference (Simulation):</span> In Indian parliamentary elections, voting occurs at designated Polling Stations mapped hierarchically:
          <span className="font-semibold text-slate-900"> State → District → Parliamentary Constituency (PC) → Assembly Constituency (AC) → Polling Station</span>.
          All polling stations, officer names, and counts shown here are synthetic simulation records for educational demonstration. SecureVOTE is not an official government portal.
        </div>
      </div>

      <Card className="mb-8">
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label htmlFor="constituency" className="block text-xs font-semibold text-slate-700 mb-1">
                Select Parliamentary Constituency
              </label>
              <Select
                id="constituency"
                options={REFERENCE_CONSTITUENCIES}
                value={constituency}
                onChange={(e) => setConstituency(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={loading || !constituency} loading={loading} className="w-full sm:w-auto">
                <Search className="h-4 w-4 mr-2" />
                Find Stations
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <ErrorState
          title="Search Failed"
          message={error}
          onRetry={() => fetchStations(constituency)}
        />
      )}

      {results !== null && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-900">
              Polling Stations in {constituency} ({results.length})
            </h2>
            <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
              EVM DIGITAL TWIN COMPATIBLE
            </span>
          </div>

          {results.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-slate-500">
                No polling stations found for this constituency in the reference dataset.
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {results.map((station) => (
                <Card key={station.id} className="border border-slate-200 hover:shadow-md transition-shadow">
                  <CardContent className="p-5 space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="p-2.5 bg-rose-50 text-rose-600 rounded-lg mt-0.5">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                            {station.station_code}
                          </span>
                          <Badge variant={station.status === "ACTIVE" ? "success" : "warning"}>
                            {station.status}
                          </Badge>
                        </div>
                        <h3 className="font-bold text-slate-900 text-sm leading-snug">{station.name}</h3>
                        <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          {station.location}
                        </p>
                      </div>
                    </div>

                    <div className="border-t border-slate-100 pt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                      <div>
                        <span className="text-[11px] text-slate-400 block">Officer in Charge:</span>
                        <span className="font-medium text-slate-800 flex items-center gap-1 mt-0.5">
                          <User className="w-3 h-3 text-slate-400" />
                          {station.officer_name || "Presiding Officer"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[11px] text-slate-400 block">Deployed EVMs:</span>
                        <span className="font-medium text-slate-800 flex items-center gap-1 mt-0.5">
                          <Cpu className="w-3 h-3 text-blue-500" />
                          {station.assigned_devices || 2} Units (CU + BU + VVPAT)
                        </span>
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
