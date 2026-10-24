"""Temporal worker runner for CouchPilot."""
import asyncio
import os
import signal
from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.activities import CouchPilotActivities
from app.workflows.workflows import CouchPilotWorkflow


async def run_worker() -> None:
    host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "couchpilot-task-queue")

    print(f"Connecting to Temporal server at {host} (namespace: {namespace})...")
    client = await Client.connect(host, namespace=namespace)

    activities = CouchPilotActivities()
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[CouchPilotWorkflow],
        activities=[
            activities.setup_worktree,
            activities.scan_repo,
            activities.generate_batch,
            activities.validate_and_apply_patch,
            activities.commit_and_cleanup,
            activities.publish_report,
        ],
    )

    print(f"CouchPilot Temporal worker started on task queue '{task_queue}'. Waiting for jobs...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
