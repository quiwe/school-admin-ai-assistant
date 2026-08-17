#!/bin/bash
# 使用Gradle Wrapper构建Android应用

set -e

echo "🚀 使用Gradle Wrapper构建Android应用..."

# 检查是否在正确的目录
if [ ! -f "gradlew" ]; then
    echo "❌ 错误: 未找到gradlew脚本"
    echo "请确保在android目录中运行此脚本"
    exit 1
fi

# 检查Java环境
if ! command -v java &> /dev/null; then
    echo "❌ 错误: 未找到Java"
    echo "请安装Java JDK 17+并设置JAVA_HOME环境变量"
    exit 1
fi

# 设置权限
chmod +x gradlew

# 清理之前的构建
echo "🧹 清理之前的构建..."
./gradlew clean

# 构建Debug APK
echo "📦 构建Debug APK..."
./gradlew assembleDebug

# 检查构建结果
if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo "✅ Debug APK构建成功!"
    echo "📍 位置: app/build/outputs/apk/debug/app-debug.apk"
    echo "📊 大小: $(du -h app/build/outputs/apk/debug/app-debug.apk | cut -f1)"
else
    echo "❌ Debug APK构建失败"
    exit 1
fi

# 构建Release APK（可选）
read -p "是否构建Release APK? (y/N): " build_release
if [[ "$build_release" =~ ^[Yy]$ ]]; then
    echo "📦 构建Release APK..."
    ./gradlew assembleRelease
    
    if [ -f "app/build/outputs/apk/release/app-release-unsigned.apk" ]; then
        echo "✅ Release APK构建成功!"
        echo "📍 位置: app/build/outputs/apk/release/app-release-unsigned.apk"
        echo "📊 大小: $(du -h app/build/outputs/apk/release/app-release-unsigned.apk | cut -f1)"
    else
        echo "❌ Release APK构建失败"
    fi
fi

echo ""
echo "🎉 构建完成!"
echo ""
echo "📱 APK文件:"
echo "  - Debug: app/build/outputs/apk/debug/app-debug.apk"
if [ -f "app/build/outputs/apk/release/app-release-unsigned.apk" ]; then
    echo "  - Release: app/build/outputs/apk/release/app-release-unsigned.apk"
fi
echo ""
echo "🚀 下一步:"
echo "  1. 安装到设备: adb install app/build/outputs/apk/debug/app-debug.apk"
echo "  2. 或者拖拽APK到模拟器"