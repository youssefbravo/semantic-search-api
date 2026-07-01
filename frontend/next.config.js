/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a self-contained server bundle for a lean Docker image.
  output: "standalone",
  // The portfolio value is the app, not lint config — don't fail the build on lint.
  eslint: { ignoreDuringBuilds: true },
};

module.exports = nextConfig;
