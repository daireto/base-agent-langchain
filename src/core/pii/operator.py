import itertools

from presidio_anonymizer.operators import Operator, OperatorType
from presidio_anonymizer.services.validators import validate_parameter


class PlaceholderMask(Operator):
    COUNTER = 'counter'

    def operate(self, text: str, params: dict) -> str:  # noqa: ARG002
        """Mask the text with a placeholder."""
        counter = params.get(self.COUNTER)
        if counter is None:
            counter = itertools.count(1)
            params[self.COUNTER] = counter
        return f'<{params.get("entity_type")}_{next(counter)}>'

    def validate(self, params: dict | None = None) -> None:
        """Validate the parameters for mask.

        Args:
            counter (itertools.count): A counter to generate unique placeholders.
        """
        counter = params.get(self.COUNTER) if params else None
        validate_parameter(counter, self.COUNTER, itertools.count)

    def operator_name(self) -> str:
        """Return operator name."""
        return 'placeholder_mask'

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize
