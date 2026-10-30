"""Public input contract. Documents are snapshots of a local supplier inbox."""
import base64
import binascii
import hashlib
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_BYTES = 4_000_000
MAX_BATCH_BYTES = 32_000_000


class SourceVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(default=None, max_length=MAX_BYTES)
    content_base64: str | None = Field(default=None, max_length=5_400_000)
    ready: bool = True

    @model_validator(mode="after")
    def check_payload(self):
        if (self.text is None) == (self.content_base64 is None):
            raise ValueError("Supply exactly one of text or content_base64")
        try:
            payload = self.bytes()
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid base64 document") from exc
        if not payload or len(payload) > MAX_BYTES:
            raise ValueError("Document must contain 1–4,000,000 bytes")
        return self

    def bytes(self):
        return self.text.encode("utf-8") if self.text is not None else base64.b64decode(self.content_base64, validate=True)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=160)
    versions: list[SourceVersion] = Field(min_length=1, max_length=3)

    def version(self, attempt):
        return self.versions[min(attempt - 1, len(self.versions) - 1)]


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[Document] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def check_batch(self):
        ids = [d.document_id for d in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Document IDs must be unique within a batch")
        if sum(len(v.bytes()) for d in self.documents for v in d.versions) > MAX_BATCH_BYTES:
            raise ValueError("Batch exceeds 32 MB")
        return self


def content_hash(payload):
    return hashlib.sha256(payload).hexdigest()
