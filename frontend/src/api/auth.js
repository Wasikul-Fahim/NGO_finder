import api, { refreshSession } from "./client";

export const register = (payload) => api.post("/api/v1/auth/register", payload).then((r) => r.data);
export const registerNgo = (payload) => api.post("/api/v1/auth/register-ngo", payload).then((r) => r.data);
export const login = (payload) => api.post("/api/v1/auth/login", payload).then((r) => r.data);
export const logout = () => api.post("/api/v1/auth/logout");
export const restoreSession = () => refreshSession();
export const changePassword = (payload) => api.post("/api/v1/auth/change-password", payload);
export const updateProfile = (payload) => api.patch("/api/v1/auth/me", payload).then((r) => r.data);
