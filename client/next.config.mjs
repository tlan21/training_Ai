/** @type {import('next').NextConfig} */
// Share the constrained workstation with the AI lane without four parallel build workers.
const nextConfig = {
  experimental: { cpus: 1 },
  async rewrites() {
    const gateway = (process.env.GATEWAY_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
    return [{ source: "/api/:path*", destination: `${gateway}/api/:path*` }];
  },
};

export default nextConfig;
