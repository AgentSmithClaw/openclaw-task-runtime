from __future__ import annotations

from openclaw_task_runtime.runtime_v1 import BOARD_PATH, DB_PATH, REGISTRY_PATH, ROLLUP_PATH, TaskRuntime


def main() -> None:
    runtime = TaskRuntime()
    runtime.materialize_views()
    print(f"initialized runtime db: {DB_PATH}")
    print(f"initialized registry: {REGISTRY_PATH}")
    print(f"initialized board: {BOARD_PATH}")
    print(f"initialized rollup: {ROLLUP_PATH}")


if __name__ == "__main__":
    main()
