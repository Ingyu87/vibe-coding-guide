from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

KEYWORDS = [
    "AI",
    "바이브",
    "바이브코딩",
    "교사",
    "학생",
    "개인정보",
    "수업",
    "평가",
    "피드백",
    "챗봇",
    "웹앱",
    "배포",
    "운영",
    "윤리",
    "보안",
    "디버깅",
    "프롬프트",
    "성취기준",
]


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


def natural_slide_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def extract_text_from_xml(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    texts = []
    for node in root.findall(".//a:t", NS):
        if node.text and node.text.strip():
            texts.append(node.text.strip())
    return texts


def parse_rels(rels_bytes: bytes) -> dict[str, str]:
    root = ET.fromstring(rels_bytes)
    rels = {}
    for rel in root.findall(".//rel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")
        if rid:
            rels[rid] = target
    return rels


def image_refs_for_slide(xml_bytes: bytes, rels: dict[str, str]) -> list[str]:
    root = ET.fromstring(xml_bytes)
    refs = []
    for blip in root.findall(".//a:blip", NS):
        rid = blip.attrib.get(f"{{{NS['r']}}}embed")
        if not rid:
            continue
        target = rels.get(rid)
        if target and "media/" in target:
            refs.append("ppt/" + target.replace("../", ""))
    return refs


def make_contact_sheet(image_paths: list[Path], out_path: Path) -> bool:
    if not image_paths:
        return False
    thumb_w, thumb_h = 320, 180
    label_h, pad, cols = 28, 12, 3
    rows = (len(image_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * pad, rows * (thumb_h + label_h) + (rows + 1) * pad), "white")
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
            sheet.paste(bg, (x, y))
            sheet.paste(img, (x + (thumb_w - img.width) // 2, y + (thumb_h - img.height) // 2))
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(190, 190, 190))
            draw.text((x, y + thumb_h + 6), path.name[:45], fill=(0, 0, 0), font=font)
        except Exception as exc:
            draw.text((x + 6, y + 6), f"error: {exc!r}"[:60], fill=(180, 0, 0), font=font)
    sheet.save(out_path, quality=92)
    return True


def keyword_counts(text: str) -> list[tuple[str, int]]:
    counts = []
    for keyword in KEYWORDS:
        count = text.count(keyword)
        if count:
            counts.append((keyword, count))
    return sorted(counts, key=lambda x: x[1], reverse=True)


def analyze_pptx(pptx_path: Path, out_dir: Path) -> dict[str, object]:
    slug = slugify(pptx_path.name)
    image_dir = out_dir / "_pptx_images" / slug
    image_dir.mkdir(parents=True, exist_ok=True)

    slides = []
    extracted_images: list[Path] = []
    with zipfile.ZipFile(pptx_path) as z:
        names = z.namelist()
        slide_names = sorted([n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")], key=natural_slide_key)
        notes_names = {natural_slide_key(n): n for n in names if n.startswith("ppt/notesSlides/notesSlide") and n.endswith(".xml")}

        for slide_name in slide_names:
            slide_no = natural_slide_key(slide_name)
            xml = z.read(slide_name)
            texts = extract_text_from_xml(xml)
            rels_name = f"ppt/slides/_rels/slide{slide_no}.xml.rels"
            rels = parse_rels(z.read(rels_name)) if rels_name in names else {}
            image_refs = image_refs_for_slide(xml, rels)
            saved_images = []
            for idx, ref in enumerate(image_refs, start=1):
                if ref not in names:
                    continue
                ext = Path(ref).suffix.lower() or ".bin"
                out_name = f"slide{slide_no:03d}_img{idx:02d}{ext}"
                out_path = image_dir / out_name
                out_path.write_bytes(z.read(ref))
                saved_images.append(out_path)
                extracted_images.append(out_path)

            notes = []
            notes_name = notes_names.get(slide_no)
            if notes_name:
                notes = extract_text_from_xml(z.read(notes_name))

            slides.append({"no": slide_no, "texts": texts, "notes": notes, "images": saved_images})

    contact_dir = out_dir / "_pptx_images" / "_contact_sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)
    contact_path = contact_dir / f"{slug}.jpg"
    make_contact_sheet(extracted_images, contact_path)

    all_text = "\n".join(["\n".join(s["texts"] + s["notes"]) for s in slides])
    md_path = out_dir / f"{slug}.md"
    lines = [f"# {pptx_path.stem}", ""]
    lines += [
        "## 변환 정보",
        "",
        f"- 원본 파일: `02_출처/{pptx_path.name}`",
        f"- 슬라이드 수: {len(slides)}",
        f"- 추출 이미지 수: {len(extracted_images)}",
        "- 변환 방식: PPTX OOXML 텍스트·노트·이미지 추출 기반 Markdown 변환",
        "",
        "## 상세 분석",
        "",
        "- 자료 성격: PPTX 기반 강의·연수 자료",
        "- 집필 활용: 슬라이드 제목, 본문 문구, 포함 이미지를 바탕으로 원고의 개발 절차, 예시 장면, 체크리스트 후보를 보강한다.",
        "- 사용 주의: 슬라이드 이미지만 있고 텍스트가 없는 경우 contact sheet를 보고 이미지 확인 보강을 해야 한다.",
        "",
        "## 주요 키워드",
        "",
    ]
    counts = keyword_counts(all_text)
    if counts:
        lines += ["| 키워드 | 빈도 |", "|---|---:|"]
        for keyword, count in counts:
            lines.append(f"| {keyword} | {count} |")
    else:
        lines.append("- 텍스트 기반 키워드가 충분히 추출되지 않았다.")
    lines += [
        "",
        "## 이미지 확인 자료",
        "",
        f"- Contact sheet: `./_pptx_images/_contact_sheets/{contact_path.name}`",
        f"- 개별 이미지 폴더: `./_pptx_images/{slug}`",
        "",
        "## 슬라이드별 추출 내용",
        "",
    ]
    for slide in slides:
        lines.append(f"### Slide {slide['no']}")
        lines.append("")
        if slide["texts"]:
            lines.append("#### 텍스트")
            lines.append("")
            for text in slide["texts"]:
                lines.append(f"- {text}")
            lines.append("")
        else:
            lines.append("- 텍스트 없음. 이미지 확인 필요.")
            lines.append("")
        if slide["notes"]:
            lines.append("#### 노트")
            lines.append("")
            for note in slide["notes"]:
                lines.append(f"- {note}")
            lines.append("")
        if slide["images"]:
            lines.append("#### 포함 이미지")
            lines.append("")
            for img in slide["images"]:
                lines.append(f"- `./_pptx_images/{slug}/{img.name}`")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"name": pptx_path.name, "md": md_path.name, "slides": len(slides), "images": len(extracted_images)}


def main() -> None:
    root = Path(".")
    source_dir = find_source_dir(root)
    out_dir = root / "02_출처_MD"
    out_dir.mkdir(exist_ok=True)
    pptxs = sorted(source_dir.glob("*.pptx"), key=lambda p: p.name)
    results = [analyze_pptx(p, out_dir) for p in pptxs]
    index_path = out_dir / "PPTX_README.md"
    lines = ["# PPTX 출처 Markdown 변환 인덱스", ""]
    lines += ["| 원본 PPTX | Markdown | 슬라이드 | 추출 이미지 |", "|---|---|---:|---:|"]
    for result in results:
        lines.append(f"| `{result['name']}` | [{result['md']}](./{result['md']}) | {result['slides']} | {result['images']} |")
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"converted_pptx={len(results)}")


if __name__ == "__main__":
    main()
