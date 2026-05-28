import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.quiwe.schooladminaiassistant",
  appName: "高校行政AI回复助手",
  webDir: "dist",
  server: {
    androidScheme: "https"
  }
};

export default config;
