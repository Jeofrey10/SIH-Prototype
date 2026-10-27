import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Lock, Mail, AlertCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/useAuth";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const from = (location.state as any)?.from?.pathname || "/dashboard";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please enter both email/username and password");
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || "Invalid credentials or account locked");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-16 h-16 rounded-xl bg-brand-600 mx-auto flex items-center justify-center font-bold text-2xl text-white shadow-lg border border-brand-400">
          AICTE
        </div>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-white">
          Complaint Monitoring &amp; Coordination Portal
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          All India Council for Technical Education
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow-xl sm:rounded-lg sm:px-10 border border-slate-700">
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3 bg-red-950/60 border border-red-500/40 rounded-md flex items-center gap-2.5 text-xs text-red-200">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label
                htmlFor="username"
                className="block text-xs font-medium text-slate-300 mb-1"
              >
                Official Email or Username
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  placeholder="name@aicte.gov.in"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-slate-300 mb-1"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 disabled:opacity-50 transition-colors"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  "Sign In"
                )}
              </button>
            </div>
          </form>

          {/* Quick-Fill Demo Credentials */}
          <div className="mt-8 pt-6 border-t border-slate-700">
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              <ShieldCheck className="w-4 h-4 text-amber-400" />
              <span>Demo Quick-Fill Accounts</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() =>
                  handleQuickFill("supervisor@aicte.gov.in", "Supervisor@123")
                }
                className="p-2 rounded bg-slate-900/80 hover:bg-slate-700 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-amber-300">Supervisor</div>
                <div className="text-[10px] text-slate-400">All Bureaus Oversight</div>
              </button>

              <button
                type="button"
                onClick={() =>
                  handleQuickFill("rb.official@aicte.gov.in", "Official@123")
                }
                className="p-2 rounded bg-slate-900/80 hover:bg-slate-700 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-blue-300">RB Official</div>
                <div className="text-[10px] text-slate-400">Bureau RB Case Worker</div>
              </button>

              <button
                type="button"
                onClick={() =>
                  handleQuickFill("pgrc.official@aicte.gov.in", "Official@123")
                }
                className="p-2 rounded bg-slate-900/80 hover:bg-slate-700 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-purple-300">PGRC Official</div>
                <div className="text-[10px] text-slate-400">Bureau PGRC Worker</div>
              </button>

              <button
                type="button"
                onClick={() =>
                  handleQuickFill("admin@aicte.gov.in", "Admin@123")
                }
                className="p-2 rounded bg-slate-900/80 hover:bg-slate-700 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-emerald-300">System Admin</div>
                <div className="text-[10px] text-slate-400">Full System &amp; Audit</div>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 text-center">
          <span className="text-xs text-slate-500">
            AICTE Prototype - Synthetic demonstration data only
          </span>
        </div>
      </div>
    </div>
  );
};
