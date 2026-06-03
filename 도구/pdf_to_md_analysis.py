from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from pathlib import Path

try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader


KEYWORDS = [
    "AI",
    "생성형 AI",
    "바이브",
    "바이브 코딩",
    "바이브코딩",
    "교사",
    "학생",
    "개인정보",
    "성취기준",
    "수업",
    "평가",
    "피드백",
    "챗봇",
    "웹앱",
    "해커톤",
    "디버깅",
    "배포",
    "운영",
    "윤리",
    "보안",
    "심의",
    "학교운영위원회",
    "학운위",
    "도구",
    "안전",
    "투명성",
    "주도성",
]


PROFILE_BY_NAME = {
    "해커톤 사례집": {
        "role": "교사 개발자 사례와 현장 언어를 제공하는 사례 기반 자료",
        "use": "프롤로그, Part 1 0장, Part 4 나눔·성장 로드맵에서 현장 장면과 사례 언어로 활용한다.",
        "cautions": "개별 사례를 모든 학교의 일반 원칙처럼 단정하지 않는다.",
    },
    "정재환": {
        "role": "교사 개발자 프로세스의 기획·설계·개발·배포·운영 흐름 자료",
        "use": "Part 2 수업 장면 구체화, Part 3 개발 고려사항, Part 4 운영 기준에 활용한다.",
        "cautions": "개발 절차 설명이 교육적 판단보다 앞서지 않도록 재구성한다.",
    },
    "심의 가이드": {
        "role": "학습지원 소프트웨어 선정, 개인정보, 학운위 심의 기준 자료",
        "use": "Part 2 안전·개인정보, 배포·공유, 부록 심의 체크리스트에 직접 활용한다.",
        "cautions": "법률 자문처럼 쓰지 않고 학교 현장에서 확인할 기준으로 설명한다.",
    },
    "디버깅_강의": {
        "role": "AI와 함께 오류를 분석하고 수정하는 디버깅 절차 자료",
        "use": "Part 3 개발 고려사항, Part 4 수정·운영, 부록 디버깅 템플릿에 활용한다.",
        "cautions": "디버깅 기술 팁을 수업 설계 기준보다 앞세우지 않는다.",
    },
    "바이브코딩을 부탁해": {
        "role": "교사 개발자 바이브코딩의 의미와 윤리 원칙, 챗봇 예시 자료",
        "use": "프롤로그, Part 1 0장, Part 3 AI 챗봇, 개인정보·상담 위험 박스에 활용한다.",
        "cautions": "상담 챗봇 예시는 저장·공유·보호 안내를 반드시 함께 다룬다.",
    },
    "AI 에듀테크": {
        "role": "AI·에듀테크 공교육 도입과 활용의 가치·원칙 자료",
        "use": "프롤로그, Part 1, Part 2의 가치 기준으로 활용한다.",
        "cautions": "가치 선언을 그대로 옮기기보다 판단 질문과 체크리스트로 바꾼다.",
    },
    "세션2": {
        "role": "웹앱 기초, 저장 구조, 배포, 테스트·수정 흐름 자료",
        "use": "Part 2 배포·공유, 설치형·웹형·디벗, Part 3 개발 고려사항에 활용한다.",
        "cautions": "구현 순서를 따라 하기 절차로만 제시하지 않고 수업 맥락과 연결한다.",
    },
    "해커톤 입문_4번째_디버깅": {
        "role": "오류 메시지, 전체 코드, 원하는 결과를 묶어 전달하는 디버깅 공식 자료",
        "use": "Part 4 운영·수정과 부록 오류 대응 템플릿에 활용한다.",
        "cautions": "AI에게 모든 수정을 맡기지 않고 교사 확인 지점을 남긴다.",
    },
}


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def profile_for(filename: str) -> dict[str, str]:
    for key, profile in PROFILE_BY_NAME.items():
        if key in filename:
            return profile
    return {
        "role": "원고 집필 참고 자료",
        "use": "관련 장의 문제의식, 예시 장면, 체크리스트 후보로 활용한다.",
        "cautions": "원문을 길게 옮기지 않고 자료집 문체로 재구성한다.",
    }


def keyword_counts(text: str) -> Counter:
    counts = Counter()
    for keyword in KEYWORDS:
        count = text.count(keyword)
        if count:
            counts[keyword] = count
    return counts


def page_heading_candidates(page_text: str) -> list[str]:
    lines = [line.strip() for line in page_text.splitlines()]
    candidates: list[str] = []
    for line in lines:
        if not line:
            continue
        if len(line) > 90:
            continue
        if re.search(r"(PART|Part|목차|CONTENTS|가이드|기준|원칙|절차|사례|디버깅|배포|운영|심의|개인정보|챗봇|웹앱|해커톤)", line):
            candidates.append(line)
        elif re.match(r"^(\d+[\.\- ]|[ⅠⅡⅢⅣⅤⅥ]+\.|Q\d+\.|FAQ|PART)", line):
            candidates.append(line)
        if len(candidates) >= 5:
            break
    return candidates


def analyze_pdf(pdf_path: Path, out_dir: Path, force: bool = False) -> dict[str, object]:
    out_path = out_dir / f"{slugify(pdf_path.name)}.md"
    if out_path.exists() and not force:
        existing = out_path.read_text(encoding="utf-8", errors="replace")
        pages_match = re.search(r"- 페이지 수: ([^\n]+)", existing)
        empty_match = re.search(r"- 빈 텍스트 페이지 수: ([^\n]+)", existing)
        top_keywords: list[tuple[str, int]] = []
        for keyword, count in re.findall(r"\| ([^|\n]+) \| (\d+) \|", existing):
            if keyword != "---":
                top_keywords.append((keyword.strip(), int(count)))
            if len(top_keywords) >= 8:
                break
        return {
            "name": pdf_path.name,
            "out": out_path.name,
            "pages": pages_match.group(1).strip() if pages_match else "?",
            "empty_pages": empty_match.group(1).strip() if empty_match else "?",
            "top_keywords": top_keywords,
            "role": profile_for(pdf_path.name)["role"],
            "skipped": True,
        }

    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, object]] = []
    all_text_parts: list[str] = []
    empty_pages = 0

    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = clean_text(page.extract_text() or "")
        except Exception as exc:
            text = f"[텍스트 추출 오류: {exc!r}]"
        if not text:
            empty_pages += 1
        all_text_parts.append(text)
        pages.append(
            {
                "page": idx,
                "chars": len(text),
                "headings": page_heading_candidates(text),
                "text": text,
            }
        )

    all_text = "\n\n".join(all_text_parts)
    counts = keyword_counts(all_text)
    profile = profile_for(pdf_path.name)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []
    lines.append(f"# {pdf_path.stem}")
    lines.append("")
    lines.append("## 변환 정보")
    lines.append("")
    lines.append(f"- 원본 파일: `02_출처/{pdf_path.name}`")
    lines.append(f"- 페이지 수: {len(reader.pages)}")
    lines.append(f"- 빈 텍스트 페이지 수: {empty_pages}")
    lines.append(f"- 변환 일시: {now}")
    lines.append("- 변환 방식: PDF 텍스트 추출 기반 Markdown 변환")
    lines.append("")
    lines.append("## 상세 분석")
    lines.append("")
    lines.append(f"- 자료 성격: {profile['role']}")
    lines.append(f"- 집필 활용: {profile['use']}")
    lines.append(f"- 사용 주의: {profile['cautions']}")
    lines.append("")
    lines.append("## 주요 키워드")
    lines.append("")
    if counts:
        lines.append("| 키워드 | 빈도 |")
        lines.append("|---|---:|")
        for keyword, count in counts.most_common():
            lines.append(f"| {keyword} | {count} |")
    else:
        lines.append("- 주요 키워드가 충분히 추출되지 않았다. 이미지 중심 PDF일 가능성이 있다.")
    lines.append("")
    lines.append("## 페이지별 제목 후보")
    lines.append("")
    any_heading = False
    for page in pages:
        headings = page["headings"]
        if not headings:
            continue
        any_heading = True
        lines.append(f"### p.{page['page']}")
        for heading in headings:
            lines.append(f"- {heading}")
        lines.append("")
    if not any_heading:
        lines.append("- 제목 후보가 충분히 추출되지 않았다.")
        lines.append("")
    lines.append("## 원고 반영 후보")
    lines.append("")
    lines.append("- 문제의식: 이 자료가 제시하는 현장 문제나 제도 기준을 장의 도입부에 반영한다.")
    lines.append("- 예시 장면: 실제 수업, 해커톤, 배포, 디버깅, 심의 장면은 사례형 문단으로 재구성한다.")
    lines.append("- 핵심 위험: 개인정보, 학생 사고 대체, 책임 불명확, 오류 방치, 평가 공정성 문제를 박스로 바꾼다.")
    lines.append("- 체크리스트: 자료의 절차와 기준은 `~있는가?`, `~확인했는가?` 형태의 판단 질문으로 바꾼다.")
    lines.append("")
    lines.append("## 페이지별 추출 텍스트")
    lines.append("")
    for page in pages:
        lines.append(f"### p.{page['page']}")
        lines.append("")
        text = page["text"] or "[텍스트 없음 또는 이미지 중심 페이지]"
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "name": pdf_path.name,
        "out": out_path.name,
        "pages": len(reader.pages),
        "empty_pages": empty_pages,
        "top_keywords": counts.most_common(8),
        "role": profile["role"],
        "skipped": False,
    }


def main() -> None:
    root = Path(".")
    source_dir = find_source_dir(root)
    out_dir = root / "02_출처_MD"
    out_dir.mkdir(exist_ok=True)

    pdfs = sorted(source_dir.glob("*.pdf"), key=lambda p: p.name)
    summaries = [analyze_pdf(pdf, out_dir) for pdf in pdfs]

    index_lines: list[str] = []
    index_lines.append("# PDF 출처 Markdown 변환 인덱스")
    index_lines.append("")
    index_lines.append("## 변환 개요")
    index_lines.append("")
    index_lines.append(f"- PDF 수: {len(summaries)}")
    index_lines.append(f"- 출력 폴더: `02_출처_MD`")
    index_lines.append("- 각 파일은 상세 분석, 주요 키워드, 페이지별 제목 후보, 페이지별 추출 텍스트를 포함한다.")
    index_lines.append("")
    index_lines.append("## 파일 목록")
    index_lines.append("")
    index_lines.append("| 원본 PDF | Markdown | 페이지 | 빈 텍스트 페이지 | 자료 성격 |")
    index_lines.append("|---|---|---:|---:|---|")
    for item in summaries:
        status = "기존 파일 유지" if item.get("skipped") else "신규 변환"
        index_lines.append(
            f"| `{item['name']}` | [{item['out']}](./{item['out']}) | {item['pages']} | {item['empty_pages']} | {item['role']} ({status}) |"
        )
    index_lines.append("")
    index_lines.append("## 키워드 요약")
    index_lines.append("")
    for item in summaries:
        index_lines.append(f"### {item['name']}")
        if item["top_keywords"]:
            index_lines.append(
                ", ".join([f"{keyword} {count}" for keyword, count in item["top_keywords"]])
            )
        else:
            index_lines.append("키워드 추출 부족")
        index_lines.append("")

    (out_dir / "README.md").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"converted={len(summaries)} out={out_dir}")


if __name__ == "__main__":
    main()
