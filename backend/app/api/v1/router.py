from fastapi import APIRouter

from app.api.v1 import agents, auth, captures, dashboard, flows, live_sessions, models, reports, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(models.router)
api_router.include_router(agents.router)
api_router.include_router(captures.router)
api_router.include_router(live_sessions.router)
api_router.include_router(flows.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(ws.router)
