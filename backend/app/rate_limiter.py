"""In-memory rate limiter and brute-force protection for security-critical endpoints."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status


@dataclass
class RateLimitRecord:
    attempts: int = 0
    window_start: float = field(default_factory=time.time)
    locked_until: float = 0.0


class BruteForceProtector:
    """Sliding-window rate limiter with progressive lockout for login attempts."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 300,  # 5 minutes
        lockout_seconds: int = 900,  # 15 minutes lockout
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._records: Dict[str, RateLimitRecord] = defaultdict(RateLimitRecord)
        self._lock = Lock()

    def _get_key(self, request: Request, identifier: str) -> str:
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        return f"{client_ip}:{identifier.strip().lower()}"

    def check_attempt(self, request: Request, identifier: str) -> None:
        key = self._get_key(request, identifier)
        now = time.time()

        with self._lock:
            record = self._records[key]

            # Check if currently locked out
            if record.locked_until > now:
                remaining_seconds = int(record.locked_until - now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed login attempts. Account temporarily locked. Please try again in {remaining_seconds} seconds.",
                    headers={"Retry-After": str(remaining_seconds)},
                )

            # Reset window if expired
            if now - record.window_start > self.window_seconds:
                record.attempts = 0
                record.window_start = now
                record.locked_until = 0.0

    def record_failure(self, request: Request, identifier: str) -> int:
        key = self._get_key(request, identifier)
        now = time.time()

        with self._lock:
            record = self._records[key]
            if now - record.window_start > self.window_seconds:
                record.attempts = 1
                record.window_start = now
            else:
                record.attempts += 1

            if record.attempts >= self.max_attempts:
                record.locked_until = now + self.lockout_seconds
                return self.lockout_seconds

            return 0

    def record_success(self, request: Request, identifier: str) -> None:
        key = self._get_key(request, identifier)
        with self._lock:
            if key in self._records:
                del self._records[key]

    def cleanup_old_records(self) -> None:
        now = time.time()
        with self._lock:
            keys_to_delete = [
                k
                for k, r in self._records.items()
                if now - r.window_start > (self.window_seconds * 2) and r.locked_until <= now
            ]
            for k in keys_to_delete:
                del self._records[k]


login_limiter = BruteForceProtector(max_attempts=5, window_seconds=300, lockout_seconds=900)
