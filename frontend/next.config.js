/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/twilio/:path*',
        destination: 'http://localhost:8000/twilio/:path*',
      },
      {
        source: '/billing/:path*',
        destination: 'http://localhost:8000/billing/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
