# Future Renderers

The prototype currently supports only `docx`, but the format seam is ready for future adapters.

## Current Format Policy

Known artifact formats:

- `docx`
- `pptx`
- `xlsx`
- `pdf`
- `html`

Currently renderable format:

- `docx`

Explicit API requests for `pptx`, `xlsx`, `pdf`, or `html` are rejected until a renderer adapter exists. LLM planning may mention those formats, but `DefaultsResolver` normalizes unsupported planned formats to `docx` with a warning.

## PptxRenderer

Expected adapter:

```text
ArtifactPlan -> PptxRenderer -> .pptx file
```

Likely dependency:

- `python-pptx`

The future plan shape should model slides, layouts, titles, speaker notes, images, charts, and tables.

## XlsxRenderer

Expected adapter:

```text
ArtifactPlan -> XlsxRenderer -> .xlsx file
```

Likely dependencies:

- `openpyxl`
- or `XlsxWriter`

The future plan shape should model workbooks, sheets, tables, formulas, formatting, and charts.

## PdfRenderer

Expected adapter:

```text
ArtifactPlan -> HtmlRenderer -> PdfRenderer -> .pdf file
```

Likely dependency:

- `WeasyPrint`

PDF should probably be generated from an HTML/CSS intermediate plan rather than assembled directly. That keeps layout concerns behind the renderer seam.

## HtmlRenderer

Expected adapter:

```text
ArtifactPlan -> HtmlRenderer -> .html file
```

Likely dependencies:

- `Jinja2`
- HTML sanitizer if user-provided HTML is ever allowed

HTML can also become an intermediate format for PDF.
