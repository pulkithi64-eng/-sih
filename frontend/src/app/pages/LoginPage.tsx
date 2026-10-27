import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, Building2, FileCheck2, Fingerprint, Loader2, Lock, ScrollText, ShieldCheck, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/common/Logo";
import { errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { homePathFor, useAuth } from "../auth";

const DEMO_PASSWORD = "Demo@2026";

const DEMO_USERS = [
  { username: "officer.wro", role: "Scrutiny Officer", scope: "Western Region", icon: FileCheck2 },
  { username: "rd.wro", role: "Regional Director", scope: "Western Region", icon: ShieldCheck },
  { username: "inst.piat", role: "Institution", scope: "Nodal officer", icon: Building2 },
  { username: "inst.apex", role: "Institution", scope: "Nodal officer", icon: Building2 },
  { username: "officer.nro", role: "Scrutiny Officer", scope: "Northern Region", icon: FileCheck2 },
  { username: "admin", role: "Administrator", scope: "Rules, sources, audit", icon: Lock },
];

const POINTS = [
  { icon: ScrollText, title: "Checklist & rule validation", text: "Category-specific checklists and configurable, versioned rules with clause references." },
  { icon: Fingerprint, title: "Document evidence", text: "Signed-QR checks, simulated issuer lookups and preliminary integrity indicators." },
  { icon: ShieldCheck, title: "Explainable, auditable", text: "Every flag carries evidence; every action lands in a hash-chained audit trail." },
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to={from && from !== "/portal/login" ? from : homePathFor(user.role)} replace />;

  async function doLogin(u: string, p: string) {
    setBusy(true);
    setError(null);
    try {
      const me = await login(u, p);
      nav(from && from !== "/portal/login" ? from : homePathFor(me.role), { replace: true });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {/* Brand panel */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-navy p-10 text-white lg:flex">
        <div className="relative">
          <Logo inverted withTagline />
        </div>
        <div className="relative max-w-md">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-saffron">Scrutiny decision support</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight">
              Documents, evidence and clear next steps.
          </h1>
          <ul className="mt-8 space-y-5">
            {POINTS.map((p) => (
              <li key={p.title} className="flex gap-3">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/10">
                  <p.icon className="h-4 w-4" aria-hidden />
                </span>
                <span>
                  <span className="block text-sm font-semibold">{p.title}</span>
                  <span className="block text-sm text-white/70">{p.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/50">Prototype built for AICTE · SIH 2026 · PS 26261</p>
      </aside>

      {/* Form */}
      <main className="flex flex-col bg-background">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="lg:hidden">
            <Logo />
          </div>
          <Link to="/" className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" aria-hidden /> Back to website
          </Link>
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-10 sm:px-6">
          <div className="w-full max-w-md">
            <h2 className="text-2xl font-semibold tracking-tight">Sign in to the portal</h2>
            <p className="mt-1 text-sm text-muted-foreground">Sign in to manage applications and review documents.</p>

            <form
              className="mt-6 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                doLogin(username.trim(), password);
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="username">Username</Label>
                <Input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && (
                <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {error}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
                Sign in
              </Button>
            </form>

            <details className="mt-6 rounded-lg border bg-card p-4">
              <summary className="cursor-pointer text-sm font-medium">Try a demo account</summary>
              <div className="mt-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Demo accounts</p>
                <p className="text-xs text-muted-foreground">
                  Password <span className="mono rounded bg-muted px-1 py-0.5 text-foreground">{DEMO_PASSWORD}</span>
                </p>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {DEMO_USERS.map((d) => (
                  <button
                    key={d.username}
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setUsername(d.username);
                      setPassword(DEMO_PASSWORD);
                      doLogin(d.username, DEMO_PASSWORD);
                    }}
                    className={cn(
                      "group flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-left transition-colors",
                      "hover:border-primary-600/50 hover:bg-navy-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60",
                    )}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-navy-50 text-navy group-hover:bg-white">
                      <d.icon className="h-4 w-4" aria-hidden />
                    </span>
                    <span className="min-w-0">
                      <span className="mono block truncate font-medium text-foreground">{d.username}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {d.role} · {d.scope}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
              </div>
            </details>

            <div className="mt-8 rounded-md border bg-card px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
              <UserRound className="mr-1 inline h-3.5 w-3.5 align-[-2px]" aria-hidden />
              <strong className="font-semibold text-foreground">Prototype disclaimer.</strong> This is a hackathon prototype using synthetic
              institutions and documents. It is not an official AICTE system. Automated outputs are advisory and require officer review.
            </div>
          </div>
        </div>
        <footer className="border-t px-6 py-3 text-center text-xs text-muted-foreground lg:hidden">
          Prototype built for AICTE · SIH 2026 · PS 26261
        </footer>
      </main>
    </div>
  );
}
