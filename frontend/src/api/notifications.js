import api from "./client";

const unwrap = (r) => r.data;

export const listNotifications = (params) => api.get("/api/v1/notifications", { params }).then(unwrap);
export const unreadCount = () => api.get("/api/v1/notifications/unread-count").then(unwrap);
export const markRead = (id) => api.patch(`/api/v1/notifications/${id}/read`).then(unwrap);
export const markAllRead = () => api.patch("/api/v1/notifications/read-all");
export const sendAnnouncement = (body) => api.post("/api/v1/announcements", body).then(unwrap);
export const sendEventReminder = (eventId) => api.post(`/api/v1/events/${eventId}/reminders`).then(unwrap);
export const getNotificationSettings = () => api.get("/api/v1/notifications/settings").then(unwrap);
export const saveNotificationSettings = (muted_types) => api.put("/api/v1/notifications/settings", { muted_types }).then(unwrap);
