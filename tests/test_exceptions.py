"""Tests for the domain exception hierarchy in ``core.exceptions``."""

from __future__ import annotations

import pytest

from core.exceptions import (
    ConfigError,
    ConverterError,
    EncodingError,
    ParseError,
    RenderError,
    SchemaMigrationError,
)


class TestConverterError:
    def test_default_user_message(self):
        err = ConverterError()
        assert err.user_message == ConverterError.default_user_message
        assert err.context == {}

    def test_explicit_user_message_overrides_default(self):
        err = ConverterError(user_message="문제가 생겼어요")
        assert err.user_message == "문제가 생겼어요"

    def test_context_is_attached_and_extensible(self):
        err = ConverterError(context={"path": "/tmp/x"})
        err.with_context(file_size=1234)
        assert err.context == {"path": "/tmp/x", "file_size": 1234}

    def test_str_falls_back_to_user_message(self):
        err = ConverterError(user_message="안녕")
        assert "안녕" in str(err)


class TestSubclasses:
    @pytest.mark.parametrize(
        "cls,parent",
        [
            (SchemaMigrationError, ConfigError),
            (EncodingError, ParseError),
            (ConfigError, ConverterError),
            (ParseError, ConverterError),
            (RenderError, ConverterError),
        ],
    )
    def test_inheritance(self, cls, parent):
        assert issubclass(cls, parent)

    def test_each_subclass_has_unique_user_message(self):
        messages = {
            ConfigError.default_user_message,
            ParseError.default_user_message,
            RenderError.default_user_message,
            EncodingError.default_user_message,
        }
        # No two subclasses should accidentally share the default copy.
        assert len(messages) == 4

    def test_catchable_as_base(self):
        with pytest.raises(ConverterError):
            raise EncodingError("foo")
