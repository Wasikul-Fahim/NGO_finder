import {
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
  { label: "Dashboard Overview", path: "/dashboard", icon: LayoutDashboard },
  { label: "Volunteer Opportunities", path: "/opportunities", icon: Compass },
  { label: "My Applications", path: "/applications", icon: CheckSquare, roles: ["VOLUNTEER"] },
  { label: "My Profile", path: "/profile", icon: Users, roles: ["VOLUNTEER"] },
  { label: "Active Campaigns", path: "/campaigns", icon: Megaphone },
  { label: "My Assigned Tasks", path: "/tasks", icon: ListTodo, roles: ["VOLUNTEER"] },
  { label: "My Donations", path: "/donations", icon: CircleDollarSign, roles: ["DONOR"] },
  { label: "My Support", path: "/support", icon: Users, roles: ["BENEFICIARY"] },
  { label: "My Impact", path: "/impact", icon: BarChart3, roles: ["VOLUNTEER"] },
  { label: "Notifications", path: "/notifications", icon: Megaphone },
];

export const adminNavigation = [
  { label: "NGO Overview", path: "/admin", icon: LayoutDashboard },
  { label: "Manage Campaigns", path: "/admin/campaigns", icon: Megaphone },
  { label: "Manage Events", path: "/admin/events", icon: CalendarDays },
  { label: "Opportunities", path: "/admin/opportunities", icon: Compass },
  { label: "Applications", path: "/admin/applications", icon: CheckSquare },
  { label: "Tasks", path: "/admin/tasks", icon: ListTodo },
  { label: "Attendance", path: "/admin/attendance", icon: CheckSquare },
  { label: "Donations", path: "/admin/donations", icon: CircleDollarSign },
  { label: "Resources", path: "/admin/resources", icon: Users },
  { label: "Reports", path: "/admin/reports", icon: BarChart3 },
  { label: "Announcements", path: "/admin/announcements", icon: Megaphone },
  { label: "Organisation Profile", path: "/admin/profile", icon: Users },
  { label: "Notifications", path: "/notifications", icon: Megaphone },
];

export const platformNavigation = [
  { label: "Platform Overview", path: "/platform", icon: LayoutDashboard },
  { label: "NGOs & Verification", path: "/platform/ngos", icon: HeartHandshake },
  { label: "Users", path: "/platform/users", icon: Users },
  { label: "Audit Log", path: "/platform/audit", icon: CheckSquare },
  { label: "Notifications", path: "/notifications", icon: Megaphone },
];

export const metrics = [
  {
    label: "Total Volunteer Hours",
    value: "36 hrs",
    delta: "+6 hrs this month",
    icon: HeartHandshake,
    tone: "purple",
  },
  {
    label: "Events Attended",
    value: "12",
    delta: "3 upcoming",
    icon: Users,
    tone: "amber",
  },
  {
    label: "Assigned Tasks",
    value: "4",
    delta: "2 due this week",
    icon: CheckSquare,
    tone: "blue",
  },
  {
    label: "Donations Contributed",
    value: "৳5,000",
    delta: "Across 4 campaigns",
    icon: CircleDollarSign,
    tone: "teal",
  },
];

export const opportunities = [
  {
    id: 1,
    match: 98,
    title: "Community Learning Facilitator",
    ngo: "Shobuj Foundation",
    location: "Dhaka · Mirpur",
    commitment: "4 hrs / week",
    skills: ["Bangla", "Teaching", "Youth Support"],
    description: "Help secondary students build confidence through weekly learning circles.",
  },
  {
    id: 2,
    match: 94,
    title: "Flood Relief Logistics Lead",
    ngo: "Relief Bridge Bangladesh",
    location: "Sylhet · On site",
    commitment: "8 hrs / week",
    skills: ["Logistics", "Coordination", "Bangla"],
    description: "Coordinate relief pack distribution for families affected by flooding.",
    urgent: true,
  },
  {
    id: 3,
    match: 91,
    title: "Digital Skills Mentor",
    ngo: "Nari Uddyog",
    location: "Online",
    commitment: "2 hrs / week",
    skills: ["Digital Literacy", "Mentoring", "English"],
    description: "Coach women entrepreneurs on essential digital tools and online safety.",
  },
  {
    id: 4,
    match: 87,
    title: "Community Nutrition Advocate",
    ngo: "Healthy Futures NGO",
    location: "Rangpur · Hybrid",
    commitment: "3 hrs / week",
    skills: ["Health", "Outreach", "Data Entry"],
    description: "Support neighborhood health sessions and collect simple impact stories.",
  },
];

export const tasks = [
  {
    id: 1,
    title: "Prepare school supply inventory",
    ngo: "Shobuj Foundation",
    status: "In Progress",
    progress: 68,
    due: "Today, 5:00 PM",
  },
  {
    id: 2,
    title: "Confirm Sylhet transport partners",
    ngo: "Relief Bridge Bangladesh",
    status: "Pending",
    progress: 25,
    due: "Tomorrow",
  },
  {
    id: 3,
    title: "Submit September impact notes",
    ngo: "Nari Uddyog",
    status: "Completed",
    progress: 100,
    due: "Sep 28, 2024",
  },
  {
    id: 4,
    title: "Review volunteer orientation deck",
    ngo: "Healthy Futures NGO",
    status: "Pending",
    progress: 0,
    due: "Oct 04, 2024",
  },
];

export const campaigns = [
  {
    id: 1,
    title: "Sylhet Flood Relief",
    ngo: "Relief Bridge Bangladesh",
    raised: 285000,
    goal: 400000,
    volunteers: 48,
    days: 6,
    urgent: true,
    color: "purple",
  },
  {
    id: 2,
    title: "Back to School 2024",
    ngo: "Shobuj Foundation",
    raised: 172500,
    goal: 250000,
    volunteers: 32,
    days: 18,
    color: "teal",
  },
  {
    id: 3,
    title: "Women Build Digital Futures",
    ngo: "Nari Uddyog",
    raised: 92000,
    goal: 150000,
    volunteers: 21,
    days: 24,
    color: "amber",
  },
];

export const donations = [
  { id: 1, campaign: "Sylhet Flood Relief", ngo: "Relief Bridge Bangladesh", amount: 2000, date: "Sep 26, 2024", channel: "bKash", status: "Completed" },
  { id: 2, campaign: "Back to School 2024", ngo: "Shobuj Foundation", amount: 1500, date: "Sep 14, 2024", channel: "Nagad", status: "Completed" },
  { id: 3, campaign: "Women Build Digital Futures", ngo: "Nari Uddyog", amount: 1000, date: "Aug 31, 2024", channel: "Card", status: "Completed" },
  { id: 4, campaign: "Clean Water for Kurigram", ngo: "Healthy Futures NGO", amount: 500, date: "Aug 12, 2024", channel: "bKash", status: "Completed" },
];

export const monthlyHours = [
  { month: "Apr", hours: 14 },
  { month: "May", hours: 22 },
  { month: "Jun", hours: 18 },
  { month: "Jul", hours: 28 },
  { month: "Aug", hours: 25 },
  { month: "Sep", hours: 36 },
];
