import uuid


class LoadingReferenceService:
    """Public loading boundary consumed by operational modules.

    Loading persistence belongs to its own occurrence. Until that module records
    a finished session, the safe answer is always false.
    """

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        del load_plan_id
        return False
