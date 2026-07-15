"""IndiaSat LULC class colours (matches web map / Titiler colormap)."""

from __future__ import annotations

# Values 0–12. 0 = transparent nodata.
LULC_COLORMAP: dict[str, str] = {
    "0": "#00000000",
    "1": "#006400",
    "2": "#FFBB22",
    "3": "#FF0000",
    "4": "#CCCCCC",
    "5": "#0077FF",
    "6": "#88FF88",
    "7": "#AA5500",
    "8": "#FFFFFF",
    "9": "#999999",
    "10": "#550088",
    "11": "#88CCEE",
    "12": "#117733",
}


def _hex_to_rgb_alpha(hex_color: str) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255


def write_gdaldem_color_file(path) -> None:
    """Write a gdaldem color-relief palette file."""
    lines = []
    for value in range(13):
        r, g, b, a = _hex_to_rgb_alpha(LULC_COLORMAP[str(value)])
        lines.append(f"{value} {r} {g} {b} {a}")
    path.write_text("\n".join(lines) + "\n")
