from PIL import Image, ImageDraw, ImageFont

_icon_cache = {}


def get_font(size):
    candidates = ["arialbd.ttf", "msyhbd.ttc", "arial.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_icon_image(percent_remaining, error=False):
    cache_key = "error" if error else "normal"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if error:
        color = (120, 120, 120, 255)
    else:
        if percent_remaining >= 50:
            color = (67, 160, 71, 255)
        elif percent_remaining >= 20:
            color = (255, 152, 0, 255)
        else:
            color = (229, 57, 53, 255)

    draw.ellipse((6, 6, size - 6, size - 6), fill=color)

    _icon_cache[cache_key] = img
    return img
