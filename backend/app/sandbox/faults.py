import asyncio
import logging
from typing import List, Optional, Set
from fastapi import Request, HTTPException
from app.db import fetch_one

logger = logging.getLogger("sandbox.faults")

_flaky_attempts: Set[str] = set()

async def get_active_faults_for_request(request: Request) -> List[str]:
    # 1. Direct header override (useful for testing or frontend direct proxies)
    header_faults = request.headers.get("X-Faults")
    if header_faults:
        return [f.strip() for f in header_faults.split(",") if f.strip()]

    # 2. Lookup via X-Run-Id in DB
    run_id = request.headers.get("X-Run-Id")
    if run_id:
        try:
            row = await fetch_one("SELECT faults FROM runs WHERE id = %s", (run_id,))
            if row and row.get("faults"):
                faults = row["faults"]
                if isinstance(faults, list):
                    return faults
        except Exception as e:
            logger.warning(f"Error fetching faults for run {run_id}: {e}")

    return []

async def apply_request_faults(request: Request, endpoint_tag: str):
    faults = await get_active_faults_for_request(request)
    if not faults:
        return

    # Slow response fault
    if "slow_response" in faults:
        logger.info(f"Injecting fault: slow_response on {request.url.path}")
        await asyncio.sleep(1.5)

    # Flaky 500 fault (fails once per endpoint per run, then recovers)
    if "flaky_500" in faults:
        run_id = request.headers.get("X-Run-Id", "default")
        key = f"{run_id}:{endpoint_tag}"
        if key not in _flaky_attempts:
            _flaky_attempts.add(key)
            logger.info(f"Injecting fault: flaky_500 on {key}")
            raise HTTPException(status_code=500, detail="Sandbox Internal Server Error (Flaky 500 Fault Injected)")

    # Expired session fault
    if "expired_session" in faults:
        # Check if fault was already applied
        run_id = request.headers.get("X-Run-Id", "default")
        key = f"{run_id}:expired_session_tripped"
        if key not in _flaky_attempts:
            _flaky_attempts.add(key)
            logger.info(f"Injecting fault: expired_session on {request.url.path}")
            raise HTTPException(status_code=401, detail="Session Expired. Please log in again.")
