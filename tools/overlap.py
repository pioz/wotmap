# $ python3 overlap.py --assets-dir overlap

#!/usr/bin/env python3
"""
Annotate a large map with POIs, labels, and nation borders.

Inputs (same folder or specify with --assets-dir):
- map.jpg
- HyliaSerifBeta-Regular.otf
- stedding.png
- portal_stone.png
- poi.json (keys: portal_stones, steddings, rivers, nations)

Rules:
- portal_stones: place "portal_stone.png" centered at coord.
- steddings: place "stedding.png" centered at coord; add label 10px below icon,
  font HyliaSerifBeta-Regular.otf at 12pt, dark green, white stroke.
- rivers: add label at coord, font 14pt, blue, white stroke.
- borders (nations): draw interpolated line (Catmull-Rom), width 5px,
  color from JSON but force alpha=70%.

Options:
- --scale to downscale output (e.g., 0.5 for 50%).
- --format png|jpg (default: jpg).
- --quality JPEG quality (default: 90).
- --tile-size to export tiles (keeps full res), e.g., 4096 to split into 4K tiles.
"""

import argparse
import json
import math
import os
import re
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------- Helpers ----------

def pt_to_px(points: float, dpi: float = 96.0) -> int:
    """Convert typographic points (1/72 inch) to pixels at given DPI."""
    return int(round(points * dpi / 72.0))

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_rgba_force_70a(rgba_str: str) -> Tuple[int, int, int, int]:
    """
    Parse 'rgba(r,g,b,a)' but enforce alpha=70%.
    Falls back to red if parsing fails.
    """
    m = re.match(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)$", rgba_str, re.I)
    if not m:
        return (255, 0, 0, int(0.75 * 255))
    r, g, b, = m.groups()
    return (int(r), int(g), int(b), int(0.75 * 255))

def catmull_rom_spline(points: List[Tuple[float, float]], samples_per_seg: int = 12, closed: bool = False) -> List[Tuple[float, float]]:
    """
    Generate a smooth polyline through given points using Catmull-Rom spline.
    Returns a list of sampled points.
    """
    if len(points) < 2:
        return points[:]
    pts = points[:]
    if closed:
        pts = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        pts = [pts[0]] + pts + [pts[-1]]

    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(samples_per_seg):
            t = j / float(samples_per_seg)
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2*p1[0]) + (-p0[0] + p2[0]) * t + (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 + (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3)
            y = 0.5 * ((2*p1[1]) + (-p0[1] + p2[1]) * t + (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 + (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out

def alpha_composite_center(base_rgba: Image.Image, icon_rgba: Image.Image, center_xy: Tuple[float, float]) -> None:
    x, y = center_xy
    w, h = icon_rgba.size
    tl = (int(round(x - w / 2)), int(round(y - h / 2)))
    base_rgba.alpha_composite(icon_rgba, dest=tl)

def ensure_rgba(im: Image.Image) -> Image.Image:
    return im.convert("RGBA") if im.mode != "RGBA" else im

def save_image(im: Image.Image, out_path: str, fmt: str, quality: int) -> None:
    if fmt.lower() == "png":
        im.save(out_path, "PNG")
    else:
        # Convert to RGB for JPEG
        im_rgb = im.convert("RGB")
        im_rgb.save(out_path, "JPEG", quality=quality, subsampling=0, optimize=False)

def export_tiles(im: Image.Image, tile_size: int, out_dir: str, base_name: str, fmt: str, quality: int) -> None:
    os.makedirs(out_dir, exist_ok=True)
    W, H = im.size
    tx = math.ceil(W / tile_size)
    ty = math.ceil(H / tile_size)
    for iy in range(ty):
        for ix in range(tx):
            left   = ix * tile_size
            upper  = iy * tile_size
            right  = min(left + tile_size, W)
            lower  = min(upper + tile_size, H)
            tile = im.crop((left, upper, right, lower))
            tile_name = f"{base_name}_x{ix:02d}_y{iy:02d}.{fmt.lower()}"
            tile_path = os.path.join(out_dir, tile_name)
            save_image(tile, tile_path, fmt, quality)

# ---------- Main processing ----------

def main():
    ap = argparse.ArgumentParser(description="Annotate a large map with POIs and nation borders.")
    ap.add_argument("--assets-dir", default=".", help="Directory containing map.jpg, font OTF, icons, and poi.json (default: current dir).")
    ap.add_argument("--map", default="map.jpg", help="Map image filename (default: map.jpg).")
    ap.add_argument("--font", default="HyliaSerifBeta-Regular.otf", help="Font filename (default: HyliaSerifBeta-Regular.otf).")
    ap.add_argument("--portal-icon", default="portal_stone.png", help="Portal stone icon filename.")
    ap.add_argument("--stedding-icon", default="stedding.png", help="Stedding icon filename.")
    ap.add_argument("--json", default="poi.json", help="POI JSON filename.")
    ap.add_argument("--out", default="map_annotated", help="Output basename without extension (default: map_annotated).")
    ap.add_argument("--format", choices=["jpg", "png"], default="jpg", help="Output format (default: jpg).")
    ap.add_argument("--quality", type=int, default=90, help="JPEG quality if --format=jpg (default: 90).")
    ap.add_argument("--scale", type=float, default=1.0, help="Optional output downscale factor (e.g., 0.5).")
    ap.add_argument("--tile-size", type=int, default=0, help="Optional tile/export size (e.g., 4096). 0 disables tiling.")
    ap.add_argument("--nation-borders", type=bool, default=False, help="Add nation borders (default: False).")
    ap.add_argument("--spline-samples", type=int, default=10, help="Samples per segment for border smoothing (default: 10).")
    ap.add_argument("--aa-scale", type=int, default=1, help="Supersampling scale for borders (1=off, 2 or 3 for smoother lines).")
    args = ap.parse_args()

    assets = args.assets_dir
    map_path = os.path.join(assets, args.map)
    font_path = os.path.join(assets, args.font)
    portal_icon_path = os.path.join(assets, args.portal_icon)
    stedding_icon_path = os.path.join(assets, args.stedding_icon)
    json_path = os.path.join(assets, args.json)

    # Load assets
    base = Image.open(map_path)
    # Use image DPI if present; otherwise assume 96
    dpi = 96.0
    if "dpi" in base.info and isinstance(base.info["dpi"], tuple) and len(base.info["dpi"]) >= 1:
        try:
            dpi = float(base.info["dpi"][0])
        except Exception:
            pass

    im = ensure_rgba(base)
    draw = ImageDraw.Draw(im, "RGBA")

    icon_portal = Image.open(portal_icon_path).convert("RGBA")
    icon_stedding = Image.open(stedding_icon_path).convert("RGBA")

    data = load_json(json_path)

    # Colors & fonts (convert points to pixels at detected DPI)
    DARK_GREEN = (0, 100, 0)
    BLUE = (0, 90, 200)
    WHITE = (255, 255, 255)

    font_stedding = ImageFont.truetype(font_path, size=pt_to_px(14, dpi))
    font_river = ImageFont.truetype(font_path, size=pt_to_px(14, dpi))

    # 1) nation borders
    if args.nation_borders:
      # Anti-aliased nation borders via supersampling
      AA = max(1, args.aa_scale)
      W, H = im.size
      layer = Image.new("RGBA", (W * AA, H * AA), (0, 0, 0, 0))
      ldraw = ImageDraw.Draw(layer, "RGBA")

      for entry in data.get("nations", []):
          border = entry.get("border", [])
          if not border or len(border) < 2:
              continue
          # Scale points to AA space (and to pre-scale 'scale')
          scale = 1
          pts = [(float(px) * scale * AA, float(py) * scale * AA) for (px, py) in border]
          color = parse_rgba_force_70a(entry.get("color", "rgba(255,0,0,1)"))

          # Increase samples proportionally to AA for extra smoothness
          smooth = catmull_rom_spline(pts, samples_per_seg=max(6, args.spline_samples * AA), closed=False)

          # Draw thicker line in AA space, then we'll downscale
          ldraw.line(smooth, fill=color, width=5 * AA, joint="curve")

      # Downscale AA layer back to base size and composite
      layer = layer.resize((W, H), Image.Resampling.LANCZOS)
      im.alpha_composite(layer)

    # 2) portal_stones
    for entry in data.get("portal_stones", []):
        x, y = entry["coord"]
        alpha_composite_center(im, icon_portal, (float(x), float(y)))

    # 3) steddings + label 10px below icon bottom
    icon_w, icon_h = icon_stedding.size
    for entry in data.get("steddings", []):
        x, y = entry["coord"]
        label = entry.get("label", "")
        cx, cy = float(x), float(y)
        alpha_composite_center(im, icon_stedding, (cx, cy))
        ty = int(round(cy + icon_h / 2)) - 10
        # Center text on x
        bbox = draw.textbbox((0, 0), label, font=font_stedding, stroke_width=2)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = int(round(cx - tw / 2))
        draw.text((tx, ty), label, font=font_stedding, fill=DARK_GREEN, stroke_width=2, stroke_fill=WHITE)

    # 4) rivers labels
    for entry in data.get("rivers", []):
        x, y = entry["coord"]
        x += 50
        label = entry.get("label", "")
        bbox = draw.textbbox((0, 0), label, font=font_river, stroke_width=2)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = int(round(float(x) - tw / 2))
        ty = int(round(float(y) - th / 2))
        draw.text((tx, ty), label, font=font_river, fill=BLUE, stroke_width=2, stroke_fill=WHITE)

    # Save main output
    out_base = args.out
    out_ext = args.format.lower()
    out_path = f"{out_base}.{out_ext}"
    save_image(im, out_path, args.format, args.quality)
    print(f"[OK] Saved: {out_path} ({im.width}x{im.height})")

    # Optional tiling (exports from the final image)
    if args.tile_size and args.tile_size > 0:
        tiles_dir = f"{out_base}_tiles_{args.tile_size}"
        export_tiles(im, args.tile_size, tiles_dir, out_base, args.format, args.quality)
        print(f"[OK] Exported tiles to: {tiles_dir}")

if __name__ == "__main__":
    main()
