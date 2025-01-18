export const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "https://api.wondy.io"
    : "http://localhost:3000";
