import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.quiwe.schooladminaiassistant",
  appName: "高校行政AI回复助手",
  webDir: "dist",
  server: {
    androidScheme: "https"
  },
  android: {
    // 配置Android应用图标
    backgroundColor: "#3B82F6",
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: false
  }
};

export default config;
