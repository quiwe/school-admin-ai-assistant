#!/bin/bash
# 下载Gradle Wrapper jar文件

set -e

echo "📥 下载Gradle Wrapper jar文件..."

# Gradle Wrapper jar的URL
WRAPPER_URL="https://services.gradle.org/distributions/gradle-8.11.1-bin.zip"
WRAPPER_JAR_URL="https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar"

# 创建目录
mkdir -p gradle/wrapper

# 下载gradle-wrapper.jar
echo "下载gradle-wrapper.jar..."
curl -L -o gradle/wrapper/gradle-wrapper.jar "$WRAPPER_JAR_URL"

# 检查下载结果
if [ -f "gradle/wrapper/gradle-wrapper.jar" ]; then
    echo "✅ gradle-wrapper.jar下载成功"
    echo "📊 文件大小: $(du -h gradle/wrapper/gradle-wrapper.jar | cut -f1)"
else
    echo "❌ gradle-wrapper.jar下载失败"
    echo "请手动下载并放置到 gradle/wrapper/ 目录"
    echo "下载链接: $WRAPPER_JAR_URL"
    exit 1
fi

# 设置权限
chmod +x gradlew
chmod +x gradlew.bat

echo ""
echo "🎉 Gradle Wrapper设置完成!"
echo ""
echo "📁 文件结构:"
echo "  - gradlew: Unix启动脚本"
echo "  - gradlew.bat: Windows启动脚本"
echo "  - gradle/wrapper/gradle-wrapper.jar: Gradle Wrapper jar"
echo "  - gradle/wrapper/gradle-wrapper.properties: 配置文件"
echo ""
echo "🚀 现在可以使用以下命令构建:"
echo "  ./gradlew assembleDebug"