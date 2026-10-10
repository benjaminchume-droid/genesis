import pytest

from genesis.acquisition.source import SourceDocument


def test_source_document_records_content_digest_and_origin():
    document = SourceDocument.capture(
        "https://example.org/reference",
        "A sample source body.",
        title="Reference",
    )
    assert document.uri == "https://example.org/reference"
    assert len(document.content_sha256) == 64
    assert document.content_sha256


def test_source_document_requires_uri_and_content():
    with pytest.raises(ValueError):
        SourceDocument.capture("", "content")
    with pytest.raises(ValueError):
        SourceDocument.capture("https://example.org", " ")
