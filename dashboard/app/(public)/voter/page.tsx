"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  AlertCircle,
  UserPlus,
  CheckCircle,
  Search,
  MapPin,
  Users,
  HelpCircle,
  MessageSquare,
  Vote,
  FileSpreadsheet,
  Globe,
  Accessibility,
} from "lucide-react";

export default function VoterPortalPage() {
  const services = [
    {
      title: "Cast Vote (Digital EVM)",
      description: "Experience the EVM digital twin simulation (CU, BU, and 7-second VVPAT slip).",
      icon: <Vote className="h-6 w-6 text-amber-500" />,
      href: "/voter/vote",
      badge: "SIMULATION",
    },
    {
      title: "Search Electoral Roll",
      description: "Search your name in the electoral roll and generate simulated e-EPIC / voter slip.",
      icon: <FileSpreadsheet className="h-6 w-6 text-blue-600" />,
      href: "/voter/roll",
      badge: "ELECTORAL ROLL",
    },
    {
      title: "Check Eligibility",
      description: "Verify age, citizenship, and residency qualifications for the current electoral revision.",
      icon: <CheckCircle className="h-6 w-6 text-emerald-500" />,
      href: "/voter/eligibility",
      badge: "REPRESENTATION OF THE PEOPLE ACT",
    },
    {
      title: "Voter Registration (Form 6)",
      description: "Simulate Form 6 enrollment for new electors or Form 8 for shift/correction.",
      icon: <UserPlus className="h-6 w-6 text-blue-500" />,
      href: "/voter/register",
      badge: "FORM 6 / 8",
    },
    {
      title: "Check Application Status",
      description: "Track Form 6 reference number or verify voter card issuance status.",
      icon: <Search className="h-6 w-6 text-indigo-500" />,
      href: "/voter/status",
      badge: "TRACK STATUS",
    },
    {
      title: "Find Polling Station",
      description: "Locate your designated Polling Station, Assembly Constituency (AC), and PC details.",
      icon: <MapPin className="h-6 w-6 text-rose-500" />,
      href: "/voter/polling-station",
      badge: "STATION & BLO",
    },
    {
      title: "Contesting Candidates",
      description: "Explore candidates, party symbols, and disclosures in your constituency.",
      icon: <Users className="h-6 w-6 text-amber-600" />,
      href: "/voter/candidates",
      badge: "FORM 7A",
    },
    {
      title: "Overseas Elector (Form 6A)",
      description: "Dual-mode simulator for Non-Resident Indian (NRI) electors and consular sessions.",
      icon: <Globe className="h-6 w-6 text-teal-600" />,
      href: "/voter/overseas",
      badge: "NRI / SECTION 20A",
    },
    {
      title: "Grievance Redressal",
      description: "Submit simulated election complaints or report polling-station issues.",
      icon: <MessageSquare className="h-6 w-6 text-orange-500" />,
      href: "/voter/complaints",
      badge: "NGSP / COMPLAINTS",
    },
    {
      title: "EVM & VVPAT Guide",
      description: "Learn how the Control Unit, Ballot Unit, 7s VVPAT slip, and NOTA operate.",
      icon: <HelpCircle className="h-6 w-6 text-slate-500" />,
      href: "/voter/help",
      badge: "VOTER EDUCATION",
    },
  ];

  return (
    <div className="container max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Voter Services Portal</h1>
        <p className="text-slate-600">Access all citizen services for SecureVOTE.</p>
      </div>

      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-8 flex items-start">
        <AlertCircle className="h-5 w-5 text-amber-600 mr-3 mt-0.5 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-amber-800">DEMO DATA - SIMULATED IDENTITY</h3>
          <p className="text-sm text-amber-700 mt-1">
            This is an educational prototype. Do not enter real personal information.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map((service, index) => (
          <Card key={index} className="hover:shadow-md transition-shadow flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    {service.icon}
                  </div>
                  <CardTitle className="text-lg">{service.title}</CardTitle>
                </div>
              </div>
              {service.badge && (
                <span className="inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold mb-2">
                  {service.badge}
                </span>
              )}
              <CardDescription>{service.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Link href={service.href} className="w-full block">
                <Button as="span" className="w-full" variant="outline">
                  Access Service
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Accessibility & ECI Procedure Reference Note */}
      <div className="mt-12 bg-slate-50 border border-slate-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-100 text-blue-700 rounded-xl shrink-0">
            <Accessibility className="w-6 h-6" />
          </div>
          <div className="space-y-2">
            <h2 className="text-base font-bold text-slate-900">
              Reference Information: Electoral Accessibility &amp; Facilities
            </h2>
            <p className="text-xs text-slate-600 leading-relaxed">
              Reference context regarding statutory Indian voting practice: Rule 49N of the Conduct of Elections Rules, 1961 provides for companion assistance for electors with visual or physical infirmity. Standard ECI polling station guidelines reference ramp access, ground-floor voting compartments, Braille numbering on Ballot Units, and queue facilitation for Senior Citizens and Persons with Disabilities (PwD). SecureVOTE provides this context purely for voter education and research demonstration.
            </p>
            <div className="pt-2 flex flex-wrap gap-4 text-xs font-medium text-slate-700">
              <span className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Braille EVM Keypad Reference
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Ground Floor Ramp Standards
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Rule 49N Companion Provision
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Voter Assistance Booth (VAB) Norms
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
