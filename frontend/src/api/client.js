import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Access token lives in memory only; the refresh token is an HTTP-only cookie.
let accessToken = null;
let onAuthLost = () => {};

export const setAccessToken = (token) => { accessToken = token; };
export const getAccessToken = () => accessToken;
export const apiBaseUrl = baseURL;
export const setAuthLostHandler = (fn) => { onAuthLost = fn; };

const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Separate instance so refresh calls never trigger the retry interceptor.
const bare = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

let refreshing = null;
export function refreshSession() {
  if (!refreshing) {
    refreshing = bare
      .post("/api/v1/auth/refresh")
      .then((res) => res.data)
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes("/auth/");
    if (status === 401 && original && !original._retried && !isAuthCall && accessToken) {
      original._retried = true; // retry at most once: no refresh loops
      try {
        const data = await refreshSession();
        accessToken = data.access_token;
        original.headers.Authorization = `Bearer ${accessToken}`;
        return api(original);
      } catch {
        accessToken = null;
        onAuthLost();
      }
    }
    return Promise.reject(error);
  },
);

/** Normalise the backend error envelope into { message, fields }. */
export function parseError(error) {
  const body = error.response?.data?.error;
  if (body) return { message: body.message, fields: body.fields || {}, status: error.response.status };
  if (error.response) return { message: "Something went wrong.", fields: {}, status: error.response.status };
  return { message: "Cannot reach the server. Check your connection and try again.", fields: {}, status: 0 };
}

export default api;
