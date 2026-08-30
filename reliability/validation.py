def validate_recovery(state: dict) -> bool:
    """Validate that recovered runtime state is usable."""
    required = state.get("status")
    return required in {"ok", "recovered"}
