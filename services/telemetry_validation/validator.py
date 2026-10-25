"""Telemetry validation service enforcing schema contracts and tenant boundary integrity."""

from packages.contracts.exceptions import ContractValidationError
from packages.contracts.flow_event import FlowEvent
from packages.tenancy.exceptions import CrossTenantAccessViolation
from packages.tenancy.models import TenantId


class TelemetryValidator:
    """Validates FlowEvent records against contract constraints and tenant authorization boundaries."""

    @staticmethod
    def validate_event(event: FlowEvent) -> None:
        """Validate single flow event."""
        if not event.tenant_id:
            raise ContractValidationError("FlowEvent missing mandatory tenant_id.")
        if not event.exporter_id:
            raise ContractValidationError("FlowEvent missing mandatory exporter_id.")
        if event.byte_count < 0:
            raise ContractValidationError("byte_count cannot be negative.")
        if event.packet_count < 0:
            raise ContractValidationError("packet_count cannot be negative.")

    @staticmethod
    def assert_tenant_boundary(event: FlowEvent, expected_tenant_id: TenantId) -> None:
        """Verify that an event's tenant matches the expected tenant boundary."""
        if event.tenant_id != expected_tenant_id:
            raise CrossTenantAccessViolation(
                principal_id=f"exporter:{event.exporter_id}",
                caller_tenant_id=event.tenant_id,
                target_tenant_id=expected_tenant_id,
                action="telemetry:boundary_check",
            )
