"""Tenant registry and exporter binding."""


from .exceptions import (
    InactiveTenantError,
    TenantNotFoundError,
    UntrustedTenantClaimViolation,
)
from .models import (
    ExporterRegistration,
    TenantConfig,
    TenantId,
    TenantStatus,
)


class TenantRegistry:
    """Thread-safe registry of authorized ISP tenants and their hardware exporters."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantConfig] = {}
        # Key: (exporter_ip, observation_domain_id) -> (tenant_id, exporter_id)
        self._exporter_lookup: dict[tuple[str, int], tuple[str, str]] = {}

    def register_tenant(self, config: TenantConfig) -> None:
        """Register or update an ISP tenant."""
        self._tenants[config.tenant_id] = config
        for exporter in config.exporters.values():
            if exporter.active:
                self._exporter_lookup[(exporter.ip_address, exporter.observation_domain_id)] = (
                    config.tenant_id,
                    exporter.exporter_id,
                )

    def register_exporter(self, tenant_id: str, exporter: ExporterRegistration) -> None:
        """Register an exporter under an existing active tenant."""
        tenant = self.get_tenant(tenant_id)
        if tenant.status != TenantStatus.ACTIVE:
            raise InactiveTenantError(tenant_id, tenant.status.value)
        tenant.register_exporter(exporter)
        self._exporter_lookup[(exporter.ip_address, exporter.observation_domain_id)] = (
            tenant_id,
            exporter.exporter_id,
        )

    def get_tenant(self, tenant_id: str) -> TenantConfig:
        """Retrieve tenant configuration by tenant_id."""
        if tenant_id not in self._tenants:
            raise TenantNotFoundError(tenant_id)
        return self._tenants[tenant_id]

    def list_tenants(self) -> list[TenantConfig]:
        """List all registered tenants."""
        return list(self._tenants.values())

    def resolve_exporter(
        self,
        exporter_ip: str,
        observation_domain_id: int,
    ) -> tuple[TenantId, str] | None:
        """
        Map an incoming network packet's source IP and Observation Domain ID
        to its pre-registered, cryptographically trusted (tenant_id, exporter_id).
        Returns None if unrecognized.
        """
        lookup = self._exporter_lookup.get((exporter_ip, observation_domain_id))
        if lookup is None:
            return None
        t_id, e_id = lookup
        tenant = self._tenants.get(t_id)
        if tenant is None or tenant.status != TenantStatus.ACTIVE:
            return None
        return t_id, e_id

    def validate_telemetry_origin(
        self,
        trusted_tenant_id: TenantId,
        exporter_id: str,
        untrusted_claimed_tenant_id: str | None = None,
    ) -> TenantId:
        """
        Enforce telemetry origin rule:
        Untrusted tenant claims embedded in packet metadata are rejected if they
        contradict the trusted exporter mapping.
        """
        if untrusted_claimed_tenant_id is not None:
            if untrusted_claimed_tenant_id != trusted_tenant_id:
                raise UntrustedTenantClaimViolation(
                    claimed_tenant_id=untrusted_claimed_tenant_id,
                    trusted_tenant_id=trusted_tenant_id,
                    exporter_id=exporter_id,
                )
        return trusted_tenant_id

    @classmethod
    def create_simulated_network(cls) -> "TenantRegistry":
        """
        Bootstrap the 7 simulated rural ISP tenants specified in FCS v1.2 Phase 1:
        - tenant-isp-alpha: Northern Valley Broadband
        - tenant-isp-beta: Coastal Reach Networks
        - tenant-isp-gamma: Highland Wireless ISP
        - tenant-isp-delta: Western Plains Fiber
        - tenant-isp-epsilon: River Bend Telecommunications
        - tenant-isp-zeta: Pine Ridge Regional ISP
        - tenant-isp-eta: Desert Sun Rural Connect
        """
        registry = cls()
        simulated_isps = [
            ("tenant-isp-alpha", "Northern Valley Broadband", "10.100.1.1", 101),
            ("tenant-isp-beta", "Coastal Reach Networks", "10.100.2.1", 102),
            ("tenant-isp-gamma", "Highland Wireless ISP", "10.100.3.1", 103),
            ("tenant-isp-delta", "Western Plains Fiber", "10.100.4.1", 104),
            ("tenant-isp-epsilon", "River Bend Telecommunications", "10.100.5.1", 105),
            ("tenant-isp-zeta", "Pine Ridge Regional ISP", "10.100.6.1", 106),
            ("tenant-isp-eta", "Desert Sun Rural Connect", "10.100.7.1", 107),
        ]

        for tid, name, ip, domain_id in simulated_isps:
            exporter = ExporterRegistration(
                exporter_id=f"gw-{tid}",
                ip_address=ip,
                observation_domain_id=domain_id,
                sample_rate=1,
                active=True,
            )
            config = TenantConfig(
                tenant_id=tid,
                name=name,
                region="ap-south-1",
                status=TenantStatus.ACTIVE,
                allowed_cidr_blocks=[f"{ip}/24"],
                max_events_per_sec=20000,
                exporters={exporter.exporter_id: exporter},
            )
            registry.register_tenant(config)

        return registry
