"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AlertCircle, UserPlus, CheckCircle, Search, MapPin, Users, HelpCircle, MessageSquare } from "lucide-react";

export default function VoterPortalPage() {
  const services = [
    {
      title: "Check Eligibility",
      description: "Verify if you are eligible to vote in the upcoming elections.",
      icon: <CheckCircle className="h-6 w-6 text-emerald-500" />,
      href: "/voter/eligibility"
    },
    {
      title: "Register to Vote",
      description: "Register as a new voter and get your Voter ID Number.",
      icon: <UserPlus className="h-6 w-6 text-blue-500" />,
      href: "/voter/register"
    },
    {
      title: "Check Voting Status",
      description: "Track your application or view your voting record.",
      icon: <Search className="h-6 w-6 text-indigo-500" />,
      href: "/voter/status"
    },
    {
      title: "Find Polling Station",
      description: "Locate your designated polling station for election day.",
      icon: <MapPin className="h-6 w-6 text-rose-500" />,
      href: "/voter/polling-station"
    },
    {
      title: "View Candidates",
      description: "Explore the candidates running in your constituency.",
      icon: <Users className="h-6 w-6 text-amber-500" />,
      href: "/voter/candidates"
    },
    {
      title: "File Complaint",
      description: "Submit and track grievances regarding the election process.",
      icon: <MessageSquare className="h-6 w-6 text-orange-500" />,
      href: "/voter/complaints"
    },
    {
      title: "Voting Guide",
      description: "Learn about the voting process, requirements, and EVM operation.",
      icon: <HelpCircle className="h-6 w-6 text-slate-500" />,
      href: "/voter/help"
    }
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
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-4 mb-2">
                <div className="p-2 bg-slate-100 rounded-lg">
                  {service.icon}
                </div>
                <CardTitle className="text-xl">{service.title}</CardTitle>
              </div>
              <CardDescription>{service.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" variant="outline">
                <Link href={service.href}>Access Service</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
