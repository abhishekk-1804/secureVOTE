"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ErrorState } from "@/components/ui/ErrorState";
import { AlertCircle, CheckCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { formatApiError } from "@/lib/format-error";

const CONSTITUENCIES = [
  { value: "North District", label: "North District" },
  { value: "South District", label: "South District" },
  { value: "East District", label: "East District" },
  { value: "West District", label: "West District" },
  { value: "Central District", label: "Central District" }
];

export default function RegisterVoterPage() {
  const [formData, setFormData] = useState({
    fullName: "",
    dateOfBirth: "",
    constituency: ""
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<{ voterId: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = { name: formData.fullName, date_of_birth: formData.dateOfBirth, constituency: formData.constituency };
      const response = await api.registerVoter("mock-election", payload, "");
      setSuccessData({ voterId: response.voter_id_number });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({ fullName: "", dateOfBirth: "", constituency: "" });
    setSuccessData(null);
    setError(null);
  };

  if (successData) {
    return (
      <div className="container max-w-2xl mx-auto px-4 py-12">
        <Card className="border-emerald-200 shadow-sm">
          <CardHeader className="text-center pb-4">
            <div className="mx-auto bg-emerald-100 p-3 rounded-full w-16 h-16 flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-emerald-600" />
            </div>
            <CardTitle className="text-2xl text-emerald-800">Registration Successful</CardTitle>
            <CardDescription>Your synthetic voter registration is complete.</CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 mb-6">
              <p className="text-sm text-slate-500 mb-2">Your Voter ID Number</p>
              <p className="text-3xl font-bold text-slate-900 tracking-wider">{successData.voterId}</p>
              <p className="text-sm text-amber-600 mt-4 flex items-center justify-center gap-1">
                <AlertCircle className="h-4 w-4" /> Please save this ID for tracking and voting.
              </p>
            </div>
          </CardContent>
          <CardFooter className="flex justify-center gap-4">
            <Button variant="outline" onClick={resetForm}>Register Another</Button>
            <Button onClick={() => window.location.href="/voter"}>Return to Portal</Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-2xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Voter Registration</h1>
        <p className="text-slate-600">Register as a synthetic voter for the SecureVOTE prototype.</p>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-8 flex items-start">
        <AlertCircle className="h-5 w-5 text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-blue-800">SIMULATED REGISTRATION</h3>
          <p className="text-sm text-blue-700 mt-1">
            This form generates a mock Voter ID for educational purposes. Do not enter real PII.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registration Form</CardTitle>
          <CardDescription>Enter details to generate your voter profile.</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-6">
              <ErrorState
                title="Registration Failed"
                message={error}
                onRetry={() => setError(null)}
              />
            </div>
          )}

          <form id="register-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-slate-700 mb-1">
                Full Name
              </label>
              <Input
                id="fullName"
                required
                placeholder="e.g., John Doe"
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
            <a href="/voter">Cancel</a>
          </Button>
          <Button type="submit" form="register-form" disabled={loading} loading={loading}>
            Submit Registration
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
