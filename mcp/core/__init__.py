"""mcp/core — MCP Core orchestration layer."""

from mcp.core.pipeline import PipelineStage, STANDARD_PIPELINE
from mcp.core.execution_context import ExecutionContext
from mcp.core.module_registry import ModuleRegistry, module_registry
from mcp.core.agent_registry import AgentRegistry, agent_registry
from mcp.core.workflow_engine import WorkflowEngine
from mcp.core.orchestrator import Orchestrator

__all__ = [
    "PipelineStage",
    "STANDARD_PIPELINE",
    "ExecutionContext",
    "ModuleRegistry",
    "module_registry",
    "AgentRegistry",
    "agent_registry",
    "WorkflowEngine",
    "Orchestrator",
]
