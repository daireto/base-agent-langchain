from time import monotonic
from typing import Any

from langchain_core.prompts import PromptTemplate
from langfuse import Langfuse
from langfuse.api import NotFoundError

from core.config import settings
from core.definitions import BASE_DIR, PROMPT_TEMPLATE_DIR
from core.langfuse_resources import langfuse
from core.logger import get_logger

_logger = get_logger('prompt_manager')


class PromptManager:
    """Manager for retrieving prompt templates from Langfuse or local files.

    Attributes:
        _langfuse_enabled: A boolean indicating if Langfuse is enabled.
        _templates_dir: The directory where local prompt templates are stored.
        _local_prompt_cache: A cache for storing local prompt templates with
            their last access time.
    """

    def __init__(self) -> None:
        self._langfuse_enabled = langfuse is not None
        self._templates_dir = BASE_DIR / PROMPT_TEMPLATE_DIR
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._local_prompt_cache: dict[str, tuple[float, PromptTemplate]] = {}

    @property
    def langfuse(self) -> Langfuse:
        """Get the Langfuse instance if enabled, otherwise raise an error."""
        if not langfuse:
            raise RuntimeError('Langfuse is not initialized.')
        return langfuse

    def get(self, name: str, **kwargs: str | Any) -> str:
        """Get a prompt template by name

        Either from Langfuse or from local templates.

        Args:
            name: The name of the prompt template to retrieve.
            **kwargs: Additional keyword arguments to format the prompt template.

        Returns:
            The formatted prompt template as a string.
        """
        if self._langfuse_enabled:
            return self.get_langfuse_prompt(name, **kwargs)

        return self.get_local_prompt(name, **kwargs)

    def get_langfuse_prompt(self, name: str, **kwargs: str | Any) -> str:
        """Get a prompt template from Langfuse by name.

        If the prompt template is not found in Langfuse, it will attempt to read it
        from local templates and create it in Langfuse.

        Args:
            name: The name of the prompt template to retrieve.
            **kwargs: Additional keyword arguments to format the prompt template.

        Returns:
            The formatted prompt template as a string.
        """
        try:
            prompt = self.langfuse.get_prompt(
                name=name,
                label='production',
                cache_ttl_seconds=settings.prompt.cache_ttl_seconds,
            )
        except NotFoundError:
            prompt_content = self._read_local_prompt(name)
            prompt = self.langfuse.create_prompt(
                name=name,
                prompt=prompt_content,
                type='text',
                labels=['production'],
            )
            _logger.info(
                'Prompt template not found in Langfuse.'
                ' Created it from local template.',
                template_name=name,
            )

        return prompt.compile(**kwargs).strip()

    def get_local_prompt(self, name: str, **kwargs: str | Any) -> str:
        """Get a prompt template from local templates by name.

        Args:
            name: The name of the prompt template to retrieve.
            **kwargs: Additional keyword arguments to format the prompt template.

        Returns:
            The formatted prompt template as a string.
        """
        now = monotonic()
        cached_prompt = self._local_prompt_cache.get(name)
        cache_ttl = settings.prompt.cache_ttl_seconds

        if cached_prompt and cache_ttl > 0 and now - cached_prompt[0] < cache_ttl:
            prompt = cached_prompt[1]
        else:
            prompt_content = self._read_local_prompt(name)
            prompt = PromptTemplate.from_template(prompt_content)
            if cache_ttl > 0:
                self._local_prompt_cache[name] = (now, prompt)

        if kwargs:
            return prompt.format(**kwargs).strip()

        return prompt.template.strip()

    def _read_local_prompt(self, name: str) -> str:
        """Read a local prompt template from the templates directory.

        Args:
            name: The name of the prompt template to read.

        Raises:
            FileNotFoundError: If the prompt template file does not exist in
                the templates directory.

        Returns:
            The content of the prompt template as a string.
        """
        prompt_path = self._templates_dir / f'{name}.md'
        if not prompt_path.exists():
            raise FileNotFoundError(
                f'Prompt template "{name}" not found in {self._templates_dir}.'
                f' Please make sure the prompt template is named correctly'
                f' and has a .md extension.'
            )

        with prompt_path.open('r', encoding='utf-8') as f:
            return f.read()


prompt_manager = PromptManager()
