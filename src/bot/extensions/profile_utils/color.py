import colorsys
import math
from functools import partial
from io import BytesIO

import hikari
import requests
from PIL import Image, ImageDraw

type RGB = tuple[int, int, int]

# fg color to bg color
fg_to_bg = {
    (255, 104, 104): (252, 206, 206),
    (251, 140, 65): (255, 212, 183),
    (232, 197, 72): (255, 244, 203),
    (152, 219, 107): (221, 245, 205),
    (71, 233, 109): (195, 255, 209),
    (54, 215, 175): (190, 248, 234),
    (122, 203, 233): (208, 241, 254),
    (93, 151, 243): (197, 216, 247),
    (86, 80, 254): (206, 204, 252),
    (135, 83, 240): (217, 200, 252),
    (197, 84, 249): (239, 207, 253),
    (239, 79, 229): (242, 194, 239),
    (242, 102, 186): (255, 198, 232),
    (241, 64, 123): (249, 194, 212),
    (36, 36, 41): (210, 210, 221),
}


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

    # Return the most popular vibrant accent color, otherwise return most popular
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


def get_colors(dominant_color: hikari.Color | None) -> tuple[RGB, RGB]:
    if dominant_color is None:
        return next(iter(fg_to_bg.items()))
    fg_color = min(fg_to_bg, key=partial(math.dist, dominant_color.rgb))
    return fg_color, fg_to_bg[fg_color]


def make_progress_bar(xp: int, total: int, fg_color: RGB, bg_color: RGB):
    width, height = 600, 20
    padding = 4
    radius = height // 2

    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=bg_color)
    filled = int(width * xp / total)
    if filled > 0:
        draw.rounded_rectangle(
            [padding, padding, filled - padding, height - padding],
            radius=radius,
            fill=fg_color,
        )
    return img
