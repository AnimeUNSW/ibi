import math
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


def rgb_to_yuv(color: RGB) -> tuple[float, float, float]:
    r, g, b = color
    return (
        0.299 * r + 0.587 * g + 0.114 * b,
        -0.14713 * r - 0.28886 * g + 0.436 * b,
        0.615 * r - 0.51499 * g - 0.10001 * b,
    )


fg_rgb_to_yuv = {color: rgb_to_yuv(color) for color in fg_to_bg}


def get_dominant_color(url: hikari.URL) -> RGB | None:
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
    img = img.convert("RGB").resize((16, 16))
    pixels = [*img.getdata()]

    def similarity(color: RGB) -> float:
        k = 0.03
        threshold = 60

        score = 0
        num_similar = 0
        for pixel in pixels:
            d = math.dist(fg_rgb_to_yuv[color], rgb_to_yuv(pixel))
            if d < threshold:
                print(d)
                score += math.exp(-k * d * d)
                num_similar += 1
        if num_similar < 30:
            return float("-inf")
        return score

    black = (36, 36, 41)

    cbest = None
    cbest_score = 0
    for color in fg_to_bg:
        if color != black:
            score = similarity(color)
            if score == float("-inf"):
                continue
            if score > cbest_score:
                cbest_score = score
                cbest = color

    return cbest or black


def get_colors(url: hikari.URL) -> tuple[RGB, RGB]:
    dominant_color = get_dominant_color(url)
    if dominant_color is None:
        return next(iter(fg_to_bg.items()))
    return dominant_color, fg_to_bg[dominant_color]


def make_progress_bar(xp: int, total: int, fg_color: RGB, bg_color: RGB):
    width, height = 600, 20
    padding = 4
    radius = height // 2

    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=bg_color)
    filled = int(width * xp / total)
    if filled > 0 and padding < filled - padding:
        draw.rounded_rectangle(
            [padding, padding, filled - padding, height - padding],
            radius=radius,
            fill=fg_color,
        )
    return img
