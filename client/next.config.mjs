/** @type {import('next').NextConfig} */
// Share the constrained workstation with the AI lane without four parallel build workers.
const nextConfig = { experimental: { cpus: 1 } };

export default nextConfig;
