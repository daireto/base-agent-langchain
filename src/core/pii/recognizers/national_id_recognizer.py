from presidio_analyzer import Pattern, PatternRecognizer

_PATTERNS = [
    Pattern(
        name='National ID (weak)',
        regex=r'\b\d{6,10}\b',
        score=0.35,
    ),
]

_CONTEXT = [
    'cc',
    'c.c',
    'cedula',
    'cédula',
    'dni',
    'documento',
    'identificacion',
    'identificación',
    'numero de documento',
    'número de documento',
    'doc',
    'id',
]


class NationalIdRecognizer(PatternRecognizer):
    """Recognizes national ID numbers used in Spanish-speaking countries.

    Examples:
        CC 1020304050
        Cédula 1020304050
        DNI 12345678
        Documento 123456789
        Identificación 123456789
    """

    def __init__(self) -> None:
        super().__init__(
            supported_entity='NATIONAL_ID',
            supported_language='es',
            patterns=_PATTERNS,
            context=_CONTEXT,
        )
