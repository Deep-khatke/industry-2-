"""Template cache tracking exporter-specific template definitions and observation domains."""

import threading
from datetime import UTC, datetime

from .protocol import TemplateDefinition


class TemplateCache:
    """
    Thread-safe template state tracker.
    Maintains template definitions isolated per (exporter_ip, observation_domain_id).
    Prevents cross-exporter or cross-domain template collisions.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: (exporter_ip, observation_domain_id, template_id) -> (TemplateDefinition, datetime)
        self._templates: dict[tuple[str, int, int], tuple[TemplateDefinition, datetime]] = {}

    def store_template(
        self,
        exporter_ip: str,
        observation_domain_id: int,
        template: TemplateDefinition,
    ) -> None:
        """Store or update a template definition for an exporter observation domain."""
        key = (exporter_ip, observation_domain_id, template.template_id)
        with self._lock:
            self._templates[key] = (template, datetime.now(UTC))

    def get_template(
        self,
        exporter_ip: str,
        observation_domain_id: int,
        template_id: int,
    ) -> TemplateDefinition | None:
        """Lookup a template definition."""
        key = (exporter_ip, observation_domain_id, template_id)
        with self._lock:
            entry = self._templates.get(key)
            return entry[0] if entry else None

    def get_templates_for_domain(
        self,
        exporter_ip: str,
        observation_domain_id: int,
    ) -> dict[int, TemplateDefinition]:
        """Retrieve all active templates for a given exporter observation domain."""
        with self._lock:
            result: dict[int, TemplateDefinition] = {}
            for (ip, dom, tid), (tmpl, _) in self._templates.items():
                if ip == exporter_ip and dom == observation_domain_id:
                    result[tid] = tmpl
            return result

    def clear(self) -> None:
        """Clear all stored templates."""
        with self._lock:
            self._templates.clear()
