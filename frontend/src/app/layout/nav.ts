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
const REVIEWERS: Role[] = ["SCRUTINY_OFFICER", "REGIONAL_DIRECTOR"];

export const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Workspace",
    items: [
      { to: "/portal/my-applications", label: "My applications", icon: FileStack, roles: ["INSTITUTION"] },
      { to: "/portal/applications", label: "Review queue", icon: FileStack, roles: ["SCRUTINY_OFFICER"] },
      { to: "/portal/applications?status=RECOMMENDED", label: "Decision queue", icon: FileStack, roles: ["REGIONAL_DIRECTOR"] },
      { to: "/portal/alerts", label: "Alerts", icon: Bell, roles: [...STAFF, "INSTITUTION"], badge: "alerts" },
      { to: "/portal/institutions", label: "My institution", icon: Building2, roles: ["INSTITUTION"] },
    ],
  },
  {
    title: "Administration",
    items: [
      { to: "/portal/rules", label: "Rules & checklists", icon: SlidersHorizontal, roles: ["ADMIN"] },
      { to: "/portal/sources", label: "Verification sources", icon: RadioTower, roles: ["ADMIN"] },
      { to: "/portal/institutions", label: "Institutions", icon: Building2, roles: ["ADMIN"] },
      { to: "/portal/audit", label: "Audit log", icon: ScrollText, roles: ["ADMIN"] },
      { to: "/portal/applications", label: "Applications", icon: FileStack, roles: ["ADMIN"] },
    ],
  },
  {
    title: "Reference",
    items: [
      { to: "/portal/dashboard", label: "Overview", icon: LayoutDashboard, roles: STAFF },
      { to: "/portal/institutions", label: "Institutions", icon: Building2, roles: REVIEWERS },
      { to: "/portal/rules", label: "Rules & checklists", icon: SlidersHorizontal, roles: REVIEWERS },
      { to: "/portal/sources", label: "Verification sources", icon: RadioTower, roles: REVIEWERS },
      { to: "/portal/audit", label: "Audit log", icon: ScrollText, roles: REVIEWERS },
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
