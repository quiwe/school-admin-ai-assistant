#!/bin/bash
# Android构建脚本
# 使用方法: ./build-android.sh

set -e

echo "🚀 开始构建Android应用..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查必要工具
check_requirements() {
    echo "📋 检查构建环境..."
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ 错误: 未找到Node.js${NC}"
        echo "请安装Node.js: https://nodejs.org/"
        exit 1
    fi
    
    # 检查npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ 错误: 未找到npm${NC}"
        exit 1
    fi
    
    # 检查Java
    if ! command -v java &> /dev/null; then
        echo -e "${YELLOW}⚠️  警告: 未找到Java${NC}"
        echo "Android构建需要Java JDK 17+"
        echo "请安装: brew install openjdk@17"
        echo ""
        echo "是否继续尝试构建? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ 环境检查完成${NC}"
}

# 构建Web版本
build_web() {
    echo ""
    echo "🌐 构建Web版本..."
    
    if [ ! -f "package.json" ]; then
        echo -e "${RED}❌ 错误: 未找到package.json${NC}"
        echo "请确保在frontend目录中运行此脚本"
        exit 1
    fi
    
    npm run build
    echo -e "${GREEN}✅ Web版本构建完成${NC}"
}

# 同步到Android
sync_android() {
    echo ""
    echo "📱 同步到Android项目..."
    
    npm run android:sync
    echo -e "${GREEN}✅ Android同步完成${NC}"
}

# 构建Android APK
build_apk() {
    echo ""
    echo "📦 构建Android APK..."
    
    cd android
    
    # 检查是否有Gradle Wrapper
    if [ -f "gradlew" ]; then
        echo "使用Gradle Wrapper..."
        chmod +x gradlew
        ./gradlew assembleDebug
    elif command -v gradle &> /dev/null; then
        echo "使用系统Gradle..."
        gradle assembleDebug
    else
        echo -e "${RED}❌ 错误: 未找到Gradle${NC}"
        echo "请安装Gradle或使用Android Studio构建"
        echo ""
        echo "安装Gradle:"
        echo "  brew install gradle"
        echo ""
        echo "或者使用Android Studio打开项目:"
        echo "  npm run android:open"
        exit 1
    fi
    
    cd ..
    
    # 检查APK是否生成
    APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"
    if [ -f "$APK_PATH" ]; then
        echo -e "${GREEN}✅ APK构建成功${NC}"
        echo "📍 APK位置: $APK_PATH"
        echo "📊 APK大小: $(du -h "$APK_PATH" | cut -f1)"
    else
        echo -e "${RED}❌ APK构建失败${NC}"
        exit 1
    fi
}

# 创建Release包
create_release() {
    echo ""
    echo "📁 创建Release包..."
    
    # 创建release目录
    mkdir -p release
    
    # 复制APK
    if [ -f "android/app/build/outputs/apk/debug/app-debug.apk" ]; then
        cp "android/app/build/outputs/apk/debug/app-debug.apk" "release/school-admin-ai-assistant-v1.1.0.apk"
        echo -e "${GREEN}✅ APK已复制到release目录${NC}"
    fi
    
    # 复制Web版本
    if [ -d "dist" ]; then
        cp -r dist release/web
        echo -e "${GREEN}✅ Web版本已复制到release目录${NC}"
    fi
    
    # 创建压缩包
    if command -v zip &> /dev/null; then
        zip -r "release/school-admin-ai-assistant-v1.1.0.zip" release/
        echo -e "${GREEN}✅ Release压缩包已创建${NC}"
    fi
    
    echo "📍 Release目录: release/"
}

# 显示构建信息
show_info() {
    echo ""
    echo "🎉 构建完成！"
    echo ""
    echo "📦 构建产物:"
    
    if [ -f "android/app/build/outputs/apk/debug/app-debug.apk" ]; then
        echo "  - Android APK: android/app/build/outputs/apk/debug/app-debug.apk"
    fi
    
    if [ -d "dist" ]; then
        echo "  - Web版本: dist/"
    fi
    
    if [ -d "release" ]; then
        echo "  - Release包: release/"
    fi
    
    echo ""
    echo "🚀 下一步:"
    echo "  1. 测试APK: adb install android/app/build/outputs/apk/debug/app-debug.apk"
    echo "  2. 创建GitHub Release: 上传APK到GitHub Releases"
    echo "  3. 分发给用户"
    echo ""
    echo "📚 文档:"
    echo "  - 构建指南: BUILD_ANDROID.md"
    echo "  - 发布说明: RELEASE_NOTES.md"
    echo "  - 部署指南: DEPLOYMENT_GUIDE.md"
}

# 主函数
main() {
    echo "=========================================="
    echo "Android应用构建脚本"
    echo "版本: v1.1.0"
    echo "=========================================="
    echo ""
    
    check_requirements
    build_web
    sync_android
    build_apk
    create_release
    show_info
}

# 运行主函数
main "$@"