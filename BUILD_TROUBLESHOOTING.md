# Android构建故障排除指南

## 🔍 最新修复

### 问题：缺少gradle-wrapper.jar
**症状**：
```
Error: Could not find or load main class org.gradle.wrapper.GradleWrapperMain
```

**解决方案**：
1. 下载gradle-wrapper.jar文件
2. 放置到 `frontend/android/gradle/wrapper/` 目录
3. 重新提交代码

**已实施**：
```bash
# 下载Gradle 8.11.1的wrapper jar
curl -L -o gradle/wrapper/gradle-wrapper.jar \
  "https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar"
```

### 问题：Gradle版本不匹配
**症状**：
```
The requestedGradle distribution 'https://services.gradle.org/distributions/gradle-8.5-bin.zip' 
does not match the wrapper distribution 'https://services.gradle.org/distributions/gradle-8.11.1-bin.zip'
```

**解决方案**：
1. 确保 `gradle-wrapper.properties` 中的版本与GitHub Actions配置一致
2. 当前配置：Gradle 8.11.1

**验证**：
```properties
# frontend/android/gradle/wrapper/gradle-wrapper.properties
distributionUrl=https\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
```

## 📋 GitHub Actions构建流程

### 当前工作流配置
```yaml
steps:
1. Checkout代码
2. Setup Node.js 18
3. Setup Java 17 (Temurin)
4. 安装npm依赖
5. 构建Web版本
6. 同步到Android
7. Setup Gradle 8.11.1
8. 构建Debug APK (./gradlew assembleDebug --stacktrace)
9. 构建Release APK (./gradlew assembleRelease --stacktrace)
10. 上传构建产物
11. 创建GitHub Release
```

### 关键配置
- **Node.js**: 18
- **Java**: 17 (Temurin)
- **Gradle**: 8.11.1
- **Android Gradle Plugin**: 8.9.2
- **Kotlin**: 2.1.0

## 🔧 常见构建错误及解决方案

### 1. 权限被拒绝
**错误**：
```
permission denied: ./gradlew
```

**解决方案**：
```yaml
- name: Build Debug APK
  run: |
    cd frontend/android
    chmod +x gradlew
    ./gradlew assembleDebug
```

### 2. Java版本不兼容
**错误**：
```
Unsupported class file major version 65
```

**解决方案**：
1. 确保使用Java 17
2. 检查 `build.gradle.kts` 中的Java版本配置：
```kotlin
compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}
```

### 3. Android SDK未找到
**错误**：
```
SDK location not found
```

**解决方案**：
GitHub Actions环境通常已配置Android SDK，但可以显式设置：
```yaml
- name: Setup Android SDK
  uses: android-actions/setup-android@v2
```

### 4. 依赖下载失败
**错误**：
```
Could not resolve com.android.tools.build:gradle:8.9.2
```

**解决方案**：
1. 检查网络连接
2. 添加Google Maven仓库：
```kotlin
// settings.gradle.kts
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
```

### 5. 内存不足
**错误**：
```
java.lang.OutOfMemoryError: Java heap space
```

**解决方案**：
在 `gradle.properties` 中增加内存配置：
```properties
org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=512m
```

## 🛠️ 调试步骤

### 1. 检查构建日志
访问 GitHub Actions 页面，查看详细的构建日志：
- 点击失败的构建记录
- 展开每个步骤的详细信息
- 查找错误信息

### 2. 本地复现问题
```bash
# 安装Java 17
brew install openjdk@17

# 设置JAVA_HOME
export JAVA_HOME=$(/usr/libexec/java_home -v 17)

# 进入Android目录
cd frontend/android

# 运行Gradle构建
./gradlew assembleDebug --stacktrace
```

### 3. 检查文件结构
确保以下文件存在：
```
frontend/android/
├── gradlew                    # ✅ 可执行文件
├── gradlew.bat                # ✅ Windows脚本
├── build.gradle.kts           # ✅ 构建配置
├── settings.gradle.kts        # ✅ 设置配置
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar      # ✅ 关键文件
│       └── gradle-wrapper.properties
└── app/
    └── build.gradle.kts       # ✅ 应用配置
```

## 📊 构建配置验证

### Android配置检查
```kotlin
// app/build.gradle.kts
android {
    namespace = "com.quiwe.schooladminaiassistant"
    compileSdk = 36
    
    defaultConfig {
        applicationId = "com.quiwe.schooladminaiassistant"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    
    kotlinOptions {
        jvmTarget = "17"
    }
}
```

### Gradle Wrapper配置检查
```properties
# gradle/wrapper/gradle-wrapper.properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

## 🚀 最新修复状态

### 已完成
✅ 下载并添加 `gradle-wrapper.jar`  
✅ 更新GitHub Actions工作流  
✅ 添加 `--stacktrace` 参数获取详细错误  
✅ 创建v1.1.0标签触发构建  

### 当前构建
- **触发时间**: 2026年8月17日 12:50
- **构建版本**: v1.1.0
- **预计时间**: 5-10分钟

### 监控链接
- **Actions页面**: https://github.com/quiwe/school-admin-ai-assistant/actions
- **Releases页面**: https://github.com/quiwe/school-admin-ai-assistant/releases

## 📱 预期构建产物

### Debug APK
- **文件名**: `app-debug.apk`
- **用途**: 调试和测试
- **特点**: 包含调试信息，可直接安装
- **大小**: 约10-20MB

### Release APK
- **文件名**: `app-release-unsigned.apk`
- **用途**: 发布前测试
- **特点**: 未签名，需要签名后才能发布
- **大小**: 约8-15MB

## 🔍 如果构建仍然失败

### 可能的其他问题

#### 1. Capacitor版本兼容性
检查Capacitor版本与Android Gradle Plugin的兼容性：
```json
// package.json
{
  "dependencies": {
    "@capacitor/core": "^8.3.4",
    "@capacitor/android": "^8.3.4"
  }
}
```

#### 2. Android Gradle Plugin版本
当前使用8.9.2，确保与Gradle 8.11.1兼容：
```kotlin
// build.gradle.kts
plugins {
    id("com.android.application") version "8.9.2" apply false
}
```

#### 3. Kotlin版本
当前使用2.1.0，确保与其他依赖兼容：
```kotlin
plugins {
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
}
```

### 手动构建测试
如果GitHub Actions持续失败，可以尝试本地构建：

1. **安装Android Studio**
2. **打开项目**: `npm run android:open`
3. **构建APK**: Build → Build APK(s)
4. **检查错误日志**

## 📞 获取帮助

### 查看构建日志
1. 访问 GitHub Actions 页面
2. 点击失败的构建记录
3. 展开 "Build Debug APK" 步骤
4. 查看详细的错误信息

### 常见错误代码
- **1**: 一般错误
- **2**: 权限问题
- **137**: 内存不足
- **143**: 进程被终止

### 联系开发者
- **GitHub Issues**: https://github.com/quiwe/school-admin-ai-assistant/issues
- **邮箱**: quiwe@qq.com

## 🎯 总结

### 当前状态
✅ **gradle-wrapper.jar** - 已添加  
✅ **GitHub Actions** - 已优化  
✅ **版本标签** - 已创建  
⏳ **构建中** - 等待验证

### 预期结果
- ✅ Gradle Wrapper正常工作
- ✅ APK构建成功
- ✅ 构建产物上传
- ✅ Release自动创建

### 下一步
1. **监控构建状态**
2. **等待构建完成**（5-10分钟）
3. **下载APK文件**
4. **测试应用功能**

---

**修复状态**: ✅ 已完成  
**构建状态**: ⏳ 等待验证  
**预计效果**: 构建成功