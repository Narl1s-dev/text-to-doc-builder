from enum import StrEnum


class ArtifactFormat(StrEnum):
    docx = "docx"
    pptx = "pptx"
    xlsx = "xlsx"
    pdf = "pdf"
    html = "html"


SUPPORTED_RENDER_FORMATS = frozenset({ArtifactFormat.docx})
DEFAULT_OUTPUT_FORMAT = ArtifactFormat.docx


def normalize_artifact_format(value: ArtifactFormat | str) -> ArtifactFormat:
    try:
        return ArtifactFormat(value)
    except ValueError as exc:
        supported_values = ", ".join(format.value for format in ArtifactFormat)
        raise ValueError(f"Unknown artifact format '{value}'. Known formats: {supported_values}.") from exc


def is_render_supported(value: ArtifactFormat | str) -> bool:
    return normalize_artifact_format(value) in SUPPORTED_RENDER_FORMATS


def supported_render_format_values() -> tuple[str, ...]:
    return tuple(format.value for format in sorted(SUPPORTED_RENDER_FORMATS, key=lambda item: item.value))


def infer_artifact_format_from_prompt(prompt: str) -> ArtifactFormat | None:
    normalized = prompt.lower()
    document_keywords = (
        "сочинен",
        "сочинён",
        "сочинение",
        "эссе",
        "essay",
        "реферат",
        "отчет",
        "отчёт",
        "документ",
        "статья",
        "работа",
        "report",
        "document",
    )
    explicit_spreadsheet_keywords = (
        "excel",
        "xlsx",
        "spreadsheet",
        "электронн",
        "книгу excel",
        "файл excel",
        "табличный файл",
        "таблицу excel",
    )
    if any(keyword in normalized for keyword in explicit_spreadsheet_keywords):
        return ArtifactFormat.xlsx

    format_keywords = {
        ArtifactFormat.pptx: (
            "презентац",
            "презенташ",
            "преза",
            "презу",
            "слайд",
            "deck",
            "slides",
            "presentation",
            "pptx",
            "powerpoint",
        ),
        ArtifactFormat.xlsx: (
            "электронную таблицу",
            "табличный документ",
            "табличный файл",
            "лист",
        ),
        ArtifactFormat.pdf: (
            "pdf",
            "пдф",
        ),
        ArtifactFormat.html: (
            "html",
            "веб-страниц",
            "страницу",
        ),
        ArtifactFormat.docx: (
            "документ",
            "отчет",
            "отчёт",
            "записк",
            "договор",
            "docx",
            "word",
        ),
    }
    for artifact_format, keywords in format_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            if artifact_format == ArtifactFormat.xlsx and any(
                keyword in normalized for keyword in document_keywords
            ):
                return ArtifactFormat.docx
            return artifact_format
    return None
