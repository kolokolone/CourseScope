import type { NextConfig } from "next";

const devOrigins: string[] = [
  "http://127.0.0.1:3000",
  "http://localhost:3000",
  process.env.COURSESCOPE_DEV_ORIGIN,
].filter(Boolean) as string[];

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: devOrigins,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // Use 127.0.0.1 to avoid localhost IPv6 edge cases on Windows.
        destination: 'http://127.0.0.1:8000/:path*',
      },
    ]
  },
};

export default nextConfig;
