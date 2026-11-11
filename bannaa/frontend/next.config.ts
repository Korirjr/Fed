import type { NextConfig } from "next";

// The browser only talks to Next.js; /api/* is forwarded to the Axum backend.
const API_URL = process.env.API_URL ?? "http://localhost:8080";

const nextConfig: NextConfig = {
  // Keep streamed responses (agent events, logs) unbuffered.
  compress: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
