"""FastAPI app exposing the LangGraph agent over the AG-UI protocol (HTTP + SSE)."""

import os

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .graph import build_graph
from .llm import Planner


def create_app(planner: Planner | None = None) -> FastAPI:
    app = FastAPI(title="Agentic UI travel planner")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    agent = LangGraphAgent(
        name="travel_planner",
        description="Plans trips and renders the answer as generative UI (json-render specs).",
        graph=build_graph(planner),
        emit_raw_events=False,  # keep the SSE stream to protocol events only
    )
    add_langgraph_fastapi_endpoint(app, agent, "/agent")
    return app


app = create_app()
