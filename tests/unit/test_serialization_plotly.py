from __future__ import annotations

import json
import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestSerializationPlotly(unittest.TestCase):
    def test_plotly_figure_is_json_dumpable(self) -> None:
        import plotly.graph_objects as go

        from services.serialization import to_jsonable

        fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1])])
        payload = to_jsonable(fig)
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
