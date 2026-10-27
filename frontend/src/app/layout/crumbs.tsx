import { createContext, useContext, useEffect, useState } from "react";

/** Lets a page supply a human label for the dynamic last breadcrumb segment (e.g. an application number). */
const CrumbCtx = createContext<{ label: string | null; setLabel: (s: string | null) => void }>({
  label: null,
  setLabel: () => {},
});

export function CrumbProvider({ children }: { children: React.ReactNode }) {
  const [label, setLabel] = useState<string | null>(null);
  return <CrumbCtx.Provider value={{ label, setLabel }}>{children}</CrumbCtx.Provider>;
}

export function useCrumbLabel() {
  return useContext(CrumbCtx).label;
}

export function useSetCrumb(label: string | null | undefined) {
  const { setLabel } = useContext(CrumbCtx);
  useEffect(() => {
    setLabel(label ?? null);
    return () => setLabel(null);
  }, [label, setLabel]);
}
