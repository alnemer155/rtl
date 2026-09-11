import type { NextConfig } from "next";
import path from "path";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // مثبّت جذر مسار العمل حتى لا يتأثر بمجلدات أب تحتوي package-lock.json
  outputFileTracingRoot: path.join(import.meta.dirname),
  async rewrites() {
    // وكيل للـAPI خلال تطوير الواجهة — الإنتاج يستخدم NEXT_PUBLIC_API_URL مباشرة
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
