"""Hand-off between `pytest_launch` and `pytest_plugin`, in a module pytest never treats as a
plugin: importing the plugin module before pytest starts makes pytest warn that it cannot
rewrite it, which projects with `filterwarnings = error` turn into a fatal error."""

from __future__ import annotations

from typing import Any

#: stimulus_ref of the execution that records import and collection time
IMPORT_REF = "py:<import>"
#: the session tracer pytest_launch started before pytest imported anything, if any
TRACER: Any = None
