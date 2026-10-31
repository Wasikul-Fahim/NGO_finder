import api from "./client";

const unwrap = (r) => r.data;

export const myContributions = () => api.get("/api/v1/contributions/me").then(unwrap);
export const recordAttendance = (body) => api.post("/api/v1/participation", body).then(unwrap);
export const updateAttendance = (id, body) => api.patch(`/api/v1/participation/${id}`, body).then(unwrap);
export const listParticipation = (params) => api.get("/api/v1/participation", { params }).then(unwrap);
export const volunteerPerformance = (params) => api.get("/api/v1/reports/volunteer-performance", { params }).then(unwrap);
export const donationSummary = (params) => api.get("/api/v1/reports/donation-summary", { params }).then(unwrap);

export const makeDonation = (body) => api.post("/api/v1/donations", body).then(unwrap);
export const myDonations = (params) => api.get("/api/v1/donations/me", { params }).then(unwrap);
export const ngoDonations = (params) => api.get("/api/v1/donations", { params }).then(unwrap);
export const setDonationStatus = (id, status) => api.patch(`/api/v1/donations/${id}/status`, { status }).then(unwrap);
export const getUtilization = (campaignId) => api.get(`/api/v1/campaigns/${campaignId}/utilization`).then(unwrap);

export const listResources = (cid) => api.get(`/api/v1/campaigns/${cid}/resources`).then(unwrap);
export const addResource = (cid, body) => api.post(`/api/v1/campaigns/${cid}/resources`, body).then(unwrap);
export const distribute = (rid, body) => api.post(`/api/v1/resources/${rid}/distributions`, body).then(unwrap);
export const listBeneficiaries = (cid) => api.get(`/api/v1/campaigns/${cid}/beneficiaries`).then(unwrap);
export const enrollBeneficiary = (cid, body) => api.post(`/api/v1/campaigns/${cid}/beneficiaries`, body).then(unwrap);
export const setSupportStatus = (cid, bid, support_status) => api.patch(`/api/v1/campaigns/${cid}/beneficiaries/${bid}`, { support_status }).then(unwrap);
export const mySupport = () => api.get("/api/v1/support/me").then(unwrap);

export const campaignReport = (params) => api.get("/api/v1/reports/campaigns", { params }).then(unwrap);
export const resourceUtilization = (params) => api.get("/api/v1/reports/resource-utilization", { params }).then(unwrap);
export const deleteResource = (id) => api.delete(`/api/v1/resources/${id}`).then(unwrap);
export const updateDonation = (id, body) => api.patch(`/api/v1/donations/${id}`, body).then(unwrap);
