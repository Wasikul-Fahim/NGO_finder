import api from "./client";

const unwrap = (r) => r.data;

export const listCampaigns = (params) => api.get("/api/v1/campaigns", { params }).then(unwrap);
export const createCampaign = (body) => api.post("/api/v1/campaigns", body).then(unwrap);
export const updateCampaign = (id, body) => api.patch(`/api/v1/campaigns/${id}`, body).then(unwrap);
export const changeCampaignStatus = (id, status) => api.post(`/api/v1/campaigns/${id}/status`, { status }).then(unwrap);
export const archiveCampaign = (id) => api.delete(`/api/v1/campaigns/${id}`).then(unwrap);

export const listEvents = (params) => api.get("/api/v1/events", { params }).then(unwrap);
export const createEvent = (body) => api.post("/api/v1/events", body).then(unwrap);
export const updateEvent = (id, body) => api.patch(`/api/v1/events/${id}`, body).then(unwrap);
export const deleteEvent = (id) => api.delete(`/api/v1/events/${id}`);

export const getMyNgo = () => api.get("/api/v1/ngos/me").then(unwrap);
export const updateMyNgo = (body) => api.patch("/api/v1/ngos/me", body).then(unwrap);

export const uploadLogo = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/v1/ngos/me/logo", form, { headers: { "Content-Type": "multipart/form-data" } }).then(unwrap);
};
export const removeLogo = () => api.delete("/api/v1/ngos/me/logo").then(unwrap);

export const myEvents = (params) => api.get("/api/v1/events/me", { params }).then(unwrap);
export const joinEvent = (id) => api.post(`/api/v1/events/${id}/join`).then(unwrap);
export const leaveEvent = (id) => api.delete(`/api/v1/events/${id}/join`).then(unwrap);
export const eventRoster = (id) => api.get(`/api/v1/events/${id}/assignments`).then(unwrap);
export const assignVolunteer = (id, volunteer_id) => api.post(`/api/v1/events/${id}/assignments`, { volunteer_id }).then(unwrap);
export const removeFromRoster = (id, volunteer_id) => api.delete(`/api/v1/events/${id}/assignments/${volunteer_id}`).then(unwrap);
