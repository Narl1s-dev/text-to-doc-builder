import pytest

from app.llm.docx_codegen import CodegenValidationError, parse_docx_codegen_response


def test_parse_docx_codegen_response_accepts_json() -> None:
    result = parse_docx_codegen_response(
        """
        {
          "python_code": "from docx import Document\\nDocument().save('/output/result.docx')",
          "warnings": ["ok"]
        }
        """
    )

    assert "Document().save" in result.python_code
    assert result.warnings == ["ok"]


def test_parse_docx_codegen_response_rejects_empty_code() -> None:
    with pytest.raises(CodegenValidationError):
        parse_docx_codegen_response('{"python_code": "   ", "warnings": []}')
