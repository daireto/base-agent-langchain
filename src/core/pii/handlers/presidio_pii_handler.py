import itertools

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine, EngineResult, OperatorConfig

from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.operator import PlaceholderMask
from core.pii.recognizers.address_recognizer import AddressRecognizer
from core.pii.recognizers.national_id_recognizer import NationalIdRecognizer
from core.pii.vault import Vault, VaultData

_NLP_CONFIG = {
    'nlp_engine_name': 'spacy',
    'models': [
        {'lang_code': 'es', 'model_name': 'es_core_news_md'},
    ],
}
_ENTITIES = [
    'NATIONAL_ID',
    'ADDRESS',
    'CREDIT_CARD',
    'CRYPTO',
    'EMAIL_ADDRESS',
    'IBAN_CODE',
    # 'IP_ADDRESS',
    # 'MAC_ADDRESS',
    # 'PERSON',
    'PHONE_NUMBER',
    'MEDICAL_LICENSE',
]


Merged = dict[int, dict[str, str]]


class PresidioPIIHandler(BasePIIHandler):
    """Handler for PII detection, anonymization, and deanonymization using Presidio.

    Attributes:
        _nlp_engine: The Presidio NLP engine used for text analysis.
        _analyzer: The Presidio AnalyzerEngine used for PII detection.
        _anonymizer: The Presidio AnonymizerEngine used for PII anonymization.
        _vault: The vault used to store and retrieve original PII data.
    """

    def __init__(self, vault: Vault) -> None:
        """Initialize the PresidioPIIHandler.

        Args:
            vault: The vault used to store and retrieve original PII data.
        """
        provider = NlpEngineProvider(nlp_configuration=_NLP_CONFIG)
        self._nlp_engine = provider.create_engine()

        self._analyzer = AnalyzerEngine(
            nlp_engine=self._nlp_engine,
            supported_languages=['es'],
        )

        self._analyzer.registry.add_recognizer(NationalIdRecognizer())
        self._analyzer.registry.add_recognizer(AddressRecognizer())

        self._anonymizer = AnonymizerEngine()
        self._anonymizer.add_anonymizer(PlaceholderMask)

        self._vault = vault

    def anonymize(self, text: str, vault_key: str) -> str:
        merged = {}
        if analyzer_results := self._analyze_text(text, merged):
            anonymized = self._anonymize_text(text, analyzer_results, merged)
            self._store_merged(merged, vault_key)
            return anonymized.text

        return text

    def deanonymize(self, text: str, vault_key: str) -> str:
        if vault_data := self._vault.retrieve(vault_key):
            return self._deanonymize_text(text, vault_data)

        return text

    def clear_vault(self, vault_key: str) -> None:
        self._vault.clear(vault_key)

    def _anonymize_text(
        self,
        text: str,
        analyzer_results: list[RecognizerResult],
        merged: Merged,
    ) -> EngineResult:
        """Anonymize the text.

        Takes the original text, the results from the analyzer, and a merged dictionary
        to store the original and anonymized text.

        Args:
            text: The original text to be anonymized.
            analyzer_results: The results from the Presidio analyzer
                containing detected PII entities.
            merged: A dictionary to store the original and anonymized text.

        Returns:
            The result of the anonymization process, including the anonymized text.
        """
        anonymized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,  # type: ignore
            operators={
                e: OperatorConfig('placeholder_mask', {'counter': itertools.count(1)})
                for e in _ENTITIES
            },
        )

        for i, result in enumerate(sorted(anonymized.items, key=lambda r: r.start)):
            merged[i]['anonymized_text'] = result.text

        return anonymized

    def _analyze_text(self, text: str, merged: Merged) -> list[RecognizerResult]:
        """Analyze the text for PII entities.

        Args:
            text: The text to be analyzed for PII entities.
            merged: A dictionary to store the original text corresponding
                to detected PII entities.

        Returns:
            The list of detected PII entities.
        """
        results = self._analyzer.analyze(
            text=text,
            language='es',
            entities=_ENTITIES,
        )

        for i, result in enumerate(sorted(results, key=lambda r: r.start)):
            merged[i] = {'original_text': text[result.start : result.end]}

        return results

    def _deanonymize_text(self, text: str, vault_data: VaultData) -> str:
        """Deanonymize the text using the original PII data from the vault.

        Args:
            text: The anonymized text to be deanonymized.
            vault_data: The data retrieved from the vault containing
                the original PII information.

        Returns:
            The deanonymized text.
        """
        placeholders_map = vault_data['placeholders_map']

        for placeholder, original_text in placeholders_map.items():
            text = text.replace(placeholder, original_text)

        return text

    def _store_merged(self, merged: Merged, vault_key: str) -> None:
        """Store the merged original and anonymized text in the vault.

        Args:
            merged: A dictionary containing the original and anonymized text.
            vault_key: The key under which the data will be stored in the vault.
        """
        placeholders_map = {
            i['anonymized_text']: i['original_text'] for i in merged.values()
        }
        data = VaultData(placeholders_map=placeholders_map)
        self._vault.store(vault_key, data)
