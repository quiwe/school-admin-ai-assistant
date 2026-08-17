#!/bin/bash
# 触发GitHub Actions构建脚本

set -e

echo "🚀 触发Android自动构建..."

# 检查Git状态
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  警告: 有未提交的更改"
    echo "请先提交所有更改"
    exit 1
fi

# 检查是否在main分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  警告: 当前不在main分支"
    echo "当前分支: $CURRENT_BRANCH"
    echo "请切换到main分支: git checkout main"
    exit 1
fi

# 检查是否已推送
if [ -n "$(git log origin/main..main --oneline)" ]; then
    echo "⚠️  警告: 有未推送的提交"
    echo "请先推送所有更改: git push origin main"
    exit 1
fi

echo "✅ 环境检查通过"

# 询问版本号
echo ""
echo "请输入版本号 (例如: v1.1.0):"
read -r VERSION

if [ -z "$VERSION" ]; then
    echo "❌ 版本号不能为空"
    exit 1
fi

# 检查标签是否已存在
if git tag -l "$VERSION" | grep -q "$VERSION"; then
    echo "⚠️  警告: 标签 $VERSION 已存在"
    echo "是否要删除并重新创建? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        git tag -d "$VERSION"
        git push origin :refs/tags/"$VERSION"
        echo "✅ 已删除旧标签"
    else
        echo "❌ 操作取消"
        exit 1
    fi
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