import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "../components/AppShell";
import { ROLE_HOME, useAuth } from "../context/AuthContext";
import Attendance from "../pages/admin/Attendance";
import IncomingDonations from "../pages/admin/IncomingDonations";
import Reports from "../pages/admin/Reports";
import ResourcesBeneficiaries from "../pages/admin/ResourcesBeneficiaries";
import AdminOverview from "../pages/admin/AdminOverview";
import ManageOpportunities from "../pages/admin/ManageOpportunities";
import ManageTasks from "../pages/admin/ManageTasks";
import ReviewApplications from "../pages/admin/ReviewApplications";
import ManageCampaigns from "../pages/admin/ManageCampaigns";
import ManageEvents from "../pages/admin/ManageEvents";
import Applications from "../pages/Applications";
import Campaigns from "../pages/Campaigns";
import Dashboard from "../pages/Dashboard";
import Donations from "../pages/Donations";
import Impact from "../pages/Impact";
import Landing from "../pages/Landing";
import Login from "../pages/Login";
import Opportunities from "../pages/Opportunities";
import Profile from "../pages/Profile";
import Register from "../pages/Register";
import Support from "../pages/Support";
import Tasks from "../pages/Tasks";
import ProtectedRoute, { RoleRoute } from "./ProtectedRoute";

/** Landing page for visitors; signed-in users go straight to their home. */
function Home() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  return user ? <Navigate to={ROLE_HOME[user.role] || "/dashboard"} replace /> : <Landing />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/opportunities" element={<Opportunities />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route element={<RoleRoute roles={["VOLUNTEER"]} />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/impact" element={<Impact />} />
        </Route>
        <Route element={<RoleRoute roles={["DONOR"]} />}>
          <Route path="/donations" element={<Donations />} />
        </Route>
        <Route element={<RoleRoute roles={["BENEFICIARY"]} />}>
          <Route path="/support" element={<Support />} />
        </Route>
        <Route element={<RoleRoute roles={["NGO_ADMIN"]} />}>
          <Route path="/admin" element={<AdminOverview />} />
          <Route path="/admin/campaigns" element={<ManageCampaigns />} />
          <Route path="/admin/events" element={<ManageEvents />} />
          <Route path="/admin/opportunities" element={<ManageOpportunities />} />
          <Route path="/admin/applications" element={<ReviewApplications />} />
          <Route path="/admin/tasks" element={<ManageTasks />} />
          <Route path="/admin/attendance" element={<Attendance />} />
          <Route path="/admin/donations" element={<IncomingDonations />} />
          <Route path="/admin/resources" element={<ResourcesBeneficiaries />} />
          <Route path="/admin/reports" element={<Reports />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
