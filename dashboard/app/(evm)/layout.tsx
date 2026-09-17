export default function EvmLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {children}
    </div>
  );
}
