import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // مثبّت جذر مسار العمل حتى لا يتأثر بمجلدات أب تحتوي package-lock.json
  outputFileTracingRoot: path.join(import.meta.dirname),
};

export default nextConfig;
