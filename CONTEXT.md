# Project Context

## Domain Terms

### Generation Request

An incoming API request that contains a natural-language prompt, optional output format, optional overrides, and client metadata.

### Generation Spec

The normalized interpretation of what the user wants to create. It captures document type, title, language, style, tone, structure, constraints, and formatting defaults.

### Artifact Plan

The concrete renderer-ready plan for a generated file. For the current prototype this is a document plan for `.docx`; future formats can introduce presentation, spreadsheet, or PDF-specific plans.

### Artifact

The persisted result of a generation request. It tracks output format, status, file metadata, warnings, and errors.

### Renderer

A format-specific module that turns an artifact plan into a real file. The current adapter is `DocxRenderer`.

### Artifact Format

The requested output file format. The system knows about future formats such as `pptx`, `xlsx`, `pdf`, and `html`, but only `docx` is renderable in the current prototype.

### Renderer Registry

The module that selects the renderer adapter for a supported artifact format.

### Generation Pipeline

The module that owns planning and rendering orchestration. It hides the details of OpenRouter planning and renderer selection behind one small interface.

### OpenRouter Planning

The LLM-backed step that converts a free-form user prompt into structured generation data.
