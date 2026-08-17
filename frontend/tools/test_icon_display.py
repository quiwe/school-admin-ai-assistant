#!/usr/bin/env python3
"""
Test script to verify Android app icon display
"""

import os
import sys

def check_icon_files():
    """Check if all required icon files exist"""
    base_dir = '/Users/maoqiu/school-admin-ai-assistant/frontend/android/app/src/main/res'
    
    required_files = [
        'mipmap-anydpi-v26/ic_launcher.xml',
        'mipmap-anydpi-v26/ic_launcher_round.xml',
        'drawable/ic_launcher_foreground.xml',
        'values/colors.xml'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(base_dir, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print("✅ All required icon files exist")
        return True

def check_mipmap_icons():
    """Check if mipmap icons exist for all densities"""
    base_dir = '/Users/maoqiu/school-admin-ai-assistant/frontend/android/app/src/main/res'
    
    densities = ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']
    icon_types = ['ic_launcher.png', 'ic_launcher_round.png']
    
    missing_icons = []
    for density in densities:
        for icon_type in icon_types:
            icon_path = os.path.join(base_dir, f'mipmap-{density}', icon_type)
            if not os.path.exists(icon_path):
                missing_icons.append(f'mipmap-{density}/{icon_type}')
    
    if missing_icons:
        print("❌ Missing mipmap icons:")
        for icon in missing_icons:
            print(f"  - {icon}")
        return False
    else:
        print("✅ All mipmap icons exist for all densities")
        return True

def check_icon_sizes():
    """Check if icon sizes are correct"""
    base_dir = '/Users/maoqiu/school-admin-ai-assistant/frontend/android/app/src/main/res'
    
    expected_sizes = {
        'mdpi': 48,
        'hdpi': 72,
        'xhdpi': 96,
        'xxhdpi': 144,
        'xxxhdpi': 192
    }
    
    size_issues = []
    for density, expected_size in expected_sizes.items():
        icon_path = os.path.join(base_dir, f'mipmap-{density}', 'ic_launcher.png')
        if os.path.exists(icon_path):
            try:
                from PIL import Image
                with Image.open(icon_path) as img:
                    actual_size = img.size[0]
                    if actual_size != expected_size:
                        size_issues.append(f'{density}: expected {expected_size}, got {actual_size}')
            except ImportError:
                # PIL not available, skip size check
                pass
    
    if size_issues:
        print("⚠️  Icon size issues:")
        for issue in size_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All icon sizes are correct")
        return True

def main():
    print("🔍 Checking Android app icon configuration...\n")
    
    all_ok = True
    
    # Check required files
    if not check_icon_files():
        all_ok = False
    
    # Check mipmap icons
    if not check_mipmap_icons():
        all_ok = False
    
    # Check icon sizes
    if not check_icon_sizes():
        all_ok = False
    
    print("\n" + "="*50)
    if all_ok:
        print("✅ All icon checks passed! Android app icons should display correctly.")
        print("\nNext steps:")
        print("1. Rebuild the Android app: npx cap sync android && npx cap open android")
        print("2. Build and run the app in Android Studio")
        print("3. Check the app icon on your device/emulator")
    else:
        print("❌ Some icon checks failed. Please fix the issues above.")
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    main()