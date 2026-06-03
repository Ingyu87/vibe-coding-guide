from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


def slugify(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r'[\\/:*?"<>|]+', "_", stem)
    stem = re.sub(r"\s+", "_", stem).strip("_")
    return stem[:120]


def find_source_dir(root: Path) -> Path:
    for item in root.iterdir():
        if item.is_dir() and str(item).startswith("02_"):
            return item
    raise FileNotFoundError("02_ source directory not found")


def write_image(image, out_path: Path) -> bool:
    try:
        data = image.data
        out_path.write_bytes(data)
        return True
    except Exception:
        return False


def main() -> None:
    root = Path(".")
    source_dir = find_source_dir(root)
    out_root = root / "02_출처_MD" / "_empty_page_images"
    out_root.mkdir(parents=True, exist_ok=True)

    index_lines = [
        "# 빈 텍스트 페이지 이미지 추출 인덱스",
        "",
        "PDF 텍스트 추출에서 빈 페이지로 잡힌 페이지의 내장 이미지를 추출했다.",
        "이 파일들은 OCR 또는 이미지 확인 기반 보강에 사용한다.",
        "",
        "| PDF | 빈 페이지 | 추출 이미지 수 | 출력 폴더 |",
        "|---|---:|---:|---|",
    ]

    for pdf in sorted(source_dir.glob("*.pdf"), key=lambda p: p.name):
        reader = PdfReader(str(pdf))
        pdf_slug = slugify(pdf.name)
        pdf_out_dir = out_root / pdf_slug
        pdf_out_dir.mkdir(exist_ok=True)
        empty_pages: list[int] = []
        extracted = 0
        detail_lines = [
            f"# {pdf.stem} - 빈 페이지 이미지 보강",
            "",
            f"- 원본 PDF: `02_출처/{pdf.name}`",
            "- 목적: 텍스트 추출이 비어 있는 페이지를 이미지로 확인하기 위한 보강 자료",
            "",
            "## 추출 결과",
            "",
        ]

        for page_no, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                continue
            empty_pages.append(page_no)
            try:
                images = list(page.images)
            except Exception as exc:
                detail_lines.append(f"### p.{page_no}")
                detail_lines.append("")
                detail_lines.append(f"- 이미지 목록 조회 실패: `{exc!r}`")
                detail_lines.append("")
                continue

            detail_lines.append(f"### p.{page_no}")
            detail_lines.append("")
            if not images:
                detail_lines.append("- 추출 가능한 내장 이미지 없음")
                detail_lines.append("")
                continue

            for image_idx, image in enumerate(images, start=1):
                ext = Path(getattr(image, "name", "")).suffix.lower() or ".bin"
                if ext not in [".png", ".jpg", ".jpeg", ".jp2", ".bmp", ".tif", ".tiff"]:
                    ext = ".bin"
                out_name = f"p{page_no:03d}_img{image_idx:02d}{ext}"
                out_path = pdf_out_dir / out_name
                ok = write_image(image, out_path)
                if ok:
                    extracted += 1
                    detail_lines.append(f"- 이미지 {image_idx}: `./_empty_page_images/{pdf_slug}/{out_name}`")
                else:
                    detail_lines.append(f"- 이미지 {image_idx}: 추출 실패")
            detail_lines.append("")

        detail_lines.append("## 이미지 확인 메모")
        detail_lines.append("")
        detail_lines.append("- 아직 수동 확인 전이다.")
        detail_lines.append("- 확인 후 원본 Markdown 파일의 해당 페이지 아래에 보강 요약을 추가한다.")
        detail_lines.append("")

        if empty_pages:
            (out_root / f"{pdf_slug}_보강.md").write_text("\n".join(detail_lines), encoding="utf-8")
            index_lines.append(
                f"| `{pdf.name}` | {', '.join(map(str, empty_pages))} | {extracted} | `02_출처_MD/_empty_page_images/{pdf_slug}` |"
            )

    (out_root / "README.md").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"image extraction index={out_root / 'README.md'}")


if __name__ == "__main__":
    main()
