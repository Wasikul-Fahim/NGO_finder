import api from "./client";

const unwrap = (r) => r.data;

export const getStats = () => api.get("/api/v1/admin/stats").then(unwrap);
export const listUsers = (params) => api.get("/api/v1/admin/users", { params }).then(unwrap);
export const updateUser = (id, body) => api.patch(`/api/v1/admin/users/${id}`, body).then(unwrap);
export const createNgoAdmin = (body) => api.post("/api/v1/admin/ngo-admins", body).then(unwrap);
export const listNgos = (params) => api.get("/api/v1/ngos", { params }).then(unwrap);
export const verifyNgo = (id, status, reason) => api.patch(`/api/v1/ngos/${id}/verify`, { status, reason: reason || null }).then(unwrap);
export const listAuditLogs = (params) => api.get("/api/v1/admin/audit-logs", { params }).then(unwrap);
export const auditActions = () => api.get("/api/v1/admin/audit-logs/actions").then(unwrap);
export const ngoDashboard = () => api.get("/api/v1/ngos/me/dashboard").then(unwrap);
export const ngoActivity = (params) => api.get("/api/v1/ngos/me/activity", { params }).then(unwrap);
export const deleteUser = (id) => api.delete(`/api/v1/admin/users/${id}`).then(unwrap);
