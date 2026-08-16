import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { captureAdminKeyFromLocation } from "./api/client";
import "./styles.css";

// 捕获 URL 中的 admin_key（局域网网页端管理员登录），在任何 API 请求前持久化。
captureAdminKeyFromLocation();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
