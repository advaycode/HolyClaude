"""CADCopilot — a parametric CAD copilot MCP for Autodesk Inventor and Fusion 360.

The replicable core of Adam CAD: tools are parametric CAD operations; the LLM is
the agent that composes them. One unified tool schema dispatches to either an
Inventor (pywin32 COM) or Fusion (in-app add-in TCP bridge) backend.
"""

__version__ = "0.1.0"
