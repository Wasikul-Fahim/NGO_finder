import api from "./client";

const unwrap = (r) => r.data;

export const getMyProfile = () => api.get("/api/v1/volunteers/me").then(unwrap);
export const updateMyProfile = (body) => api.patch("/api/v1/volunteers/me", body).then(unwrap);

export const listOpportunities = (params) => api.get("/api/v1/opportunities", { params }).then(unwrap);
export const getRecommended = (limit = 10) => api.get("/api/v1/opportunities/recommended", { params: { limit } }).then(unwrap);
export const createOpportunity = (body) => api.post("/api/v1/opportunities", body).then(unwrap);
export const updateOpportunity = (id, body) => api.patch(`/api/v1/opportunities/${id}`, body).then(unwrap);
export const deactivateOpportunity = (id) => api.delete(`/api/v1/opportunities/${id}`).then(unwrap);

export const applyTo = (id) => api.post(`/api/v1/opportunities/${id}/applications`).then(unwrap);
export const myApplications = (params) => api.get("/api/v1/applications/me", { params }).then(unwrap);
export const reviewQueue = (params) => api.get("/api/v1/applications", { params }).then(unwrap);
export const messageApplicant = (id, message) => api.post(`/api/v1/applications/${id}/messages`, { message }).then(unwrap);
export const reviewApplication = (id, status, note) => api.patch(`/api/v1/applications/${id}/review`, { status, note: note || null }).then(unwrap);

export const myTasks = (params) => api.get("/api/v1/tasks/me", { params }).then(unwrap);
export const listTasks = (params) => api.get("/api/v1/tasks", { params }).then(unwrap);
export const createTask = (body) => api.post("/api/v1/tasks", body).then(unwrap);
export const assignTask = (id, volunteer_id) => api.post(`/api/v1/tasks/${id}/assign`, { volunteer_id }).then(unwrap);
export const setTaskStatus = (id, status) => api.patch(`/api/v1/tasks/${id}/status`, { status }).then(unwrap);
