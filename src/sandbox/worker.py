"""python -m sandbox.worker [--bundle NAME]... — run one Worker per selected bundle."""

import argparse
import asyncio
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

import sandbox.workflows  # noqa: F401  (side effect: registers all bundles)
from sandbox import config, registry

GRACEFUL_SHUTDOWN_TIMEOUT = timedelta(seconds=5)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Temporal sandbox workers.")
    parser.add_argument(
        "--bundle",
        action="append",
        dest="bundle",
        help="Bundle name to serve (repeatable). Defaults to all registered bundles.",
    )
    return parser.parse_args()


async def run_worker(client: Client, bundle: registry.Bundle) -> None:
    async with Worker(
        client,
        task_queue=bundle.effective_task_queue,
        workflows=bundle.workflows,
        activities=bundle.activities,
        graceful_shutdown_timeout=GRACEFUL_SHUTDOWN_TIMEOUT,
    ):
        await asyncio.Event().wait()


async def main() -> None:
    args = parse_args()
    bundles = registry.resolve(args.bundle)

    print(
        f"Connecting to Temporal at {config.TEMPORAL_ADDRESS} "
        f"(namespace={config.TEMPORAL_NAMESPACE})"
    )
    client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)

    for bundle in bundles:
        print(f"Serving bundle {bundle.name!r} on task queue {bundle.effective_task_queue!r}")

    tasks = [asyncio.ensure_future(run_worker(client, bundle)) for bundle in bundles]
    gathered = asyncio.gather(*tasks)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, gathered.cancel)

    try:
        await gathered
    except asyncio.CancelledError:
        print("Shutting down workers gracefully...")


if __name__ == "__main__":
    asyncio.run(main())
