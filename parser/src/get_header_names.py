import re
from docx import Document

HEADING1_RE = re.compile(r"^(heading|заголовок)\s*1$", re.IGNORECASE)

def is_section_heading(paragraph) -> bool:
    name = (paragraph.style.name or "").strip()
    return bool(HEADING1_RE.match(name)) and paragraph.text.strip() != ""

def split_by_sections(docx_path: str) -> list[dict]:
    doc = Document(docx_path)

    sections = []
    current = None

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue

        if is_section_heading(p):
            current = {"title": text, "content": []}
            sections.append(current)
        else:
            if current is not None:
                current["content"].append(text)

    for s in sections:
        s["content_text"] = "\n".join(s["content"])

    return sections

if __name__ == "__main__":
    sections = split_by_sections("../../input.docx")
    for s in sections:
        print("###", s["title"])
        # print(s["content_text"][:400], "...\n")