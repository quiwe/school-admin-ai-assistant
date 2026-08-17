#!/bin/bash
# 修复GitHub Actions构建问题的脚本

set -e

echo "🔧 修复GitHub Actions构建问题..."

# 1. 确保gradle-wrapper.jar存在
echo "1. 检查gradle-wrapper.jar..."
if [ ! -f "frontend/android/gradle/wrapper/gradle-wrapper.jar" ]; then
    echo "下载gradle-wrapper.jar..."
    curl -L -o frontend/android/gradle/wrapper/gradle-wrapper.jar \
        "https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar"
fi

# 2. 确保gradlew有执行权限
echo "2. 设置gradlew权限..."
chmod +x frontend/android/gradlew
chmod +x frontend/android/gradlew.bat

# 3. 检查Capacitor Android模块
echo "3. 检查Capacitor Android模块..."
if [ ! -d "frontend/node_modules/@capacitor/android" ]; then
    echo "安装Capacitor Android..."
    cd frontend
    npm install @capacitor/android
    cd ..
fi

# 4. 创建符号链接（如果需要）
echo "4. 检查符号链接..."
if [ ! -d "frontend/android/node_modules" ]; then
    echo "创建node_modules符号链接..."
    ln -sf ../node_modules frontend/android/node_modules
fi

# 5. 检查Gradle配置
echo "5. 检查Gradle配置..."
if [ ! -f "frontend/android/gradle.properties" ]; then
    echo "创建gradle.properties..."
    cat > frontend/android/gradle.properties << EOF
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
EOF
fi

# 6. 测试Gradle Wrapper
echo "6. 测试Gradle Wrapper..."
cd frontend/android
if command -v java &> /dev/null; then
    echo "运行Gradle Wrapper测试..."
    ./gradlew --version
else
    echo "⚠️  Java未安装，跳过Gradle测试"
fi
cd ../..

echo ""
echo "✅ GitHub Actions修复完成!"
echo ""
echo "📋 下一步:"
echo "1. 提交更改: git add . && git commit -m 'fix: 修复GitHub Actions构建'"
echo "2. 推送代码: git push origin main"
echo "3. 重新触发构建: git tag -d v1.1.0 && git tag -a v1.1.0 -m 'v1.1.0' && git push origin v1.1.0"
echo ""
echo "🔗 监控构建: https://github.com/quiwe/school-admin-ai-assistant/actions"