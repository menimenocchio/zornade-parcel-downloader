#!/usr/bin/env python3
"""
Create a simple icon for the plugin.
Requires PIL/Pillow: pip install Pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a 24x24 pixel image
    size = (24, 24)
    img = Image.new('RGBA', size, (70, 130, 180, 255))  # Steel blue background
    
    draw = ImageDraw.Draw(img)
    
    # Draw a simple house-like shape representing parcels
    # Draw a rectangle (parcel)
    draw.rectangle([4, 8, 20, 20], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    
    # Draw a smaller rectangle inside
    draw.rectangle([7, 11, 17, 17], fill=None, outline=(0, 0, 0, 255))
    
    # Save the icon
    img.save('icon.png')
    print("Icon created: icon.png")
    
except ImportError:
    print("PIL/Pillow not available. Please create an icon.png file manually (24x24 pixels)")
    print("Or install Pillow: pip install Pillow")
