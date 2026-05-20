# PWA App Icons

This directory contains icons for the Progressive Web App (PWA).

## Current Status
- `icon.svg` - SVG source file (placeholder)

## Required Icons
The manifest.json requires the following PNG icons:
- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

## How to Generate Icons

### Option 1: Using ImageMagick (Recommended)
```bash
# Install ImageMagick if not installed
# Ubuntu/Debian: sudo apt-get install imagemagick
# macOS: brew install imagemagick

# Generate all required sizes from SVG
convert icon.svg -resize 72x72 icon-72x72.png
convert icon.svg -resize 96x96 icon-96x96.png
convert icon.svg -resize 128x128 icon-128x128.png
convert icon.svg -resize 144x144 icon-144x144.png
convert icon.svg -resize 152x152 icon-152x152.png
convert icon.svg -resize 192x192 icon-192x192.png
convert icon.svg -resize 384x384 icon-384x384.png
convert icon.svg -resize 512x512 icon-512x512.png
```

### Option 2: Using Online Tools
1. Visit https://realfavicongenerator.net/
2. Upload your SVG or custom design
3. Download the generated icon package
4. Extract and rename icons to match the required sizes

### Option 3: Using Figma/Canva
1. Create a 512x512 design
2. Export at multiple sizes
3. Rename files to match required sizes

## Design Guidelines
- Use your church logo or a simple icon
- Ensure good contrast on dark/light backgrounds
- Keep it simple and recognizable at small sizes
- Use your brand colors (currently set to #2c3e50 for theme)
- Consider using a church cross or building icon

## Testing
After generating icons, test the PWA:
1. Open your site in Chrome/Edge
2. Open DevTools → Application → Manifest
3. Verify all icons load correctly
4. Test on mobile device for install prompt
