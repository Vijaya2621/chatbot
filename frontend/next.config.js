/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    REACT_APP_API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://a904c4b23415.ngrok-free.app',
  },
}

module.exports = nextConfig