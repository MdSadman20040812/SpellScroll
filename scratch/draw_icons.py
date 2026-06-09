import os
import sys

def draw():
    # Make sure Pillow is installed
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image, ImageDraw, ImageFont

    os.makedirs("static/icons", exist_ok=True)
    
    # Render sizes
    for size in [192, 512]:
        # Create dark background image
        img = Image.new("RGBA", (size, size), (13, 13, 20, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw glowing violet circle outer border
        margin = size // 10
        draw.ellipse(
            [(margin, margin), (size - margin, size - margin)],
            outline=(167, 139, 250, 255),
            width=size // 40
        )
        
        # Draw inner styling (a nice scroll representation)
        scroll_margin = size // 4
        # Scroll cylinder 1
        draw.rectangle(
            [(scroll_margin, scroll_margin + size//8), (size - scroll_margin, scroll_margin + size//4)],
            fill=(52, 211, 153, 255),
            outline=(167, 139, 250, 255),
            width=size // 80
        )
        # Scroll paper body
        draw.rectangle(
            [(scroll_margin + size//12, scroll_margin + size//4), (size - scroll_margin - size//12, size - scroll_margin)],
            fill=(167, 139, 250, 180),
            outline=(52, 211, 153, 255),
            width=size // 80
        )
        
        # Save images
        filepath = f"static/icons/icon-{size}.png"
        img.save(filepath, "PNG")
        print(f"Generated PWA icon: {filepath}")

if __name__ == "__main__":
    draw()
