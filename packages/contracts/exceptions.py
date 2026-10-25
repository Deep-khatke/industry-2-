"""Exceptions for telemetry contract validation."""


class ContractValidationError(ValueError):
    """Raised when a telemetry record fails contract schema validation."""


class InvalidSchemaVersionError(ContractValidationError):
    """Raised when a contract encounters an unsupported schema version."""

    def __init__(self, given_version: str, supported_versions: list[str]) -> None:
        super().__init__(
            f"Unsupported schema version: '{given_version}'. Supported: {supported_versions}"
        )
        self.given_version = given_version
        self.supported_versions = supported_versions


class RecordSizeLimitExceeded(ContractValidationError):
    """Raised when a record exceeds bounded memory size limits."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"Record size {size_bytes} bytes exceeds maximum allowed limit of {max_bytes} bytes."
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
