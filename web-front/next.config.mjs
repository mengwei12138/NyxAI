/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        // 代理后端静态缓存文件：图片 + TTS 音频
        source: '/cache/:path*',
        destination: `${BACKEND_URL}/cache/:path*`,
      },
    ]
  },
}

export default nextConfig
