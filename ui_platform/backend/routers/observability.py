from fastapi import APIRouter
from observability.prometheus import REQUEST_COUNT, REQUEST_LATENCY
from prometheus_client import generate_latest

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics")
def metrics():
    return generate_latest()
