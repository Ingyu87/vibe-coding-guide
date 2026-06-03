from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_sheet(folder: Path, out_path: Path) -> bool:
    image_paths = sorted(
        [p for p in folder.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    )
    if not image_paths:
        return False

    thumb_w, thumb_h = 320, 180
    label_h = 28
    pad = 12
    cols = 3
    rows = (len(image_paths) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for idx, path in enumerate(image_paths):
        row, col = divmod(idx, cols)
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((thumb_w, thumb_h))
            bg = Image.new("RGB", (thumb_w, thumb_h), (245, 245, 245))
            bx = x + (thumb_w - img.width) // 2
            by = y + (thumb_h - img.height) // 2
            sheet.paste(bg, (x, y))
            sheet.paste(img, (bx, by))
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(190, 190, 190))
            draw.text((x, y + thumb_h + 6), path.name[:45], fill=(0, 0, 0), font=font)
        except Exception as exc:
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(220, 80, 80))
            draw.text((x + 6, y + 6), f"error: {exc!r}"[:60], fill=(180, 0, 0), font=font)

    sheet.save(out_path, quality=92)
    return True


def main() -> None:
    root = Path("02_출처_MD") / "_empty_page_images"
    sheets_dir = root / "_contact_sheets"
    sheets_dir.mkdir(exist_ok=True)
    lines = ["# 빈 페이지 이미지 Contact Sheets", ""]
    for folder in sorted([p for p in root.iterdir() if p.is_dir() and p.name != "_contact_sheets"]):
        out = sheets_dir / f"{folder.name}.jpg"
        if make_sheet(folder, out):
            lines.append(f"- [{folder.name}](./_contact_sheets/{out.name})")
    (root / "CONTACT_SHEETS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"contact sheets written={sheets_dir}")


if __name__ == "__main__":
    main()
