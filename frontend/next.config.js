/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a self-contained server bundle for a lean Docker image.
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_INTERNAL_URL || "http://api:8000"}/:path*` }];
  },
};

module.exports = nextConfig;
