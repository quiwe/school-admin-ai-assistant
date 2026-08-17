#!/usr/bin/env python3
"""
Generate Android app icons in different densities
"""

from PIL import Image, ImageDraw
import os

def create_icon(size, output_path):
    """Create an app icon with the specified size"""
    # Create a new image with RGBA mode
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a blue circle background
    margin = size // 10
    circle_bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(circle_bbox, fill='#3B82F6')
    
    # Draw a white "AI" text in the center
    text = "AI"
    text_color = '#FFFFFF'
    
    # Calculate text position (center of circle)
    text_x = size // 2
    text_y = size // 2
    
    # For simplicity, we'll draw a simple representation
    # In a real app, you'd use a proper font and text rendering
    # Here we'll draw two vertical lines for 'A' and 'I'
    
    line_width = size // 20
    
    # Draw 'A' (simplified as two lines with a crossbar)
    a_left = text_x - size // 6
    a_right = text_x + size // 6
    a_top = text_y - size // 6
    a_bottom = text_y + size // 6
    
    # Left vertical line of A
    draw.line([(a_left, a_bottom), (a_left, a_top)], fill=text_color, width=line_width)
    # Right vertical line of A
    draw.line([(a_right, a_bottom), (a_right, a_top)], fill=text_color, width=line_width)
    # Crossbar of A
    draw.line([(a_left, text_y), (a_right, text_y)], fill=text_color, width=line_width)
    
    # Draw 'I' (simple vertical line)
    i_x = text_x + size // 4
    i_top = text_y - size // 6
    i_bottom = text_y + size // 6
    
    draw.line([(i_x, i_bottom), (i_x, i_top)], fill=text_color, width=line_width)
    
    # Save the image
    img.save(output_path, 'PNG')
    print(f"Created icon: {output_path} ({size}x{size})")

def main():
    # Icon sizes for different Android densities
    densities = {
        'mdpi': 48,
        'hdpi': 72,
        'xhdpi': 96,
        'xxhdpi': 144,
        'xxxhdpi': 192
    }
    
    # Base directory for Android resources
    base_dir = '/Users/maoqiu/school-admin-ai-assistant/frontend/android/app/src/main/res'
    
    for density, size in densities.items():
        # Create mipmap directory if it doesn't exist
        mipmap_dir = os.path.join(base_dir, f'mipmap-{density}')
        os.makedirs(mipmap_dir, exist_ok=True)
        
        # Generate icon
        icon_path = os.path.join(mipmap_dir, 'ic_launcher.png')
        create_icon(size, icon_path)
    
    print("All icons generated successfully!")

if __name__ == '__main__':
    main()