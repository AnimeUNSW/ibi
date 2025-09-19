import colorsys
from io import BytesIO

import hikari
import requests
from PIL import Image, ImageDraw


def get_dominant_color(url: hikari.URL) -> hikari.Color | None:
    try:
        res = requests.get(url.url, timeout=10)
        res.raise_for_status()
    except requests.Timeout:
        print(f"Image request for {url} timed out")
        return None
    except requests.HTTPError as e:
        print(f"Image request for {url} gave HTTPError: {e}")
        return None
    except requests.RequestException as e:
        print(f"Image request for {url} gave RequestException: {e}")
        return None

    img = Image.open(BytesIO(res.content))
    paletted = img.convert("P", palette=Image.ADAPTIVE, colors=16)  # type: ignore[reportAttributeAccessIssue]
    palette = paletted.getpalette()
    if palette is None:
        return None
    colors = paletted.getcolors()
    if not colors:
        return None
    color_counts = sorted(colors, reverse=True)
    idx = color_counts[0][1]
    for _, idx in color_counts:
        rgb = palette[3 * idx : 3 * idx + 3]  # type: ignore[reportOperatorIssue]
        if is_vibrant_accent(rgb):
            return hikari.Color.of(rgb)
    # If can't, just return most popular color
    idx = color_counts[0][1]
    rgb = palette[3 * idx : 3 * idx + 3]  # type: ignore[reportOperatorIssue]
    return hikari.Color.of(rgb)


def is_vibrant_accent(rgb):
    r, g, b = [x / 255 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.5 or v < 0.4 or v > 0.9:
        return False

    if (0.0 <= h <= 0.05) or (0.95 <= h <= 1.0):  # red
        return True
    elif 0.25 <= h <= 0.45:  # green
        return True
    elif 0.55 <= h <= 0.75:  # blue
        return True

    return False


def make_progress_bar(xp: int, total: int, color: hikari.Color | None):
    if color is None:
        # Just some default blue-ish color
        color = hikari.Color(0x2892D7)
    width, height = 600, 40
    bg_color = (250, 250, 250, 255)
    bar_color = (40, 146, 215, 255)
    padding = 5
    radius = 20

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=bg_color)
    filled = int(width * xp / total)
    if filled > 0:
        draw.rounded_rectangle(
            [padding, padding, filled - padding, height - padding],
            radius=radius,
            fill=bar_color,
        )
    return img
