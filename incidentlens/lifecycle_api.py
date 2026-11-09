"""HTTP routes for persistent incident lifecycle operations."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from incidentlens.lifecycle import IncidentLifecycleStore
from incidentlens.lifecycle_schemas import IncidentUpdateRequest, OpenIncidentRequest

router = APIRouter(prefix="/v1/lifecycle/incidents", tags=["incident lifecycle"])

def get_lifecycle_store(request: Request) -> IncidentLifecycleStore:
    return request.app.state.lifecycle_store

@router.post("", status_code=201)
def open_incident(payload: OpenIncidentRequest,
                  store: Annotated[IncidentLifecycleStore, Depends(get_lifecycle_store)]):
    return store.open_or_get(**payload.model_dump())

@router.get("")
def list_incidents(store: Annotated[IncidentLifecycleStore, Depends(get_lifecycle_store)],
                   status: Annotated[str | None, Query()] = None,
                   service: Annotated[str | None, Query(max_length=120)] = None,
                   limit: Annotated[int, Query(ge=1, le=200)] = 100):
    if status and status not in {"OPEN", "ACKNOWLEDGED", "RESOLVED"}:
        raise HTTPException(status_code=422, detail="Invalid incident status")
    return store.list(status=status, service=service, limit=limit)

@router.get("/{incident_id}")
def get_incident(incident_id: str,
                 store: Annotated[IncidentLifecycleStore, Depends(get_lifecycle_store)]):
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident": incident, "activity": store.activity(incident_id)}

@router.patch("/{incident_id}")
def update_incident(incident_id: str, payload: IncidentUpdateRequest,
                    store: Annotated[IncidentLifecycleStore, Depends(get_lifecycle_store)]):
    try:
        update_data = payload.model_dump(exclude_unset=True)
        actor = update_data.pop("actor", "operator")

        incident = store.update(
            incident_id,
            actor=actor,
            **update_data
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
