from __future__ import annotations

import matplotlib


# Tests generate files and never require an interactive window.  Force a
# deterministic headless backend so CI and Windows systems without Tcl/Tk do
# not fail before the reporting assertions are reached.
matplotlib.use("Agg", force=True)
