"""Optional FastAPI adapter. Install with: pip install -e '.[api]'"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .vlsm import NetworkRequest, VLSMError, allocation_report

app = FastAPI(title="Professional Network Toolkit API", version="1.1.0")


class SubnetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    hosts: int = Field(gt=0, le=4_294_967_294)


class VLSMRequest(BaseModel):
    parent: str
    subnets: list[SubnetRequest] = Field(min_length=1, max_length=100)


@app.get("/health")
def health():
    return {"status": "ok", "service": "network-toolkit"}


@app.post("/api/v1/vlsm")
def calculate_vlsm(payload: VLSMRequest):
    try:
        requests = [NetworkRequest(item.name, item.hosts) for item in payload.subnets]
        return allocation_report(payload.parent, requests)
    except (ValueError, VLSMError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
