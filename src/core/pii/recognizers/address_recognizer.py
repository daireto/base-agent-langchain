from presidio_analyzer import Pattern, PatternRecognizer

_STREET_ADDR_PATTERN = (
    r"""
\b
(?:
    calle|cl|cll|cle|
    carrera|cra|crra|carr|cr|kr|
    avenida|av|ave|avn|avd|
    diagonal|dg|diag|dgl|
    transversal|tv|tr|trans|trv|ts|tvs|
    circular|cq|circ|cc|
    autopista|aut|auto|
    pasaje|pj|psj|paj|
    via|vía|vi|v|
    camino|cn|cam|
    carretera|crt|ctra|
    variante|vte|var|
    bulevar|blv|blvd|boulevard
)
\.?
(?:\s+[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ\-]+){0,5}
(?:\s*(?:#|no|n°|n|num|numero|número)\.?\s*)
\d+[A-Za-z]{0,2}
(?:\s*[-/]\s*\d+[A-Za-z]{0,2})?
\b
""".replace('\n', '')
    .replace(' ', '')
    .strip()
)


_PATTERNS = [
    Pattern(
        name='Street Address (weak)',
        regex=_STREET_ADDR_PATTERN,
        score=0.85,
    )
]

_CONTEXT = [
    'direccion',
    'dirección',
    'vive',
    'vivo',
    'domicilio',
    'residencia',
    'ubicado',
    'ubicada',
    'encuentro',
    'en',
]


class AddressRecognizer(PatternRecognizer):
    """Recognizes physical street addresses in Spanish.

    Examples:
        Vivo en Calle 123 # 45-67
        Estoy ubicado en Carrera 45 No. 12-34
        Mi dirección es Avenida Siempre Viva 742 #12-34
    """

    def __init__(self) -> None:
        super().__init__(
            supported_entity='ADDRESS',
            supported_language='es',
            patterns=_PATTERNS,
            context=_CONTEXT,
        )
