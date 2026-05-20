#!/usr/bin/env python
"""
Generate PWA icons from SVG source.
Requires: cairosvg (pip install cairosvg) or PIL with svg support
"""

import os
from pathlib import Path

# Icon sizes required for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Paths
STATIC_DIR = Path(__file__).parent / 'static'
ICONS_DIR = STATIC_DIR / 'icons'
SVG_SOURCE = ICONS_DIR / 'icon.svg'

def generate_icons_with_cairosvg():
    """Generate PNG icons using cairosvg library."""
    try:
        import cairosvg
    except ImportError:
        print("cairosvg not installed. Run: pip install cairosvg")
        return False
    
    for size in ICON_SIZES:
        output_path = ICONS_DIR / f'icon-{size}x{size}.png'
        cairosvg.svg2png(
            url=str(SVG_SOURCE),
            write_to=str(output_path),
            output_width=size,
            output_height=size
        )
        print(f"Generated: {output_path}")
    
    return True

def generate_icons_with_pil():
    """Generate PNG icons using PIL (basic fallback)."""
    try:
        from PIL import Image
        import io
    except ImportError:
        print("PIL not installed. Run: pip install Pillow")
        return False
    
    # Read SVG
    with open(SVG_SOURCE, 'r') as f:
        svg_data = f.read()
    
    for size in ICON_SIZES:
        output_path = ICONS_DIR / f'icon-{size}x{size}.png'
        
        # Note: PIL doesn't natively support SVG rendering
        # This is a placeholder - you need cairosvg or svglib for proper SVG to PNG
        print(f"Warning: PIL cannot render SVG directly. Use cairosvg instead.")
        print(f"Skipping: {output_path}")
    
    return False

def main():
    """Main function to generate PWA icons."""
    print("Generating PWA icons...")
    print(f"Source: {SVG_SOURCE}")
    print(f"Output directory: {ICONS_DIR}")
    
    # Ensure icons directory exists
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Try cairosvg first (recommended)
    if generate_icons_with_cairosvg():
        print("\n✓ All icons generated successfully using cairosvg!")
        return
    
    # Fallback to PIL (won't work for SVG)
    print("\nTrying PIL fallback...")
    if generate_icons_with_pil():
        print("\n✓ All icons generated successfully using PIL!")
        return
    
    print("\n✗ Failed to generate icons.")
    print("\nTo install required dependencies:")
    print("  pip install cairosvg")
    print("\nOr use an online tool like:")
    print("  https://realfavicongenerator.net/")
    print("  https://www.favicon-generator.org/")

if __name__ == '__main__':
    main()
