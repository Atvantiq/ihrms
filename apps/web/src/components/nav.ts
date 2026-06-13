export interface NavItem {
  label: string;
  href: string;
  icon: string;
  hrOnly?: boolean;
  superOnly?: boolean;
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
      { label: "Dashboard", href: "/dashboard", icon: "▦" },
      { label: "Tasks", href: "/tasks", icon: "⊟" },
      { label: "Reports", href: "/reports", icon: "▤", hrOnly: true },
    ],
  },
  {
    label: "People",
    items: [
      { label: "Directory", href: "/directory", icon: "⛁" },
      { label: "Recruitment", href: "/recruitment", icon: "◎", hrOnly: true },
      { label: "Performance", href: "/performance", icon: "★" },
      { label: "Org masters", href: "/settings/org", icon: "◈", hrOnly: true },
    ],
  },
  {
    label: "Time",
    items: [
      { label: "Leave", href: "/leave", icon: "◰" },
      { label: "Holidays", href: "/settings/holidays", icon: "▤" },
      { label: "Attendance", href: "/attendance", icon: "⏱" },
      { label: "Timesheet", href: "/timesheet", icon: "⊞" },
    ],
  },
  {
    label: "Money",
    items: [
      { label: "Payroll", href: "/payroll", icon: "₹", hrOnly: true },
    ],
  },
  {
    label: "Lifecycle",
    items: [
      { label: "Exit & F&F", href: "/exit", icon: "↗", hrOnly: true },
    ],
  },
  {
    label: "Admin",
    items: [
      { label: "Audit log", href: "/settings/audit", icon: "❒", hrOnly: true },
    ],
  },
  {
    label: "Control Plane",
    items: [
      { label: "Tenants & Billing", href: "/control-plane", icon: "⬡", superOnly: true },
    ],
  },
];
