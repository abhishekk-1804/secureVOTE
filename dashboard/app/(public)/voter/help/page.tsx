"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Info, CheckSquare, Settings, Accessibility, HelpCircle } from "lucide-react";

export default function HelpPage() {
  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Voting Guide</h1>
        <p className="text-slate-600">Information to help you participate in the democratic process.</p>
      </div>

      <div className="space-y-8">
        <section>
          <div className="flex items-center gap-3 mb-4">
            <CheckSquare className="h-6 w-6 text-indigo-500" />
            <h2 className="text-2xl font-semibold">How to Vote</h2>
          </div>
          <Card>
            <CardContent className="pt-6">
              <ol className="list-decimal pl-5 space-y-4 text-slate-700">
                <li className="pl-2">
                  <strong className="text-slate-900">Check Eligibility:</strong> Verify your registration status and assigned polling station before election day.
                </li>
                <li className="pl-2">
                  <strong className="text-slate-900">Authentication:</strong> Present your valid Voter ID or accepted alternative identification to the polling officer.
                </li>
                <li className="pl-2">
                  <strong className="text-slate-900">Verification:</strong> The officer will verify your details against the electoral roll and mark your finger with indelible ink.
                </li>
                <li className="pl-2">
                  <strong className="text-slate-900">Cast Your Vote:</strong> Proceed to the voting compartment. Press the blue button next to your chosen candidate on the EVM.
                </li>
                <li className="pl-2">
                  <strong className="text-slate-900">Confirmation:</strong> Verify your vote on the VVPAT machine. A slip will print, be visible for 7 seconds, and then drop into the sealed box.
                </li>
              </ol>
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-4">
            <Info className="h-6 w-6 text-indigo-500" />
            <h2 className="text-2xl font-semibold">What to Bring</h2>
          </div>
          <Card>
            <CardContent className="pt-6">
              <p className="mb-4 text-slate-700">In statutory elections, voters present an official Voter ID (EPIC). In this prototype, the following simulated documents are accepted:</p>
              <ul className="list-disc pl-5 space-y-2 text-slate-700">
                <li>Aadhaar Card</li>
                <li>Passport</li>
                <li>Driving License</li>
                <li>PAN Card</li>
                <li>Government employee service ID card</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-4">
            <Settings className="h-6 w-6 text-indigo-500" />
            <h2 className="text-2xl font-semibold">EVM Operation Guide</h2>
          </div>
          <Card>
            <CardContent className="pt-6 text-slate-700 space-y-4">
              <p>The Electronic Voting Machine (EVM) is simple to use:</p>
              <ul className="list-disc pl-5 space-y-2">
                <li>The machine lists candidate names, photos, and party symbols.</li>
                <li>Press the <strong>BLUE BUTTON</strong> adjacent to the symbol of your preferred candidate.</li>
                <li>A red light will glow next to the candidate's name, accompanied by a long beep sound.</li>
                <li>This confirms that your vote has been securely recorded.</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-4">
            <Accessibility className="h-6 w-6 text-indigo-500" />
            <h2 className="text-2xl font-semibold">Accessibility Options</h2>
          </div>
          <Card>
            <CardContent className="pt-6 text-slate-700 space-y-4">
              <p>SecureVOTE ensures elections are accessible to all citizens:</p>
              <ul className="list-disc pl-5 space-y-2">
                <li>All polling stations are equipped with ramps for wheelchair access.</li>
                <li>Braille signage is available on EVMs for visually impaired voters.</li>
                <li>Voters with disabilities or seniors (80+) can request assistance or use the postal ballot facility.</li>
                <li>Special queues are designated for senior citizens and persons with disabilities.</li>
              </ul>
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-3 mb-4">
            <HelpCircle className="h-6 w-6 text-indigo-500" />
            <h2 className="text-2xl font-semibold">Frequently Asked Questions</h2>
          </div>
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="font-semibold text-slate-900 mb-1">What if my name is not on the voter list?</h3>
                <p className="text-slate-700 text-sm">You cannot vote if your name is absent from the electoral roll, even if you possess a Voter ID. Please verify your registration status well before election day.</p>
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 mb-1">Are mobile phones allowed inside?</h3>
                <p className="text-slate-700 text-sm">No, mobile phones, cameras, and other electronic devices are strictly prohibited inside the voting compartment to ensure ballot secrecy.</p>
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 mb-1">What is NOTA?</h3>
                <p className="text-slate-700 text-sm">NOTA stands for "None of the Above". It is an option on the EVM that allows you to officially register your rejection of all contesting candidates.</p>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
