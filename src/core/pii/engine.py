from presidio_analyzer.nlp_engine import NlpEngineProvider

_NLP_CONFIG = {
    'nlp_engine_name': 'spacy',
    'models': [
        {'lang_code': 'es', 'model_name': 'es_core_news_md'},
    ],
}

provider = NlpEngineProvider(nlp_configuration=_NLP_CONFIG)
nlp_engine = provider.create_engine()
