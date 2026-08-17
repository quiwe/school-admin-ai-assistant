# Android应用打包指南

## 当前状态

✅ **Web版本已构建成功**
✅ **Android项目已同步**
⚠️ **需要Android Studio或Java环境来构建APK**

## 构建方法

### 方法1：使用Android Studio（推荐）

1. **安装Android Studio**
   - 下载：https://developer.android.com/studio
   - 安装并配置Android SDK

2. **打开项目**
   ```bash
   cd frontend
   npm run android:open
   ```

3. **构建APK**
   - 在Android Studio中：Build → Build Bundle(s) / APK(s) → Build APK(s)
   - 等待构建完成
   - APK位置：`android/app/build/outputs/apk/debug/app-debug.apk`

### 方法2：使用命令行（需要Java和Gradle）

1. **安装Java JDK 17+**
   ```bash
   # macOS (使用Homebrew)
   brew install openjdk@17
   ```

2. **安装Gradle**
   ```bash
   brew install gradle
   ```

3. **构建APK**
   ```bash
   cd android
   gradle assembleDebug
   ```

4. **APK位置**
   ```
   app/build/outputs/apk/debug/app-debug.apk
   ```

### 方法3：使用Capacitor CLI（如果配置了）

```bash
cd frontend
npx cap build android
```

## 当前环境检查

### 已完成
✅ Web版本构建完成（dist目录）
✅ Android项目同步完成
✅ 图标资源已生成
✅ 配置文件已更新

### 需要环境
⚠️ Java JDK 17+
⚠️ Android SDK
⚠️ Gradle或Android Studio

## 快速构建脚本

如果环境已配置，可以使用以下脚本：

```bash
#!/bin/bash
# build-android.sh

echo "1. 构建Web版本..."
npm run build

echo "2. 同步到Android..."
npm run android:sync

echo "3. 构建Android APK..."
cd android
if command -v gradle &> /dev/null; then
    gradle assembleDebug
elif [ -f "gradlew" ]; then
    ./gradlew assembleDebug
else
    echo "错误：未找到Gradle或Gradle Wrapper"
    echo "请安装Gradle或使用Android Studio构建"
    exit 1
fi

echo "4. 构建完成！"
echo "APK位置：app/build/outputs/apk/debug/app-debug.apk"
```

## 发布到Releases

### 1. 创建GitHub Release

```bash
# 创建带注释的标签
git tag -a v1.1.0 -m "v1.1.0: 修复Android图标显示不完整问题"

# 推送标签
git push origin v1.1.0
```

### 2. 上传APK到Release

1. 访问 GitHub 仓库：https://github.com/quiwe/school-admin-ai-assistant
2. 点击 "Releases" → "Create a new release"
3. 选择标签：v1.1.0
4. 填写发布说明（从RELEASE_NOTES.md复制）
5. 上传APK文件
6. 发布Release

### 3. 发布说明模板

```markdown
## v1.1.0 - 2026年8月17日

### 🐛 Bug 修复
- 修复Android图标显示不完整问题

### 📦 下载
- `app-debug.apk` - Android调试版本

### 📋 安装说明
1. 下载APK文件
2. 在Android设备上启用"未知来源"安装
3. 安装APK文件
4. 享受修复后的应用！

### 🔧 技术细节
- 自适应图标配置修复
- 所有密度的mipmap图标生成
- 圆形图标变体支持
```

## 验证构建

### 检查APK文件
```bash
# 检查APK是否存在
ls -la android/app/build/outputs/apk/debug/

# 检查APK信息
aapt dump badging android/app/build/outputs/apk/debug/app-debug.apk
```

### 测试APK
```bash
# 安装到连接的设备
adb install android/app/build/outputs/apk/debug/app-debug.apk

# 或者拖拽到模拟器
```

## 故障排除

### 问题1：缺少Java环境
**解决方案**：
```bash
# 安装OpenJDK 17
brew install openjdk@17

# 配置环境变量
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

### 问题2：缺少Android SDK
**解决方案**：
1. 安装Android Studio
2. 或者手动安装Android SDK
3. 设置ANDROID_HOME环境变量

### 问题3：Gradle构建失败
**解决方案**：
```bash
# 清理并重新构建
cd android
gradle clean
gradle assembleDebug
```

## 自动化构建

### GitHub Actions配置

创建 `.github/workflows/build-android.yml`：

```yaml
name: Build Android APK

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Setup Java
      uses: actions/setup-java@v3
      with:
        distribution: 'temurin'
        java-version: '17'
        
    - name: Install dependencies
      run: |
        cd frontend
        npm install
        
    - name: Build Web
      run: |
        cd frontend
        npm run build
        
    - name: Sync Android
      run: |
        cd frontend
        npm run android:sync
        
    - name: Build APK
      run: |
        cd frontend/android
        gradle assembleDebug
        
    - name: Upload APK
      uses: actions/upload-artifact@v3
      with:
        name: app-debug
        path: frontend/android/app/build/outputs/apk/debug/app-debug.apk
        
    - name: Create Release
      uses: softprops/action-gh-release@v1
      if: startsWith(github.ref, 'refs/tags/')
      with:
        files: frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

## 总结

### 当前状态
✅ **代码已修复并推送**
✅ **Web版本已构建**
✅ **Android项目已同步**
⚠️ **需要构建环境来打包APK**

### 下一步
1. 配置Android构建环境（Java + Android SDK）
2. 使用Android Studio构建APK
3. 创建GitHub Release
4. 上传APK到Release
5. 分发给用户

### 联系信息
如需帮助，请参考：
- Android官方文档：https://developer.android.com
- Capacitor文档：https://capacitorjs.com
- GitHub Issues：https://github.com/quiwe/school-admin-ai-assistant/issues