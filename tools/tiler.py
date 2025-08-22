from PIL import Image
import math
import os

def split_image(image_path: str, tile_size: str, output_dir: str = "www/tiles", output_prefix: str = "tile"):
    # Parse tile size string
    target_w, target_h = map(int, tile_size.lower().split("x"))

    # Open image
    img = Image.open(image_path)
    img_w, img_h = img.size

    # Calcola il numero di tile lungo ogni dimensione
    cols = math.ceil(img_w / target_w)
    rows = math.ceil(img_h / target_h)

    # Dimensione effettiva dei tile (adattata per coprire tutta l'immagine)
    tile_w = math.ceil(img_w / cols)
    tile_h = math.ceil(img_h / rows)

    print(f"Image size: {img_w}x{img_h}")
    print(f"Target tile: {target_w}x{target_h}")
    print(f"Tiles grid: {cols}x{rows} → {cols*rows} tiles")
    print(f"Final tile size: {tile_w}x{tile_h}")

    # Crea la directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)

    # Split in tiles
    for r in range(rows):
        for c in range(cols):
            left = c * tile_w
            upper = r * tile_h
            right = min((c+1) * tile_w, img_w)
            lower = min((r+1) * tile_h, img_h)

            tile = img.crop((left, upper, right, lower))

            # Salva come JPG con nome tile_X_Y.jpg
            tile.convert("RGB").save(
                os.path.join(output_dir, f"{output_prefix}_{r}_{c}.jpg"),
                "JPEG",
                quality=95
            )

# Esempio d'uso
if __name__ == "__main__":
    split_image("www/map.v1.jpg", "500x500")
