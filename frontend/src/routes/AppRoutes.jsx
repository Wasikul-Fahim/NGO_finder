import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "../components/AppShell";
import { ROLE_HOME, useAuth } from "../context/AuthContext";
import AdminOverview from "../pages/admin/AdminOverview";
import ManageCampaigns from "../pages/admin/ManageCampaigns";
import ManageEvents from "../pages/admin/ManageEvents";
import Campaigns from "../pages/Campaigns";
import Dashboard from "../pages/Dashboard";
import Donations from "../pages/Donations";
import Impact from "../pages/Impact";
import Landing from "../pages/Landing";
import Login from "../pages/Login";
import Opportunities from "../pages/Opportunities";
import Register from "../pages/Register";
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
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/donations" element={<Donations />} />
        <Route path="/impact" element={<Impact />} />
        <Route element={<RoleRoute roles={["NGO_ADMIN"]} />}>
          <Route path="/admin" element={<AdminOverview />} />
          <Route path="/admin/campaigns" element={<ManageCampaigns />} />
          <Route path="/admin/events" element={<ManageEvents />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
