plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
}

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

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = false
    }

    sourceSets {
        getByName("main") {
            assets.srcDirs("src/main/assets", "../dist")
            java.srcDirs("src/main/java")
        }
    }
}

dependencies {
    // Capacitor
    implementation(project(":capacitor-android"))

    // NanoHTTPD — embedded HTTP server
    implementation("org.nanohttpd:nanohttpd:2.3.1")

    // Room — SQLite ORM
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // OkHttp — HTTP client for AI providers
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // kotlinx.serialization — JSON
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    // AndroidX core
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")

    // PDFBox — PDF parsing
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0")
}
