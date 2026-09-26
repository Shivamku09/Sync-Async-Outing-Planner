from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, time
from typing import Any, Awaitable, Callable

import httpx

from load_generator.metrics import latency_summary
from load_generator.payloads import planning_payload


async def _bounded_run(
    total: int,
    concurrency: int,
    operation: Callable[[int], Awaitable[dict[str, Any]]],
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def execute(index: int) -> dict[str, Any]:
        async with semaphore:
            return await operation(index)

    return await asyncio.gather(*(execute(index) for index in range(total)))


async def run_sync(client: httpx.AsyncClient, base_url: str, total: int, concurrency: int) -> dict[str, Any]:
    async def send(_: int) -> dict[str, Any]:
        started = perf_counter()
        try:
            response = await client.post(f"{base_url}/sync", json=planning_payload())
            elapsed_ms = (perf_counter() - started) * 1000
            body = response.json()
            succeeded = response.is_success and body.get("status") == "succeeded"
            return {"succeeded": succeeded, "latency_ms": elapsed_ms, "status_code": response.status_code}
        except Exception as exc:
            return {"succeeded": False, "latency_ms": (perf_counter() - started) * 1000, "error": type(exc).__name__}

    test_started = perf_counter()
    results = await _bounded_run(total, concurrency, send)
    duration = perf_counter() - test_started
    successful = [item for item in results if item["succeeded"]]
    return {
        "mode": "sync",
        "total_requests_sent": total,
        "successful": len(successful),
        "failed": total - len(successful),
        "duration_seconds": round(duration, 2),
        "throughput_requests_per_second": round(total / duration, 2) if duration else 0,
        "latency_ms": latency_summary([item["latency_ms"] for item in successful]),
    }


async def run_async(
    client: httpx.AsyncClient,
    base_url: str,
    callback_receiver_url: str,
    callback_public_url: str,
    total: int,
    concurrency: int,
    callback_timeout: float,
) -> dict[str, Any]:
    await client.post(f"{callback_receiver_url}/reset")
    submission_times: dict[str, float] = {}
    acknowledgement_latencies: list[float] = []

    async def send(_: int) -> dict[str, Any]:
        started_epoch = time()
        started = perf_counter()
        payload = planning_payload() | {"callback_url": callback_public_url}
        try:
            response = await client.post(f"{base_url}/async", json=payload)
            elapsed_ms = (perf_counter() - started) * 1000
            body = response.json()
            request_id = body.get("id")
            accepted = response.status_code == 202 and bool(request_id)
            if accepted:
                submission_times[str(request_id)] = started_epoch
                acknowledgement_latencies.append(elapsed_ms)
            return {"accepted": accepted, "status_code": response.status_code}
        except Exception as exc:
            return {"accepted": False, "error": type(exc).__name__}

    test_started = perf_counter()
    submissions = await _bounded_run(total, concurrency, send)
    accepted = sum(1 for item in submissions if item["accepted"])

    deadline = perf_counter() + callback_timeout
    callback_items: list[dict[str, Any]] = []
    while perf_counter() < deadline and len(callback_items) < accepted:
        response = await client.get(f"{callback_receiver_url}/results")
        callback_items = response.json().get("items", [])
        if len(callback_items) < accepted:
            await asyncio.sleep(0.25)

    relevant = [item for item in callback_items if item.get("request_id") in submission_times]
    callback_times = [
        (float(item["received_at_epoch"]) - submission_times[item["request_id"]]) * 1000
        for item in relevant
    ]
    planning_succeeded = sum(1 for item in relevant if item.get("payload", {}).get("status") == "succeeded")
    duration = perf_counter() - test_started
    return {
        "mode": "async",
        "total_requests_sent": total,
        "successful": planning_succeeded,
        "failed": total - planning_succeeded,
        "accepted": accepted,
        "rejected_or_failed_to_submit": total - accepted,
        "callbacks_received": len(relevant),
        "callbacks_missing": accepted - len(relevant),
        "planning_succeeded": planning_succeeded,
        "planning_failed": len(relevant) - planning_succeeded,
        "duration_seconds": round(duration, 2),
        "acknowledgement_latency_ms": latency_summary(acknowledgement_latencies),
        "time_to_callback_ms": latency_summary(callback_times),
    }


def _print_summary(summary: dict[str, Any]) -> None:
    print(f"\n{summary['mode'].upper()} SUMMARY")
    print("-" * 40)
    for key, value in summary.items():
        if key != "mode":
            print(f"{key}: {value}")


async def run(args: argparse.Namespace) -> None:
    timeout = httpx.Timeout(args.request_timeout)
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    summaries: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        if args.mode in {"sync", "both"}:
            summaries.append(await run_sync(client, args.base_url, args.requests, args.concurrency))
        if args.mode in {"async", "both"}:
            summaries.append(await run_async(
                client, args.base_url, args.callback_receiver_url, args.callback_url,
                args.requests, args.concurrency, args.callback_timeout,
            ))

    for summary in summaries:
        _print_summary(summary)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "requests_per_mode": args.requests,
        "concurrency": args.concurrency,
        "summaries": summaries,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nJSON report: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load test the sync and async outing planner APIs")
    parser.add_argument("--mode", choices=["sync", "async", "both"], default="both")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--base-url", default="http://api:8000")
    parser.add_argument("--callback-receiver-url", default="http://callback-receiver:9000")
    parser.add_argument("--callback-url", default="http://callback-receiver:9000/callback")
    parser.add_argument("--callback-timeout", type=float, default=60.0)
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--output", default="/results/load-test-result.json")
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be at least 1")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
