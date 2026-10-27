import {
  Bell,
  Building2,
  FilePlus2,
  FileStack,
  LayoutDashboard,
  type LucideIcon,
  RadioTower,
  ScrollText,
  SlidersHorizontal,
} from "lucide-react";
import type { Role } from "@/lib/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles: Role[];
  badge?: "alerts";
}

const STAFF: Role[] = ["SCRUTINY_OFFICER", "REGIONAL_DIRECTOR", "ADMIN"];

export const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Scrutiny",
    items: [
      { to: "/portal/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: STAFF },
      { to: "/portal/applications", label: "Applications", icon: FileStack, roles: STAFF },
      { to: "/portal/institutions", label: "Institutions", icon: Building2, roles: [...STAFF, "INSTITUTION"] },
      { to: "/portal/my-applications", label: "My applications", icon: FileStack, roles: ["INSTITUTION"] },
      { to: "/portal/applications/new", label: "New application", icon: FilePlus2, roles: ["INSTITUTION"] },
      { to: "/portal/alerts", label: "Alerts", icon: Bell, roles: [...STAFF, "INSTITUTION"], badge: "alerts" },
    ],
  },
  {
    title: "Configuration",
    items: [
      { to: "/portal/rules", label: "Rules & checklists", icon: SlidersHorizontal, roles: STAFF },
      { to: "/portal/sources", label: "Verification sources", icon: RadioTower, roles: STAFF },
      { to: "/portal/audit", label: "Audit log", icon: ScrollText, roles: STAFF },
    ],
  },
];

export const CRUMB_LABEL: Record<string, string> = {
  dashboard: "Dashboard",
  applications: "Applications",
  institutions: "Institutions",
  "my-applications": "My applications",
  new: "New application",
  edit: "Edit",
  rules: "Rules & checklists",
  sources: "Verification sources",
  alerts: "Alerts",
  audit: "Audit log",
};
