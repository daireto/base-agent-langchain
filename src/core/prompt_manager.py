from pathlib import Path
from typing import Any

from langchain_core.prompts import PromptTemplate
from langfuse import get_client

from core.config import settings
from core.definitions import PROMPT_TEMPLATE_DIR

langfuse = get_client() if settings.use_langfuse else None


class PromptManager:
    """Manager for retrieving prompt templates from Langfuse or local files."""

    def __init__(self) -> None:
        self._langfuse_enabled = langfuse and langfuse.auth_check()
        self._templates_dir = Path(__file__).parent.parent / PROMPT_TEMPLATE_DIR
        self._templates_dir.mkdir(parents=True, exist_ok=True)

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
        """Get a prompt template from Langfuse by name."""
        if not langfuse:
            raise RuntimeError('Langfuse is not enabled. Please check your settings.')

        return langfuse.get_prompt(name).compile(**kwargs).strip()

    def get_local_prompt(self, name: str, **kwargs: str | Any) -> str:
        """Get a prompt template from local templates by name."""
        prompt_path = self._templates_dir / f'{name}.md'
        if not prompt_path.exists():
            raise FileNotFoundError(
                f'Prompt template "{name}" not found in {self._templates_dir}.'
                f' Please make sure the prompt template is named correctly'
                f' and has a .md extension.'
            )

        prompt = PromptTemplate.from_file(prompt_path, encoding='utf-8')

        if kwargs:
            return prompt.format(**kwargs).strip()

        return prompt.template.strip()


prompt_manager = PromptManager()
