import type { NextConfig } from "next";

const rawBackend = process.env.BACKEND_URL || "";
const backendUrl = rawBackend.startsWith("http") ? rawBackend : "http://127.0.0.1:8000";


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
