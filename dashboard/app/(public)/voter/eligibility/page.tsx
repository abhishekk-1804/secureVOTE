"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { AlertCircle, CheckCircle, XCircle, HelpCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

const CONSTITUENCIES = [
  { value: "North District", label: "North District" },
  { value: "South District", label: "South District" },
  { value: "East District", label: "East District" },
  { value: "West District", label: "West District" },
  { value: "Central District", label: "Central District" }
];

export default function EligibilityCheckerPage() {
  const [formData, setFormData] = useState({
    fullName: "",
    dateOfBirth: "",
    constituency: ""
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = { name: formData.fullName, date_of_birth: formData.dateOfBirth, constituency: formData.constituency };
      const response = await api.checkEligibility("mock-election", payload);
      setResult(response);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ELIGIBLE': return <CheckCircle className="h-12 w-12 text-emerald-500" />;
      case 'NOT_ELIGIBLE': return <XCircle className="h-12 w-12 text-rose-500" />;
      case 'NEEDS_REVIEW': return <HelpCircle className="h-12 w-12 text-amber-500" />;
      default: return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ELIGIBLE': return "success";
      case 'NOT_ELIGIBLE': return "danger";
      case 'NEEDS_REVIEW': return "warning";
      default: return "neutral";
    }
  };

  return (
    <div className="container max-w-2xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Eligibility Checker</h1>
        <p className="text-slate-600">Verify if you are eligible to vote in the upcoming elections.</p>
      </div>

      <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4 mb-8 flex items-start">
        <AlertCircle className="h-5 w-5 text-indigo-600 mr-3 mt-0.5 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-indigo-800">SIMULATED ELIGIBILITY CHECK</h3>
          <p className="text-sm text-indigo-700 mt-1">
            This tool simulates eligibility logic for educational purposes.
          </p>
        </div>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Check Status</CardTitle>
            <CardDescription>Enter your details to verify eligibility.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-6">
                <ErrorState
                  title="Check Failed"
                  message={error}
                  onRetry={() => setError(null)}
                />
              </div>
            )}

            <form id="eligibility-form" onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-slate-700 mb-1">
                  Full Name
                </label>
                <Input
                  id="fullName"
                  required
                  placeholder="e.g., Jane Doe"
                  value={formData.fullName}
                  onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                  disabled={loading}
                />
              </div>

              <div>
                <label htmlFor="dateOfBirth" className="block text-sm font-medium text-slate-700 mb-1">
                  Date of Birth
                </label>
                <Input
                  id="dateOfBirth"
                  type="date"
                  required
                  value={formData.dateOfBirth}
                  onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
                  disabled={loading}
                />
              </div>

              <div>
                <label htmlFor="constituency" className="block text-sm font-medium text-slate-700 mb-1">
                  Constituency
                </label>
                <Select
                  id="constituency"
                  options={CONSTITUENCIES}
                  value={formData.constituency}
                  onChange={(e) => setFormData({ ...formData, constituency: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>
            </form>
          </CardContent>
          <CardFooter className="flex justify-between border-t border-slate-100 pt-4">
            <Button variant="ghost" disabled={loading}>
              <a href="/voter">Back</a>
            </Button>
            <Button type="submit" form="eligibility-form" disabled={loading} loading={loading}>
              Check Eligibility
            </Button>
          </CardFooter>
        </Card>

        {result && (
          <Card className={`border-${getStatusColor(result.status)}-200`}>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center text-center">
                {getStatusIcon(result.status)}
                <h3 className="text-xl font-bold mt-4 mb-2">Eligibility Status</h3>
                <Badge variant={getStatusColor(result.status) as any} className="mb-4 text-sm px-3 py-1">
                  {result.status.replace('_', ' ')}
                </Badge>

                {result.reasons && result.reasons.length > 0 && (
                  <div className="w-full mt-4 text-left bg-slate-50 p-4 rounded-md border border-slate-100">
                    <p className="font-medium text-slate-700 mb-2">Details:</p>
                    <ul className="list-disc pl-5 space-y-1 text-slate-600">
                      {result.reasons.map((reason: string, idx: number) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
