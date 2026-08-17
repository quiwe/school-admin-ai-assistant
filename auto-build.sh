#!/bin/bash
# 自动构建脚本（非交互式）

set -e

echo "🚀 自动触发Android构建..."

# 检查Git状态
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ 错误: 有未提交的更改"
    exit 1
fi

# 检查是否在main分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "❌ 错误: 当前不在main分支"
    exit 1
fi

# 检查是否已推送
if [ -n "$(git log origin/main..main --oneline)" ]; then
    echo "❌ 错误: 有未推送的提交"
    exit 1
fi

# 使用v1.1.0版本
VERSION="v1.1.0"

# 检查标签是否已存在
if git tag -l "$VERSION" | grep -q "$VERSION"; then
    echo "⚠️  标签 $VERSION 已存在，删除并重新创建..."
    git tag -d "$VERSION"
    git push origin :refs/tags/"$VERSION"
fi

# 创建标签
echo "📝 创建标签: $VERSION"
git tag -a "$VERSION" -m "$VERSION: 修复Android图标显示不完整问题"

# 推送标签
echo "📤 推送标签到GitHub..."
git push origin "$VERSION"

echo ""
echo "🎉 构建触发成功！"
echo ""
echo "📋 接下来的步骤:"
echo "1. 访问 GitHub Actions: https://github.com/quiwe/school-admin-ai-assistant/actions"
echo "2. 等待构建完成 (约5-10分钟)"
echo "3. 下载APK文件"
echo "4. 创建GitHub Release (如果未自动创建)"
echo ""
echo "🔗 相关链接:"
echo "  - GitHub仓库: https://github.com/quiwe/school-admin-ai-assistant"
echo "  - Actions页面: https://github.com/quiwe/school-admin-ai-assistant/actions"
echo "  - Releases页面: https://github.com/quiwe/school-admin-ai-assistant/releases"
echo ""
echo "📱 构建产物:"
echo "  - app-debug.apk: 调试版本"
echo "  - app-release-unsigned.apk: 发布版本 (未签名)"
echo ""
echo "⏱️  预计构建时间: 5-10分钟"