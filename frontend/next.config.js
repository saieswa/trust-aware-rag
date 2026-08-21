/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Traces the minimal set of files actually needed at runtime into
  // .next/standalone, including a self-contained server.js — this is
  // what lets the production Docker image ship without node_modules at
  // all (see deployment/docker/Dockerfile.frontend). Has no effect on
  // `npm run dev`.
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
