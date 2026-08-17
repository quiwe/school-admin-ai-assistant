# 高校行政AI回复助手 - 前端

这是一个基于React和Capacitor的跨平台应用，支持Web和Android平台。

## 功能特性
- AI驱动的行政回复助手
- 支持多种AI模型（OpenAI、MiniMax等）
- 简洁直观的用户界面
- 支持PDF文档解析
- 跨平台支持（Web + Android）

## 开发环境设置

### 1. 安装依赖
```bash
npm install
```

### 2. 开发模式
```bash
# 启动Web开发服务器
npm run dev

# 在浏览器中打开 http://localhost:5173
```

### 3. Android开发
```bash
# 同步Web资源到Android项目
npm run android:sync

# 在Android Studio中打开项目
npx cap open android
```

### 4. 构建和部署
```bash
# 构建Web版本
npm run build

# 构建Android版本
npm run build
npm run android:sync
# 在Android Studio中构建APK
```

## 项目结构
```
frontend/
├── src/                    # React源代码
├── public/                 # 静态资源
├── android/                # Android项目
├── dist/                   # 构建输出
├── tools/                  # 开发工具
│   ├── generate_icons.py   # 图标生成工具
│   └── test_icon_display.py # 图标测试工具
├── package.json            # 项目配置
├── capacitor.config.ts     # Capacitor配置
└── vite.config.ts          # Vite配置
```

## Android应用图标

### 问题修复
已修复安卓版本图标显示不完整的问题：
- ✅ 创建了正确的自适应图标配置
- ✅ 生成了所有密度的mipmap图标
- ✅ 确保图标内容在安全区域内显示

### 图标自定义
1. 修改向量图标：`android/app/src/main/res/drawable/ic_launcher_foreground.xml`
2. 修改背景颜色：`android/app/src/main/res/values/colors.xml`
3. 重新生成图标：`python3 tools/generate_icons.py`

### 验证图标
```bash
python3 tools/test_icon_display.py
```

详细说明请参考：[ANDROID_ICON_GUIDE.md](./ANDROID_ICON_GUIDE.md)

## 常见问题

### Q: 如何添加新的AI模型？
A: 在 `src/config/models.ts` 中添加新的模型配置。

### Q: 如何修改应用主题？
A: 修改 `src/styles/` 目录下的CSS文件。

### Q: Android构建失败？
A: 确保已安装Android SDK，并检查 `android/local.properties` 文件。

## 技术栈
- **前端框架**: React 19
- **构建工具**: Vite
- **跨平台**: Capacitor
- **样式**: Tailwind CSS
- **状态管理**: React Context
- **HTTP客户端**: Capacitor HTTP

## 贡献指南
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证
MIT License