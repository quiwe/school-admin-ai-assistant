#!/bin/bash
# 测试Gradle Wrapper是否正常工作

set -e

echo "🔍 测试Gradle Wrapper..."

# 检查文件是否存在
echo "1. 检查必要文件..."
if [ ! -f "gradlew" ]; then
    echo "❌ 错误: gradlew文件不存在"
    exit 1
fi

if [ ! -f "gradlew.bat" ]; then
    echo "❌ 错误: gradlew.bat文件不存在"
    exit 1
fi

if [ ! -f "gradle/wrapper/gradle-wrapper.jar" ]; then
    echo "❌ 错误: gradle-wrapper.jar文件不存在"
    echo "请运行 ./download-wrapper.sh 下载"
    exit 1
fi

if [ ! -f "gradle/wrapper/gradle-wrapper.properties" ]; then
    echo "❌ 错误: gradle-wrapper.properties文件不存在"
    exit 1
fi

echo "✅ 所有必要文件存在"

# 检查文件权限
echo ""
echo "2. 检查文件权限..."
if [ ! -x "gradlew" ]; then
    echo "⚠️  gradlew没有执行权限，正在修复..."
    chmod +x gradlew
fi

echo "✅ 文件权限正确"

# 检查Java环境
echo ""
echo "3. 检查Java环境..."
if ! command -v java &> /dev/null; then
    echo "⚠️  警告: 未找到Java"
    echo "Gradle Wrapper需要Java 17+"
    echo "请安装: brew install openjdk@17"
else
    java_version=$(java -version 2>&1 | head -n 1)
    echo "✅ Java版本: $java_version"
fi

# 检查Gradle Wrapper配置
echo ""
echo "4. 检查Gradle Wrapper配置..."
if grep -q "gradle-8.11.1-bin.zip" "gradle/wrapper/gradle-wrapper.properties"; then
    echo "✅ Gradle版本配置正确: 8.11.1"
else
    echo "⚠️  警告: Gradle版本可能不匹配"
    echo "当前配置:"
    grep "distributionUrl" "gradle/wrapper/gradle-wrapper.properties"
fi

# 测试Gradle Wrapper
echo ""
echo "5. 测试Gradle Wrapper..."
if command -v java &> /dev/null; then
    echo "运行: ./gradlew --version"
    if ./gradlew --version; then
        echo "✅ Gradle Wrapper测试成功"
    else
        echo "❌ Gradle Wrapper测试失败"
        echo "请检查Java环境和Gradle配置"
    fi
else
    echo "⚠️  跳过Gradle Wrapper测试（需要Java环境）"
fi

echo ""
echo "🎉 Gradle Wrapper检查完成!"
echo ""
echo "📁 文件结构:"
ls -la gradlew gradlew.bat
ls -la gradle/wrapper/
echo ""
echo "🚀 如果所有检查通过，可以运行构建:"
echo "  ./gradlew assembleDebug"