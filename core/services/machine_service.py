"""
Machine service.

Wraps MachineRepositoryInterface with business-meaningful status
derivation. "Running" vs "Idle" is derived from real batch_stage_history
data (a machine with an open stage-history row is busy) — this is
genuine derived state, not a simulation. True machine telemetry
(Maintenance status, actual uptime) is out of MVP scope; see
docs/FutureScope.md.
"""

import logging
from dataclasses import dataclass

from core.repositories.machine_repository import MachineRepositoryInterface
from core.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MachineStatus:
    """Domain object combining a machine's static info with its current derived status."""

    machine_id: int
    machine_name: str
    machine_type: str
    default_stage: str
    is_running: bool
    stage_history_count: int


class MachineService:
    """Business logic for machine status and utilization. Depends only on the repository interface."""

    def __init__(self, machine_repository: MachineRepositoryInterface) -> None:
        self._machine_repository = machine_repository

    def get_all_statuses(self) -> list[MachineStatus]:
        """Status for every active machine, ordered by name."""
        machines = self._machine_repository.get_all(active_only=True)
        history_counts = self._machine_repository.get_stage_history_counts()

        return [
            MachineStatus(
                machine_id=m.machine_id,
                machine_name=m.machine_name,
                machine_type=m.machine_type,
                default_stage=m.default_stage,
                is_running=self._machine_repository.is_machine_busy(m.machine_id),
                stage_history_count=history_counts.get(m.machine_id, 0),
            )
            for m in machines
        ]

    def get_status(self, machine_id: int) -> MachineStatus:
        machine = self._machine_repository.get_by_id(machine_id)
        if machine is None:
            raise NotFoundError(f"No machine with id {machine_id}.")

        return MachineStatus(
            machine_id=machine.machine_id,
            machine_name=machine.machine_name,
            machine_type=machine.machine_type,
            default_stage=machine.default_stage,
            is_running=self._machine_repository.is_machine_busy(machine.machine_id),
            stage_history_count=self._machine_repository.get_stage_history_counts().get(machine.machine_id, 0),
        )

    def get_machines_for_stage(self, stage: str) -> list[MachineStatus]:
        """
        Machines whose default_stage matches, for populating a selector
        (e.g. the Inspection page's machine dropdown, filtered to
        Quality Inspection stage machines).
        """
        machines = self._machine_repository.get_by_stage(stage)
        return [self.get_status(m.machine_id) for m in machines]

    def utilization_summary(self) -> dict[str, int]:
        """Stage-history-row count per machine name — the MVP's utilization proxy metric."""
        counts = self._machine_repository.get_stage_history_counts()
        machines = {m.machine_id: m.machine_name for m in self._machine_repository.get_all(active_only=False)}
        return {machines.get(mid, f"machine {mid}"): count for mid, count in counts.items()}
