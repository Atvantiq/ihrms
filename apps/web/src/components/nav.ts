export interface NavItem {
  label: string;
  href: string;
  icon: string;
  hrOnly?: boolean;
  comingSoon?: boolean;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

/** Sidebar model — mirrors the prototype's grouping. Built screens link;
 *  not-yet-built modules are shown dimmed so the product reads as complete. */
export const NAV: NavSection[] = [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: "▦", comingSoon: true },
    ],
  },
  {
    label: "People",
    items: [
      { label: "Directory", href: "/directory", icon: "⛁" },
      { label: "Org masters", href: "/settings/org", icon: "◈", hrOnly: true },
    ],
  },
  {
    label: "Time",
    items: [
      { label: "Leave", href: "/leave", icon: "◰" },
      { label: "Holidays", href: "/settings/holidays", icon: "▤" },
      { label: "Attendance", href: "/attendance", icon: "⏱", comingSoon: true },
      { label: "Timesheet", href: "/timesheet", icon: "⊞", comingSoon: true },
    ],
  },
  {
    label: "Money",
    items: [
      { label: "Payroll", href: "/payroll", icon: "₹", comingSoon: true, hrOnly: true },
    ],
  },
  {
    label: "Admin",
    items: [
      { label: "Audit log", href: "/settings/audit", icon: "❒", hrOnly: true },
    ],
  },
];
