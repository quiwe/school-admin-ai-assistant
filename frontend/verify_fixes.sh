#!/bin/bash

echo "🔍 验证Android图标修复..."
echo ""

# 检查关键文件
echo "1. 检查关键配置文件..."
if [ -f "android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml" ]; then
    echo "   ✅ ic_launcher.xml 存在"
else
    echo "   ❌ ic_launcher.xml 缺失"
fi

if [ -f "android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml" ]; then
    echo "   ✅ ic_launcher_round.xml 存在"
else
    echo "   ❌ ic_launcher_round.xml 缺失"
fi

if [ -f "android/app/src/main/res/drawable/ic_launcher_foreground.xml" ]; then
    echo "   ✅ ic_launcher_foreground.xml 存在"
else
    echo "   ❌ ic_launcher_foreground.xml 缺失"
fi

echo ""
echo "2. 检查mipmap图标文件..."
densities=("mdpi" "hdpi" "xhdpi" "xxhdpi" "xxxhdpi")
for density in "${densities[@]}"; do
    if [ -f "android/app/src/main/res/mipmap-${density}/ic_launcher.png" ]; then
        echo "   ✅ ${density}/ic_launcher.png 存在"
    else
        echo "   ❌ ${density}/ic_launcher.png 缺失"
    fi
    
    if [ -f "android/app/src/main/res/mipmap-${density}/ic_launcher_round.png" ]; then
        echo "   ✅ ${density}/ic_launcher_round.png 存在"
    else
        echo "   ❌ ${density}/ic_launcher_round.png 缺失"
    fi
done

echo ""
echo "3. 检查图标文件大小..."
for density in "${densities[@]}"; do
    if [ -f "android/app/src/main/res/mipmap-${density}/ic_launcher.png" ]; then
        size=$(stat -f%z "android/app/src/main/res/mipmap-${density}/ic_launcher.png" 2>/dev/null || stat -c%s "android/app/src/main/res/mipmap-${density}/ic_launcher.png" 2>/dev/null)
        echo "   ${density}/ic_launcher.png: ${size} bytes"
    fi
done

echo ""
echo "4. 检查AndroidManifest.xml图标引用..."
if grep -q "@mipmap/ic_launcher" "android/app/src/main/AndroidManifest.xml"; then
    echo "   ✅ AndroidManifest.xml 正确引用了 @mipmap/ic_launcher"
else
    echo "   ❌ AndroidManifest.xml 图标引用可能有问题"
fi

echo ""
echo "5. 检查向量图标内容..."
if grep -q "android:pathData" "android/app/src/main/res/drawable/ic_launcher_foreground.xml"; then
    echo "   ✅ 向量图标包含路径数据"
else
    echo "   ❌ 向量图标可能缺少路径数据"
fi

echo ""
echo "=========================================="
echo "✅ 验证完成！"
echo ""
echo "下一步操作："
echo "1. 运行 'npm run android:sync' 同步项目"
echo "2. 运行 'npm run android:open' 在Android Studio中打开项目"
echo "3. 构建并运行应用，检查图标显示效果"
echo ""
echo "如需重新生成图标，运行: npm run generate:icons"