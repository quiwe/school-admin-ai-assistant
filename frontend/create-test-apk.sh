#!/bin/bash
# 创建测试APK脚本
# 这个脚本创建一个模拟的APK文件用于测试

set -e

echo "📱 创建测试APK..."

# 创建输出目录
mkdir -p build/outputs/apk/debug
mkdir -p build/outputs/apk/release

# 创建一个简单的ZIP文件作为APK（实际APK是ZIP格式）
echo "Creating debug APK..."
cd build/outputs/apk/debug

# 创建一个简单的测试文件
cat > README.txt << EOF
School Admin AI Assistant - Android APK
=======================================

版本: v1.1.0
构建时间: $(date)
平台: Android

这是一个测试APK文件。
实际APK需要使用Android Studio或Gradle构建。

构建步骤:
1. 安装Android Studio
2. 打开 frontend/android 项目
3. 构建APK: Build → Build APK(s)

文件说明:
- app-debug.apk: 调试版本
- app-release-unsigned.apk: 发布版本（未签名）

EOF

# 创建ZIP文件作为APK
zip -r app-debug.apk README.txt
rm README.txt

cd ../../..

# 创建release版本
cd build/outputs/apk/release
cp ../debug/app-debug.apk app-release-unsigned.apk
cd ../../..

echo "✅ 测试APK创建完成"
echo ""
echo "📁 文件位置:"
echo "  - Debug APK: build/outputs/apk/debug/app-debug.apk"
echo "  - Release APK: build/outputs/apk/release/app-release-unsigned.apk"
echo ""
echo "⚠️  注意: 这些是测试文件，不是真正的Android APK"
echo "要构建真正的APK，请使用Android Studio或配置Gradle环境"