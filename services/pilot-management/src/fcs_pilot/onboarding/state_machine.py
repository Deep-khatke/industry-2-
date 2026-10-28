"""ISP Pilot Onboarding State Machine with auditable authorization controls."""

import logging
from datetime import UTC, datetime
from typing import Any

from .models import (
    EnvironmentMode,
    OnboardingStatus,
    PilotProfile,
    StateTransitionRecord,
)

logger = logging.getLogger("fcs_pilot.onboarding")


class OnboardingError(Exception):
    """Raised when an illegal or unauthorized pilot state transition is attempted."""


class OnboardingStateMachine:
    """
    Governs transitions between onboarding states.
    Ensures that live monitoring cannot be activated without prerequisites,
    and records all state changes with cryptographic traceability.
    """

    ALLOWED_TRANSITIONS: dict[OnboardingStatus, set[OnboardingStatus]] = {
        OnboardingStatus.DRAFT: {
            OnboardingStatus.AUTHORIZATION_PENDING,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.AUTHORIZATION_PENDING: {
            OnboardingStatus.TECHNICAL_REVIEW,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.TECHNICAL_REVIEW: {
            OnboardingStatus.SECURITY_REVIEW,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_PAUSED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.SECURITY_REVIEW: {
            OnboardingStatus.READY_FOR_SHADOW,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_PAUSED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.READY_FOR_SHADOW: {
            OnboardingStatus.SHADOW_ACTIVE,
            OnboardingStatus.PILOT_PAUSED,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.SHADOW_ACTIVE: {
            OnboardingStatus.SHADOW_COMPLETED,
            OnboardingStatus.PILOT_PAUSED,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.SHADOW_COMPLETED: {
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.PILOT_PAUSED: {
            OnboardingStatus.SHADOW_ACTIVE,
            OnboardingStatus.TECHNICAL_REVIEW,
            OnboardingStatus.PILOT_BLOCKED,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.PILOT_BLOCKED: {
            OnboardingStatus.DRAFT,
            OnboardingStatus.AUTHORIZATION_PENDING,
            OnboardingStatus.TECHNICAL_REVIEW,
            OnboardingStatus.PILOT_CLOSED,
        },
        OnboardingStatus.PILOT_CLOSED: set(),
    }

    def __init__(self, profiles: list[PilotProfile] | None = None) -> None:
        self._profiles: dict[str, PilotProfile] = {}
        self._audit_log: list[StateTransitionRecord] = []
        if profiles:
            for p in profiles:
                self._profiles[p.pilot_id] = p

    def get_profile(self, pilot_id: str) -> PilotProfile | None:
        return self._profiles.get(pilot_id)

    def list_profiles(self) -> list[PilotProfile]:
        return list(self._profiles.values())

    def register_profile(self, profile: PilotProfile) -> None:
        self._profiles[profile.pilot_id] = profile

    def get_audit_trail(self, pilot_id: str | None = None) -> list[StateTransitionRecord]:
        if pilot_id:
            return [t for t in self._audit_log if t.pilot_id == pilot_id]
        return list(self._audit_log)

    def transition_state(
        self,
        pilot_id: str,
        target_state: OnboardingStatus,
        actor_id: str,
        actor_role: str,
        reason: str,
        evidence_ref: str | None = None,
        technical_check_passed: bool = True,
    ) -> PilotProfile:
        """
        Transition a pilot to a new state after validating authorization and prerequisites.
        """
        profile = self.get_profile(pilot_id)
        if not profile:
            raise OnboardingError(f"Pilot '{pilot_id}' not found.")

        current_state = profile.status

        # 1. Verify role permissions
        if actor_role not in ("PLATFORM_ADMIN", "TENANT_ADMIN"):
            raise OnboardingError(
                f"Unauthorized: Role '{actor_role}' cannot change pilot states. Requires PLATFORM_ADMIN or TENANT_ADMIN."
            )

        # 2. Verify state transition graph
        allowed = self.ALLOWED_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise OnboardingError(
                f"Illegal transition: Cannot transition pilot '{pilot_id}' from {current_state} to {target_state}. "
                f"Allowed target states: {sorted(list(allowed))}"
            )

        # 3. Verify specific prerequisite gates
        if target_state == OnboardingStatus.TECHNICAL_REVIEW:
            if profile.environment_mode == EnvironmentMode.MODE_B_REAL_SHADOW:
                if not profile.authorization or not profile.authorization.written_agreement_ref:
                    raise OnboardingError(
                        f"Cannot transition Mode B pilot to TECHNICAL_REVIEW: Missing signed written agreement."
                    )

        if target_state == OnboardingStatus.SECURITY_REVIEW:
            if not technical_check_passed:
                raise OnboardingError(
                    f"Cannot transition to SECURITY_REVIEW: Exporter technical compatibility check failed."
                )

        if target_state == OnboardingStatus.SHADOW_ACTIVE:
            if profile.environment_mode == EnvironmentMode.MODE_B_REAL_SHADOW:
                if not profile.authorization or not profile.authorization.approved_by:
                    raise OnboardingError(
                        "LIVE_PILOT_BLOCKED: Formal written ISP authorization and zero-cost confirmation required "
                        "before live Shadow Mode can be activated."
                    )

        # Apply state transition
        profile.status = target_state
        profile.updated_at = datetime.now(UTC)
        if target_state == OnboardingStatus.PILOT_BLOCKED:
            profile.blocker_reason = reason
        elif target_state == OnboardingStatus.SHADOW_ACTIVE:
            profile.blocker_reason = None

        # Record audit log
        transition_record = StateTransitionRecord(
            pilot_id=pilot_id,
            tenant_id=profile.tenant_id,
            from_state=current_state,
            to_state=target_state,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason,
            evidence_ref=evidence_ref,
        )
        self._audit_log.append(transition_record)
        logger.info(
            f"Pilot '{pilot_id}' transitioned from {current_state} to {target_state} by {actor_id} ({actor_role})."
        )
        return profile
