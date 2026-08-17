import type { NextConfig } from "next";

const envBackend = process.env.BACKEND_URL ?? "";
// Guard: if the env var contains a non-http value (e.g. Render passing key-as-value), use safe fallback
const backendUrl = envBackend.startsWith("http")
  ? envBackend
  : process.env.NODE_ENV === "production"
  ? "https://whitfield-api.onrender.com"
  : "http://127.0.0.1:8000";


const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
