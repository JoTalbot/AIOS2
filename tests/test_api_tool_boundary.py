from api.app import create_app


def test_control_plane_has_no_direct_tool_execution_route():
    app = create_app(operator_validator=lambda request: object())
    routes = {getattr(route, "path", "") for route in app.routes}
    assert not any("/tool" in path and path not in {"/health", "/ready"} for path in routes)
