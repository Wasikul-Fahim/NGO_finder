import { Navigate, Outlet, useLocation } from "react-router-dom";

import { ROLE_HOME, useAuth } from "../context/AuthContext";

function FullScreenMessage({ children }) {
  return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm font-semibold text-slate-500">{children}</div>;
}

/** Requires a signed-in user; remembers where they were headed. */
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <FullScreenMessage>Loading…</FullScreenMessage>;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  return children ?? <Outlet />;
}

/** Requires one of the given roles; otherwise sends the user to their own home. */
export function RoleRoute({ roles, children }) {
  const { user } = useAuth();
  if (!roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role] || "/"} replace />;
  return children ?? <Outlet />;
}
