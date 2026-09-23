"""
Markdown Report to PDF Converter
마크다운 리포트를 PDF로 변환하는 스크립트

reports/issues/ 폴더의 모든 .md 리포트를 PDF로 변환하여
reports/issues/pdf/ 폴더에 저장합니다.
"""

import sys
import markdown
from pathlib import Path
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# Windows 콘솔의 기본 인코딩(cp949)이 이모지/특수문자를 표현하지 못해
# UnicodeEncodeError가 나는 것을 방지하기 위해 UTF-8로 강제 설정합니다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPORTS_DIR = Path("reports/issues")
PDF_OUTPUT_DIR = Path("reports/issues/pdf")

# 프로젝트에 동봉된 한글 폰트 파일 (Windows에서는 "맑은 고딕" 등 시스템 폰트를
# 이름으로 찾지 못해 weasyprint가 Helvetica로 대체해버리는 문제가 있었습니다.
# -> OS 폰트 검색에 의존하지 않도록 폰트 파일을 프로젝트에 직접 포함시키고
#    @font-face로 파일 경로를 명시해서 불러옵니다.)
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_REGULAR = FONT_DIR / "NotoSansKR-Regular.otf"
FONT_BOLD = FONT_DIR / "NotoSansKR-Bold.otf"

if not FONT_REGULAR.exists() or not FONT_BOLD.exists():
    raise FileNotFoundError(
        f"한글 폰트 파일을 찾을 수 없습니다: {FONT_DIR}\n"
        "assets/fonts/NotoSansKR-Regular.otf, NotoSansKR-Bold.otf 가 프로젝트에 포함되어 있는지 확인하세요."
    )

# PDF 스타일 (한글 폰트 포함)
# @font-face 블록만 f-string으로 만들어 폰트 파일 경로를 주입하고,
# 나머지 CSS 규칙은 중괄호를 이스케이프할 필요 없이 일반 문자열로 둡니다.
_FONT_FACE_CSS = f"""
@font-face {{
    font-family: "NotoSansKR";
    src: url("{FONT_REGULAR.as_uri()}");
    font-weight: normal;
}}

@font-face {{
    font-family: "NotoSansKR";
    src: url("{FONT_BOLD.as_uri()}");
    font-weight: bold;
}}
"""

PDF_CSS = _FONT_FACE_CSS + """
@page {
    size: A4;
    margin: 2cm 1.8cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9px;
        color: #888;
    }
}

body {
    font-family: "NotoSansKR", sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #222;
}

h1 {
    font-size: 20pt;
    color: #0f3460;
    border-bottom: 3px solid #0099ff;
    padding-bottom: 8px;
    margin-top: 0;
}

h2 {
    font-size: 15pt;
    color: #0f3460;
    border-bottom: 1px solid #ccc;
    padding-bottom: 4px;
    margin-top: 24px;
}

h3 {
    font-size: 12.5pt;
    color: #16213e;
    margin-top: 18px;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 9.5pt;
}

th, td {
    border: 1px solid #ccc;
    padding: 6px 10px;
    text-align: left;
}

th {
    background-color: #0f3460;
    color: white;
}

tr:nth-child(even) {
    background-color: #f5f7fa;
}

code {
    background-color: #f0f0f0;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 9pt;
}

blockquote {
    border-left: 4px solid #0099ff;
    margin: 10px 0;
    padding: 6px 16px;
    background-color: #f5f9ff;
    color: #444;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}

ul, ol {
    margin: 8px 0;
    padding-left: 24px;
}

li {
    margin: 4px 0;
}

strong {
    color: #0f3460;
}
"""


# weasyprint는 font_config(FontConfiguration)를 명시적으로 넘겨주지 않으면
# CSS의 @font-face 규칙을 파싱만 하고 실제로는 등록/사용하지 않습니다.
# (이게 바로 "맑은 고딕"/번들 폰트를 지정해도 Windows에서 Helvetica로
#  대체되어 한글이 통째로 안 보이던 문제의 진짜 원인이었습니다.)
# -> font_config를 한 번 만들어서 CSS 파싱과 PDF 생성 양쪽에 동일하게 넘겨줍니다.
_FONT_CONFIG = FontConfiguration()

# CSS는 한 번만 파싱해서 재사용합니다 (파일마다 새로 파싱하면 눈에 띄게 느려집니다)
_PDF_STYLESHEET = CSS(string=PDF_CSS, font_config=_FONT_CONFIG)


def convert_md_to_pdf(md_file: Path, output_dir: Path):
    """단일 마크다운 파일을 PDF로 변환"""
    md_text = md_file.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "nl2br"]
    )

    html_full = f"""
    <html>
    <head><meta charset="utf-8"></head>
    <body>{html_body}</body>
    </html>
    """

    pdf_file = output_dir / (md_file.stem + ".pdf")
    HTML(string=html_full).write_pdf(
        pdf_file,
        stylesheets=[_PDF_STYLESHEET],
        font_config=_FONT_CONFIG,
    )

    return pdf_file


def main():
    print("\n" + "=" * 60)
    print("📄 Converting Markdown Reports to PDF...")
    print("=" * 60)

    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(REPORTS_DIR.glob("*.md"))

    if not md_files:
        print(f"⚠️  변환할 .md 파일이 없습니다: {REPORTS_DIR}")
        return []

    converted = []
    for md_file in md_files:
        try:
            pdf_file = convert_md_to_pdf(md_file, PDF_OUTPUT_DIR)
            size_kb = pdf_file.stat().st_size / 1024
            print(f"  ✅ {md_file.name} → {pdf_file.name} ({size_kb:.0f} KB)")
            converted.append(str(pdf_file))
        except Exception as e:
            print(f"  ❌ {md_file.name} 변환 실패: {e}")

    print("\n" + "=" * 60)
    print(f"✅ 총 {len(converted)}개 PDF 생성 완료!")
    print(f"📂 위치: {PDF_OUTPUT_DIR}")
    print("=" * 60)

    return converted


if __name__ == "__main__":
    main()
