"""Domain exceptions for the TRPG log converter.

Inspired by patterns used in production Python services (Django, FastAPI, Stripe SDK):
domain-specific exception classes carry structured context so callers can branch on
type rather than parsing error strings.

Naming convention:
    *Error  — recoverable / user-facing; surface message to the user
    *Fault  — programmer error / invariant violation; should be reported to logs

Usage:
    try:
        engine.parse_file(path)
    except ParseError as exc:
        # Show exc.user_message to the user; exc.context for debugging
        ...
    except RenderError:
        ...
"""
from __future__ import annotations

from typing import Any


class ConverterError(Exception):
    """Base class for all errors raised by this project.

    Attributes:
        user_message: Korean, user-facing description (safe to display in a dialog).
        context: Structured debug info; goes to logs, not the UI.
    """

    default_user_message: str = "오류가 발생했습니다."

    def __init__(
        self,
        message: str = "",
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or user_message or self.default_user_message)
        self.user_message = user_message or self.default_user_message
        self.context: dict[str, Any] = context or {}

    def with_context(self, **kwargs: Any) -> "ConverterError":
        self.context.update(kwargs)
        return self


# --- Config layer ----------------------------------------------------------

class ConfigError(ConverterError):
    """Configuration file is missing, malformed, or fails validation."""
    default_user_message = "설정 파일을 읽는 중 문제가 발생했습니다."


class SchemaMigrationError(ConfigError):
    """A schema migration step failed."""
    default_user_message = "설정 버전 마이그레이션에 실패했습니다."


# --- Parsing layer ---------------------------------------------------------

class ParseError(ConverterError):
    """Input file could not be parsed into entries."""
    default_user_message = "파일을 분석하는 중 문제가 발생했습니다."


class EncodingError(ParseError):
    """File could not be decoded with any of the supported encodings."""
    default_user_message = (
        "파일 인코딩을 인식할 수 없습니다. "
        "UTF-8 / EUC-KR / CP949 인코딩의 파일만 지원합니다."
    )


class UnsupportedFormatError(ParseError):
    """Input file format is not one we know how to parse."""
    default_user_message = "지원하지 않는 파일 형식입니다."


# --- Rendering layer -------------------------------------------------------

class RenderError(ConverterError):
    """Output document could not be generated."""
    default_user_message = "출력 파일을 생성하는 중 문제가 발생했습니다."


class EpubRenderError(RenderError):
    default_user_message = "EPUB 파일을 생성하는 중 문제가 발생했습니다."


class DocxRenderError(RenderError):
    default_user_message = "DOCX 파일을 생성하는 중 문제가 발생했습니다."


class PdfRenderError(RenderError):
    default_user_message = "PDF 파일을 생성하는 중 문제가 발생했습니다."


# --- Resource layer --------------------------------------------------------

class ResourceError(ConverterError):
    """A required runtime resource (font, image, template) is missing or invalid."""
    default_user_message = "필요한 리소스를 찾을 수 없습니다."


class FontLoadError(ResourceError):
    default_user_message = "글꼴을 불러오지 못했습니다."


# --- Programmer error ------------------------------------------------------

class ConverterFault(ConverterError):
    """An invariant has been violated. This is a bug, not a user problem."""
    default_user_message = "내부 오류가 발생했습니다. 로그를 확인해주세요."


__all__ = [
    "ConverterError",
    "ConfigError",
    "SchemaMigrationError",
    "ParseError",
    "EncodingError",
    "UnsupportedFormatError",
    "RenderError",
    "EpubRenderError",
    "DocxRenderError",
    "PdfRenderError",
    "ResourceError",
    "FontLoadError",
    "ConverterFault",
]
