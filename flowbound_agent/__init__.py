"""Google ADK agent package for FlowBound.

The ADK runtime is imported lazily so non-Google runtimes such as Nebius Token
Factory can use the shared proposal schema without requiring google-adk at import
time.
"""

__all__ = ["root_agent"]


def __getattr__(name: str):
    if name == "root_agent":
        from .agent import root_agent

        return root_agent
    raise AttributeError(name)
