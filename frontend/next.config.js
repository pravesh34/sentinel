/** @type {import('next').NextConfig} */
module.exports = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/:path*" }];
  }
};
