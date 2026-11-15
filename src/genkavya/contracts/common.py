"""Common contract status, error, and metadata types."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ContractStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
    UNVERIFIED = "unverified"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    UNVERIFIED = "unverified"


class ErrorDetail(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ContractMetadata(ContractModel):
    contract_version: str = "1.0"
    created_at: datetime | None = None
    producer: str = Field(min_length=1)


T = TypeVar("T")


class ContractEnvelope(ContractModel, Generic[T]):
    status: ContractStatus
    data: T | None = None
    errors: list[ErrorDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: ContractMetadata

