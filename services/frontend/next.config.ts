import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',

  // Images
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.anansi.ai',
      },
      {
        protocol: 'https',
        hostname: '*.r2.cloudflarestorage.com',
      },
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
      },
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://*.sentry.io https://js.stripe.com",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' blob: data: https://*.r2.cloudflarestorage.com https://avatars.githubusercontent.com https://lh3.googleusercontent.com",
              "font-src 'self' data:",
              "connect-src 'self' ws: wss: https://api.anansi.ai https://o*.ingest.sentry.io https://api.stripe.com",
              "frame-src https://js.stripe.com",
              "media-src 'self' blob:",
            ].join('; '),
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
          },
        ],
      },
    ];
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/app',
        destination: '/app/dashboard',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
