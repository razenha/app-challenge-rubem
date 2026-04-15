class InvalidStatusTransitionError(Exception):
    """
    Raised when a model is asked to transition between statuses that don't
    follow the allowed workflow (e.g. an invoice already CREDITED can't
    transition back to PAID).
    """

    def __init__(self, model, current_status, target_status):
        self.model = model
        self.current_status = current_status
        self.target_status = target_status
        identity = (
            f"{model.__class__.__name__}("
            f"id={model.id}, stark_id={getattr(model, 'stark_id', None)})"
        )
        super().__init__(
            f"Invalid status transition for {identity}: "
            f"{current_status!r} → {target_status!r} is not allowed."
        )
