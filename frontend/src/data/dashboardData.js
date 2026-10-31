import {
  Bell,
  BarChart3,
  CheckSquare,
  CircleDollarSign,
  Compass,
  HeartHandshake,
  LayoutDashboard,
  ListTodo,
  CalendarDays,
  Megaphone,
  Users,
} from "lucide-react";

export const navigation = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, roles: ["VOLUNTEER"] },
  { label: "Opportunities", path: "/opportunities", icon: Compass, roles: ["VOLUNTEER"] },
  { label: "My Applications", path: "/applications", icon: CheckSquare, roles: ["VOLUNTEER"] },
  { label: "My Tasks", path: "/tasks", icon: ListTodo, roles: ["VOLUNTEER"] },
  { label: "Events", path: "/events", icon: CalendarDays, roles: ["VOLUNTEER"] },
  { label: "Campaigns", path: "/campaigns", icon: Megaphone },
  { label: "My Donations", path: "/donations", icon: CircleDollarSign, roles: ["DONOR"] },
  { label: "My Support", path: "/support", icon: Users, roles: ["BENEFICIARY"] },
  { label: "My Impact", path: "/impact", icon: BarChart3, roles: ["VOLUNTEER"] },
  { label: "My Profile", path: "/profile", icon: Users, roles: ["VOLUNTEER"] },
  { label: "Notifications", path: "/notifications", icon: Bell },
];

export const adminNavigation = [
  { label: "NGO Overview", path: "/admin", icon: LayoutDashboard },
  { label: "Campaigns", path: "/admin/campaigns", icon: Megaphone },
  { label: "Events", path: "/admin/events", icon: CalendarDays },
  { label: "Opportunities", path: "/admin/opportunities", icon: Compass },
  { label: "Applications", path: "/admin/applications", icon: CheckSquare },
  { label: "Tasks", path: "/admin/tasks", icon: ListTodo },
  { label: "Attendance", path: "/admin/attendance", icon: CheckSquare },
  { label: "Donations", path: "/admin/donations", icon: CircleDollarSign },
  { label: "Resources", path: "/admin/resources", icon: Users },
  { label: "Reports", path: "/admin/reports", icon: BarChart3 },
  { label: "Announcements", path: "/admin/announcements", icon: Megaphone },
  { label: "Organisation Profile", path: "/admin/profile", icon: HeartHandshake },
  { label: "Notifications", path: "/notifications", icon: Bell },
];

export const platformNavigation = [
  { label: "Platform Overview", path: "/platform", icon: LayoutDashboard },
  { label: "NGOs & Verification", path: "/platform/ngos", icon: HeartHandshake },
  { label: "Users", path: "/platform/users", icon: Users },
  { label: "Reports", path: "/platform/reports", icon: BarChart3 },
  { label: "Audit Log", path: "/platform/audit", icon: CheckSquare },
  { label: "Notifications", path: "/notifications", icon: Bell },
];
