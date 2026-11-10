/** @type {import('next').NextConfig} */
const nextConfig = {
  // SSE streams must not be buffered by response compression.
  compress: false,
  // The backend runs on :8000; proxy API + SSE through Next.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:8000/:path*" },
    ];
  },
};

module.exports = nextConfig;
