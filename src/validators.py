import json
import re
from typing import Any, Dict, List


def _issue(rule: str, message: str, severity: str = "error", page: int = None, bbox=None, details: Dict[str, Any] = None):
    out = {"rule": rule, "message": message, "severity": severity}
    if page is not None:
        out["page"] = page
    if bbox is not None:
        out["bbox"] = bbox
    if details is not None:
        out["details"] = details
    return out


def check_sections_presence_and_order(data: Dict) -> List[Dict]:
    """Наличие и порядок обязательных разделов (Введение, Назначение, Технические характеристики)."""
    required = ["введение", "назначение", "технические характеристики"]
    issues: List[Dict] = []
    sections = data.get("sections") or []
    titles = []
    for s in sections:
        if isinstance(s, dict):
            titles.append(s.get("title", "").strip().lower())
        else:
            titles.append(str(s).strip().lower())
    idx = 0
    for req in required:
        found = None
        for i in range(idx, len(titles)):
            if req in titles[i]:
                found = i
                break
        if found is None:
            issues.append(_issue("section_missing", f"Missing required section: {req}", "error"))
        else:
            if found < idx:
                issues.append(_issue("section_order", f"Section {req} is out of order", "warning"))
            idx = found + 1
    return issues


def check_section_numbering_format(data: Dict) -> List[Dict]:
    """Проверка формата нумерации разделов и вложенности (1, 1.1, 1.1.1)."""
    issues: List[Dict] = []
    sections = data.get("sections") or []
    pattern = re.compile(r"^\d+(?:\.\d+)*$")

    flattened: List[Dict] = []

    def _flatten(lst):
        for s in lst:
            if not isinstance(s, dict):
                continue
            flattened.append({"number": s.get("number"), "title": s.get("title")})
            children = s.get("children") or s.get("subsections") or []
            if children:
                _flatten(children)

    _flatten(sections)

    prev_parts: List[int] = []
    prev_num = None
    for item in flattened:
        num = item.get("number")
        title = item.get("title")
        if not num:
            continue
        if not pattern.match(str(num)):
            issues.append(_issue("section_number_format", f"Invalid section number format: {num}", "error", details={"title": title}))
            continue
        parts = [int(x) for x in str(num).split('.')]

        if prev_parts:
            # unexpected jump in depth (e.g. 1 -> 1.1.1 without intermediate)
            if len(parts) > len(prev_parts) + 1:
                issues.append(_issue("section_number_hierarchy", f"Unexpected jump in numbering: {num}", "warning", details={"title": title}))

            # same level but gap in sibling numbering (e.g. 2.1 -> 2.3)
            if len(parts) == len(prev_parts) and parts[:-1] == prev_parts[:-1]:
                if parts[-1] > prev_parts[-1] + 1:
                    issues.append(_issue("section_number_gap", f"Gap in numbering: {prev_num} -> {num}", "warning", details={"title": title}))

        prev_parts = parts
        prev_num = num

    return issues


def check_page_numbering_rules(data: Dict) -> List[Dict]:
    """Проверка сквозной нумерации страниц: последовательность и отсутствие дубликатов.

    Parser may provide `pages` as list of dicts with `number` key or as simple list of numbers.
    """
    issues: List[Dict] = []
    pages = data.get("pages") or []
    nums: List[int] = []
    for p in pages:
        if isinstance(p, dict):
            n = p.get("number")
        else:
            n = p
        try:
            nums.append(int(str(n).strip()))
        except Exception:
            continue
    if not nums:
        return issues
    seen = set()
    for n in nums:
        if n in seen:
            issues.append(_issue("duplicate_page_number", f"Duplicate page number {n}", "warning", page=n))
        seen.add(n)
    nums_sorted = sorted(nums)
    start = nums_sorted[0]
    for expected, actual in enumerate(nums_sorted, start=start):
        if expected != actual:
            issues.append(_issue("page_numbering_sequence", f"Page numbering sequence broken: expected {expected} got {actual}", "error", page=actual))
            break
    return issues


def check_tables_format(data: Dict) -> List[Dict]:
    """Оформление таблиц: подпись формата 'Таблица X.Y', наличие наименования и ссылок в тексте."""
    issues: List[Dict] = []
    tables = data.get("tables") or []
    cap_pattern = re.compile(r"^(Таблица|Table)\s+\d+(?:\.\d+)?", re.IGNORECASE)
    for t in tables:
        caption = t.get("caption")
        page = t.get("page")
        if not caption:
            issues.append(_issue("table_caption_missing", "Table caption missing", "error", page=page))
            continue
        if not cap_pattern.match(caption):
            issues.append(_issue("table_caption_format", f"Table caption has invalid format: {caption}", "warning", page=page))
        # check references in text if parser provides 'references'
        refs = t.get("references")
        if not refs:
            issues.append(_issue("table_no_refs", "Table is not referenced in the document text", "warning", page=page))
    return issues


def check_figures_format(data: Dict) -> List[Dict]:
    """Проверка оформления рисунков: нумерация (Рисунок X.Y), подпись под рисунком, ссылки в тексте"""
    issues = []
    figs = data.get("figures") or []
    fig_pattern = re.compile(r"^(Рисунок|Figure)\s+\d+(?:\.\d+)?", re.IGNORECASE)
    for f in figs:
        caption = f.get("caption")
        page = f.get("page")
        if not caption:
            issues.append(_issue("figure_caption_missing", "Figure caption missing", "warning", page=page))
            continue
        if not fig_pattern.match(caption):
            issues.append(_issue("figure_caption_format", f"Figure caption has invalid format: {caption}", "warning", page=page))
        # caption placement: expect 'below' or 'under'
        pos = f.get("caption_position")
        if pos and pos.lower() not in ("below", "under"):
            issues.append(_issue("figure_caption_position", f"Figure caption position unexpected: {pos}", "warning", page=page))
        refs = f.get("references")
        if not refs:
            issues.append(_issue("figure_no_refs", "Figure is not referenced in the document text", "warning", page=page))
    return issues


def check_formulas_format(data: Dict) -> List[Dict]:
    """Распознавание формул и контроль корректности нумерации в круглых скобках у правого поля листа"""
    issues = []
    forms = data.get("formulas") or []
    # expect numbering like (1.5) or (1)
    num_pattern = re.compile(r"^\(?\d+(?:\.\d+)?\)?$")
    for f in forms:
        number = f.get("number")
        page = f.get("page")
        if number is None:
            issues.append(_issue("formula_number_missing", "Formula numbering missing", "warning", page=page))
        else:
            if not num_pattern.match(str(number)):
                issues.append(_issue("formula_number_format", f"Formula number has invalid format: {number}", "warning", page=page))
        # check placement if parser provides 'position'
        pos = f.get("position")
        if pos and pos.get("h_align") and pos.get("h_align").lower() not in ("right", "centre", "center"):
            issues.append(_issue("formula_position", f"Formula position unexpected: {pos}", "warning", page=page))
    return issues


def check_appendices_format(data: Dict) -> List[Dict]:
    """Проверка оформления приложений: заголовки буквами кириллицы (ПРИЛОЖЕНИЕ А), начало с новой страницы и ссылки в тексте"""
    issues = []
    apps = data.get("appendices") or []
    app_pattern = re.compile(r"^\s*ПРИЛОЖЕНИЕ\s+[А-ЯЁ]", re.IGNORECASE)
    for a in apps:
        heading = a.get("heading") or ""
        page = a.get("start_page") or a.get("page")
        if not heading:
            issues.append(_issue("appendix_heading_missing", "Appendix heading missing", "warning", page=page))
            continue
        if not app_pattern.match(heading.upper()):
            issues.append(_issue("appendix_heading_format", f"Appendix heading should start with Cyrillic letter: {heading}", "warning", page=page))
        # new page start check
        if a.get("starts_on_same_page_as_previous"):
            issues.append(_issue("appendix_page_start", "Appendix must start on a new page", "error", page=page))
        refs = a.get("references")
        if not refs:
            issues.append(_issue("appendix_no_refs", "Appendix is not referenced in the document text", "warning", page=page))
    return issues


def run_all_checks(data: Dict) -> Dict:
    # Map of the seven required checks
    checks_def = [
        (check_sections_presence_and_order, "section_presence", "Presence and order of required sections"),
        (check_section_numbering_format, "section_numbering", "Section numbering format and hierarchy"),
        (check_page_numbering_rules, "page_numbering", "Page numbering sequence and duplicates"),
        (check_tables_format, "table_captions", "Table captions and references"),
        (check_figures_format, "figure_captions", "Figure captions and references"),
        (check_formulas_format, "formulas", "Formulas numbering and placement"),
        (check_appendices_format, "appendices", "Appendices headings and references"),
    ]

    checks_out: List[Dict] = []
    total = len(checks_def)
    passed = 0
    failed = 0

    for func, cid, default_msg in checks_def:
        try:
            issues = func(data) or []
        except Exception as e:
            issues = [{"rule": "internal_error", "message": f"Checker raised exception: {e}", "severity": "error"}]

        if not issues:
            status = "PASSED"
            message = {
                "section_presence": "Required sections present and in correct order.",
                "section_numbering": "Нумерация разделов соответствует ГОСТ 2.105.",
                "page_numbering": "Нумерация страниц последовательна.",
                "table_captions": "Таблицы оформлены корректно.",
                "figure_captions": "Рисунки оформлены корректно.",
                "formulas": "Формулы оформлены корректно.",
                "appendices": "Приложения оформлены корректно.",
            }.get(cid, default_msg)
            checks_out.append({"check_id": cid, "status": status, "message": message})
            passed += 1
        else:
            status = "FAILED"
            errors_list: List[Dict] = []
            for it in issues:
                err_page = it.get("page")
                elem = None
                det = it.get("details") or {}
                if isinstance(det, dict):
                    elem = det.get("title") or det.get("element") or det.get("name")
                errors_list.append({
                    "page": err_page,
                    "element": elem or it.get("message"),
                    "rule": it.get("rule"),
                    "description": it.get("message"),
                    "suggestion": (det.get("suggestion") if isinstance(det, dict) else None) or "",
                })

            message = f"Обнаружены ошибки: {len(errors_list)}"
            checks_out.append({"check_id": cid, "status": status, "message": message, "errors": errors_list})
            failed += 1

    if failed == 0:
        compliance = "COMPLIANT"
    elif passed == 0:
        compliance = "NON_COMPLIANT"
    else:
        compliance = "PARTIALLY_COMPLIANT"

    summary = {"total_checks": total, "passed": passed, "failed": failed}

    out = {
        "document_name": data.get("file") or data.get("document_name") or "",
        "compliance_status": compliance,
        "checks": checks_out,
        "summary": summary,
    }

    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(json.dumps({"error": "no json path provided"}))
        sys.exit(1)
    p = sys.argv[1]
    with open(p, encoding='utf-8') as f:
        data = json.load(f)
    out = run_all_checks(data)
    print(json.dumps(out, ensure_ascii=False))
