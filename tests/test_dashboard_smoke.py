"""Smoke test of dashboard/app.py.

* If Streamlit is installed, the official ``streamlit.testing.v1.AppTest``
  runs the whole page headlessly and asserts there were no exceptions.
* Otherwise a minimal stand-in for the ``streamlit`` module is injected so the
  script's data flow (filters -> KPIs -> rules -> clusters -> SPARQL) and all
  Plotly figure construction are still executed end to end.
Requires the warehouse to exist (run ``python run_pipeline.py`` first).
"""
import runpy
import sys
import types
import warnings
from datetime import date
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"
sys.path.insert(0, str(ROOT / "src"))
from ontorisk import config  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (config.WAREHOUSE_DB.exists() or config.WAREHOUSE_DB.with_suffix(".sqlite").exists()),
    reason="run `python run_pipeline.py` first")

try:
    import streamlit  # noqa: F401
    HAVE_ST = True
except Exception:
    HAVE_ST = False
FORCE_STUB = bool(__import__("os").environ.get("ONTORISK_FORCE_STUB"))


@pytest.mark.skipif(not HAVE_ST, reason="streamlit not installed")
def test_app_runs_with_streamlit_apptest():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    kpi_html = [h.proto.body for h in at.get("html") if 'class="or-kpis"' in h.proto.body]
    assert len(kpi_html) == 1 and kpi_html[0].count('class="or-card or-kpi') == 4   # four KPI cards
    at.multiselect[0].select("West").run()
    assert not at.exception
    at.text_input(key="q").input("logistics").run()                            # global search
    assert not at.exception


class _Stub(types.SimpleNamespace):
    """Records calls; returns sensible defaults for widgets."""

    def __init__(self, log, selections=None):
        super().__init__()
        self._log, self._sel = log, selections or {}

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self._log.append((name, args, kwargs))
            label = args[0] if args else ""
            if name == "multiselect":
                return self._sel.get(label, [])
            if name in ("radio", "selectbox"):
                opts = list(args[1])
                return opts[kwargs.get("index", 0)]
            if name == "slider":
                return args[3] if len(args) > 3 else kwargs.get("value")
            if name == "date_input":
                return args[1]
            if name == "text_area":
                return args[1]
            if name == "button":
                return True
            if name == "columns":
                n = args[0] if isinstance(args[0], int) else len(args[0])
                return [_Stub(self._log, self._sel) for _ in range(n)]
            if name in ("container", "expander"):
                return _Stub(self._log, self._sel)
            if name == "Page":
                return types.SimpleNamespace(run=args[0], title=kwargs.get("title"), default=kwargs.get("default"))
            if name == "navigation":
                pages = [p for group in args[0].values() for p in group]
                return next(p for p in pages if p.default)
            if name == "segmented_control":
                return kwargs.get("default")
            if name in ("cache_data", "cache_resource"):
                if args and callable(args[0]):
                    return args[0]
                return lambda f: f
            if name == "stop":
                raise SystemExit
            return None
        if name in ("column_config", "sidebar"):
            return _Stub(self._log, self._sel)
        return call

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("selections", [{}, {"Region": ["West", "South"], "Risk type": ["weather", "logistics"]}])
def test_app_runs_with_stub(selections, monkeypatch):
    if HAVE_ST and not FORCE_STUB:
        pytest.skip("real streamlit available - AppTest covers this")
    log = []
    fake = _Stub(log, selections)
    mod = types.ModuleType("streamlit")
    mod.__getattr__ = lambda name: getattr(fake, name)
    monkeypatch.setitem(sys.modules, "streamlit", mod)
    monkeypatch.delitem(sys.modules, "ui", raising=False)   # re-import so ui.py binds to this stub
    runpy.run_path(str(APP), run_name="__main__")
    called = [c[0] for c in log]
    html = [c[1][0] for c in log if c[0] == "html"]
    assert sum(h.count('class="or-card or-kpi') for h in html) == 4   # four KPI cards
    assert called.count("plotly_chart") >= 2              # exposure trend + OLAP cube
    assert "error" not in called
