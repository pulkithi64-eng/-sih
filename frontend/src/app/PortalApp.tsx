import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, homePathFor, useAuth } from "./auth";
import AppShell from "./layout/AppShell";
import LoginPage from "./pages/LoginPage";
import { PageSkeleton } from "./components/Skeletons";
import type { Role } from "@/lib/types";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const InstitutionsPage = lazy(() => import("./pages/InstitutionsPage"));
const ApplicationDetailPage = lazy(() => import("./pages/application/ApplicationDetailPage"));
const NewApplicationPage = lazy(() => import("./pages/wizard/NewApplicationPage"));
const RulesPage = lazy(() => import("./pages/RulesPage"));
const SourcesPage = lazy(() => import("./pages/SourcesPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <PageSkeleton />;
  if (!user) return <Navigate to="/portal/login" replace state={{ from: loc.pathname + loc.search }} />;
  return <>{children}</>;
}

function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) return <Navigate to={homePathFor(user?.role)} replace />;
  return <>{children}</>;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homePathFor(user.role) : "/portal/login"} replace />;
}

const OFFICER_PLUS: Role[] = ["SCRUTINY_OFFICER", "REGIONAL_DIRECTOR", "ADMIN"];

export default function PortalApp() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<Home />} />
          <Route
            path="dashboard"
            element={
              <RequireRole roles={OFFICER_PLUS}>
                <Lazy el={<DashboardPage />} />
              </RequireRole>
            }
          />
          <Route path="applications" element={<Lazy el={<ApplicationsPage />} />} />
          <Route path="institutions" element={<Lazy el={<InstitutionsPage />} />} />
          <Route
            path="my-applications"
            element={
              <RequireRole roles={["INSTITUTION"]}>
                <Lazy el={<ApplicationsPage mine />} />
              </RequireRole>
            }
          />
          <Route
            path="applications/new"
            element={
              <RequireRole roles={["INSTITUTION"]}>
                <Lazy el={<NewApplicationPage />} />
              </RequireRole>
            }
          />
          <Route
            path="applications/:id/edit"
            element={
              <RequireRole roles={["INSTITUTION"]}>
                <Lazy el={<NewApplicationPage />} />
              </RequireRole>
            }
          />
          <Route path="applications/:id" element={<Lazy el={<ApplicationDetailPage />} />} />
          <Route path="rules" element={<RequireRole roles={OFFICER_PLUS}><Lazy el={<RulesPage />} /></RequireRole>} />
          <Route path="sources" element={<RequireRole roles={OFFICER_PLUS}><Lazy el={<SourcesPage />} /></RequireRole>} />
          <Route path="alerts" element={<Lazy el={<AlertsPage />} />} />
          <Route path="audit" element={<RequireRole roles={OFFICER_PLUS}><Lazy el={<AuditPage />} /></RequireRole>} />
          <Route path="*" element={<Lazy el={<NotFoundPage />} />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

function Lazy({ el }: { el: React.ReactNode }) {
  return <Suspense fallback={<PageSkeleton />}>{el}</Suspense>;
}
