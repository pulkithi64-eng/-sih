import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, session, UNAUTHORIZED_EVENT } from "@/lib/api";
import type { Role, User } from "@/lib/types";

interface AuthCtx {
  user: User | null;
  ready: boolean;
  maskPii: boolean;
  toggleMaskPii: () => void;
  sessionExpiring: boolean;
  remainingMinutes: number;
  extendSession: () => Promise<void>;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

const MASK_PII_KEY = "verisense.privacy.maskPii";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const [user, setUser] = useState<User | null>(() => (session.getToken() ? session.getUser() : null));
  const [ready, setReady] = useState(false);
  const [sessionExpiring, setSessionExpiring] = useState(false);
  const [remainingMinutes, setRemainingMinutes] = useState(480);
  const [maskPii, setMaskPii] = useState<boolean>(() => {
    try {
      return localStorage.getItem(MASK_PII_KEY) !== "0";
    } catch {
      return true;
    }
  });

  const toggleMaskPii = useCallback(() => {
    setMaskPii((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(MASK_PII_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  // Revalidate stored session on mount
  useEffect(() => {
    if (!session.getToken()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then((u) => {
        session.setUser(u);
        setUser(u);
      })
      .catch((e) => {
        if (e?.status === 401 || e?.status === 403) {
          session.clear();
          setUser(null);
        }
      })
      .finally(() => setReady(true));
  }, []);

  // Periodically check session validity & remaining lifetime
  useEffect(() => {
    if (!user) {
      setSessionExpiring(false);
      return;
    }

    const checkSession = async () => {
      try {
        const st = await api.sessionStatus();
        const mins = Math.max(0, Math.floor(st.remainingSeconds / 60));
        setRemainingMinutes(mins);
        // Warn if less than 15 minutes remaining
        if (mins <= 15 && mins > 0) {
          setSessionExpiring(true);
        } else if (mins <= 0) {
          toast.error("Session expired", { description: "Please log in again to continue." });
          session.clear();
          setUser(null);
        } else {
          setSessionExpiring(false);
        }
      } catch {
        /* ignore transient check errors */
      }
    };

    checkSession();
    const interval = setInterval(checkSession, 60_000);
    return () => clearInterval(interval);
  }, [user]);

  useEffect(() => {
    const onUnauth = () => {
      setUser(null);
      qc.clear();
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauth);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauth);
  }, [qc]);

  const extendSession = useCallback(async () => {
    try {
      const res = await api.refreshSession();
      session.set(res.accessToken, res.user);
      setSessionExpiring(false);
      setRemainingMinutes(480);
      toast.success("Session renewed successfully");
    } catch (e) {
      toast.error("Could not extend session", { description: "Please re-login." });
    }
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await api.login(username, password);
      session.set(res.accessToken, res.user);
      qc.clear();
      setUser(res.user);
      setSessionExpiring(false);
      setRemainingMinutes(480);
      return res.user;
    },
    [qc],
  );

  const logout = useCallback(() => {
    session.clear();
    qc.clear();
    setUser(null);
    setSessionExpiring(false);
  }, [qc]);

  const value = useMemo(
    () => ({
      user,
      ready,
      maskPii,
      toggleMaskPii,
      sessionExpiring,
      remainingMinutes,
      extendSession,
      login,
      logout,
    }),
    [user, ready, maskPii, toggleMaskPii, sessionExpiring, remainingMinutes, extendSession, login, logout],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}

export const isOfficerPlus = (r?: Role) => r === "SCRUTINY_OFFICER" || r === "REGIONAL_DIRECTOR" || r === "ADMIN";
export const isReviewer = (r?: Role) => r === "SCRUTINY_OFFICER" || r === "REGIONAL_DIRECTOR";
export const canDecide = (r?: Role) => r === "REGIONAL_DIRECTOR";
export const isAdmin = (r?: Role) => r === "ADMIN";
export const isInstitution = (r?: Role) => r === "INSTITUTION";

export function homePathFor(role?: Role) {
  if (role === "INSTITUTION") return "/portal/my-applications";
  return "/portal/dashboard";
}
