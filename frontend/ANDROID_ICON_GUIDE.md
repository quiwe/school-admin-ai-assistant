# Android 应用图标设置指南

## 问题描述
安卓版本图标显示不完整，通常是因为自适应图标（Adaptive Icon）配置不正确。

## 解决方案

### 1. 已修复的问题
- ✅ 创建了正确的自适应图标配置
- ✅ 生成了所有密度的mipmap图标（mdpi, hdpi, xhdpi, xxhdpi, xxxhdpi）
- ✅ 创建了圆形图标变体（ic_launcher_round.png）
- ✅ 修复了向量图标路径引用
- ✅ 确保图标内容在安全区域内显示

### 2. 图标文件结构
```
android/app/src/main/res/
├── drawable/
│   └── ic_launcher_foreground.xml    # 向量图标前景
├── mipmap-anydpi-v26/
│   ├── ic_launcher.xml              # Android 8.0+ 自适应图标
│   └── ic_launcher_round.xml        # 圆形图标变体
├── mipmap-mdpi/
│   ├── ic_launcher.png              # 48x48
│   └── ic_launcher_round.png        # 48x48
├── mipmap-hdpi/
│   ├── ic_launcher.png              # 72x72
│   └── ic_launcher_round.png        # 72x72
├── mipmap-xhdpi/
│   ├── ic_launcher.png              # 96x96
│   └── ic_launcher_round.png        # 96x96
├── mipmap-xxhdpi/
│   ├── ic_launcher.png              # 144x144
│   └── ic_launcher_round.png        # 144x144
├── mipmap-xxxhdpi/
│   ├── ic_launcher.png              # 192x192
│   └── ic_launcher_round.png        # 192x192
└── values/
    └── colors.xml                   # 图标背景颜色
```

### 3. 重新生成图标
如果需要重新生成图标，可以使用提供的Python脚本：

```bash
cd frontend
python3 generate_icons.py          # 生成标准图标
python3 generate_round_icons.py    # 生成圆形图标
```

### 4. 同步和测试
```bash
# 同步Android项目
npm run android:sync

# 在Android Studio中打开项目
npx cap open android

# 构建并运行应用
# 在Android Studio中点击运行按钮
```

### 5. 自定义图标
要自定义图标，请修改以下文件：

1. **向量图标**：`android/app/src/main/res/drawable/ic_launcher_foreground.xml`
   - 修改路径数据和颜色
   - 确保内容在安全区域内（距离边缘至少18dp）

2. **背景颜色**：`android/app/src/main/res/values/colors.xml`
   - 修改 `ic_launcher_background` 颜色值

3. **PNG图标**：重新运行图标生成脚本或使用图像编辑软件

### 6. 常见问题
**Q: 图标显示不完整？**
A: 确保向量图标的内容在安全区域内。Android自适应图标有36dp的圆角遮罩，内容需要在中心66x66dp的区域内。

**Q: 图标在不同设备上显示不一致？**
A: 确保所有密度的mipmap图标都已生成，并且尺寸正确。

**Q: 如何测试图标显示效果？**
A: 在Android Studio中运行应用，或使用 `adb install` 安装APK后查看应用图标。

### 7. 验证工具
运行图标检查脚本验证配置：
```bash
python3 test_icon_display.py
```

## 注意事项
- Android 8.0+ 使用自适应图标，会自动裁剪图标形状
- 不同设备可能显示不同形状（圆形、方形、圆角方形等）
- 确保图标在所有形状下都清晰可辨
- 测试时请在不同Android版本和设备上验证