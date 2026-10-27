"""SIMULATED issuing-authority services, mounted by app.main at /mock.

    from app.mock_authorities import router
    app.include_router(router, prefix="/mock")

SIMULATED issuing authority for prototype; real integration would use authorized APIs (DigiLocker Issuer/Requester
APIs, NBA, NAAC, state land-record and fire-NOC portals, ICAI UDIN, AICTE TER gateway).
"""
from .routes import router

__all__ = ["router"]
