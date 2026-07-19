import itertools

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine, EngineResult, OperatorConfig

from core.pii.engine import nlp_engine
from core.pii.handlers.base_handler import BasePIIHandler
from core.pii.operator import PlaceholderMask
from core.pii.recognizers.address_recognizer import AddressRecognizer
from core.pii.recognizers.national_id_recognizer import NationalIdRecognizer
from core.pii.vault import Vault, VaultData

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
    def __init__(self, vault: Vault) -> None:
        self._analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
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
        results = self._analyzer.analyze(
            text=text,
            language='es',
            entities=_ENTITIES,
        )

        for i, result in enumerate(sorted(results, key=lambda r: r.start)):
            merged[i] = {'original_text': text[result.start : result.end]}

        return results

    def _deanonymize_text(self, text: str, vault_data: VaultData) -> str:
        placeholders_map = vault_data['placeholders_map']

        for placeholder, original_text in placeholders_map.items():
            text = text.replace(placeholder, original_text)

        return text

    def _store_merged(self, merged: Merged, vault_key: str) -> None:
        placeholders_map = {
            i['anonymized_text']: i['original_text'] for i in merged.values()
        }
        data = VaultData(placeholders_map=placeholders_map)
        self._vault.store(vault_key, data)
