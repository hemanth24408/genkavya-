import pytest
from pydantic import ValidationError

from genkavya.contracts.common import ContractMetadata, ErrorDetail


def test_metadata_and_error_models_validate():
    assert ContractMetadata(producer="rag").producer == "rag"
    assert ErrorDetail(code="E1", message="failed").retryable is False


def test_contract_models_reject_extra_fields():
    with pytest.raises(ValidationError):
        ContractMetadata(producer="rag", unexpected=True)

