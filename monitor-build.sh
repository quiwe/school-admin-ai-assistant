#!/bin/bash
# 监控GitHub Actions构建状态

set -e

echo "🔍 监控GitHub Actions构建状态..."
echo ""

# 检查是否安装了GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "⚠️  未安装GitHub CLI，使用浏览器监控"
    echo ""
    echo "请手动访问以下链接监控构建状态:"
    echo "  - Actions页面: https://github.com/quiwe/school-admin-ai-assistant/actions"
    echo "  - Releases页面: https://github.com/quiwe/school-admin-ai-assistant/releases"
    echo ""
    echo "构建完成后，下载APK文件:"
    echo "  - app-debug.apk: 调试版本"
    echo "  - app-release-unsigned.apk: 发布版本"
    exit 0
fi

# 使用GitHub CLI监控构建
echo "使用GitHub CLI监控构建..."
echo ""

# 检查最新的workflow run
echo "📋 最新的构建记录:"
gh run list --limit 5

echo ""
echo "🔍 查看最新的构建详情..."

# 获取最新的workflow run ID
LATEST_RUN=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

if [ -n "$LATEST_RUN" ]; then
    echo "构建ID: $LATEST_RUN"
    echo ""
    
    # 监控构建状态
    echo "⏳ 等待构建完成..."
    echo "（按 Ctrl+C 停止监控）"
    echo ""
    
    # 持续监控直到构建完成
    while true; do
        STATUS=$(gh run view $LATEST_RUN --json status --jq '.status')
        CONCLUSION=$(gh run view $LATEST_RUN --json conclusion --jq '.conclusion')
        
        echo "$(date '+%H:%M:%S') - 状态: $STATUS"
        
        if [ "$STATUS" = "completed" ]; then
            if [ "$CONCLUSION" = "success" ]; then
                echo ""
                echo "🎉 构建成功！"
                echo ""
                echo "📦 构建产物:"
                gh run view $LATEST_RUN --json jobs --jq '.jobs[] | select(.name == "build") | .steps[] | select(.name == "Upload Debug APK") | .conclusion'
                
                echo ""
                echo "📥 下载APK文件:"
                echo "  gh run download $LATEST_RUN"
                echo ""
                echo "🔗 或者访问GitHub页面下载:"
                echo "  https://github.com/quiwe/school-admin-ai-assistant/actions/runs/$LATEST_RUN"
            else
                echo ""
                echo "❌ 构建失败: $CONCLUSION"
                echo ""
                echo "🔍 查看构建日志:"
                echo "  gh run view $LATEST_RUN --log"
            fi
            break
        fi
        
        sleep 30
    done
else
    echo "❌ 未找到构建记录"
    echo ""
    echo "请手动访问GitHub Actions页面:"
    echo "  https://github.com/quiwe/school-admin-ai-assistant/actions"
fi