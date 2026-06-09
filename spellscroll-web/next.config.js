/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // Cerberus API key will be made accessible server-side
    CERBERUS_API_KEY: process.env.CERBERUS_API_KEY || "csk-ewm9m3r8mkwwwn2d4kkp8r4wtp8kt66x4hxfp92ec9tyw4rw"
  }
};

module.exports = nextConfig;
