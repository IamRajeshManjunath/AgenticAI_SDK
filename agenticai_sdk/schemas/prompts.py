"""Prompt template configuration schema."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator


class PromptTemplateConfig(BaseModel):
    """Structural prompt schema with compile-time variable validation.

    Attributes:
        template_id: Unique identifier for the prompt template.
        template_string: The Jinja2/f-string-style template body.
        input_variables: Declared variable names expected inside the template.
    """

    template_id: str = Field(
        ...,
        min_length=1,
        description="Unique prompt template identifier.",
    )
    template_string: str = Field(
        ...,
        min_length=1,
        description="Prompt template body using {variable} placeholders.",
    )
    input_variables: list[str] = Field(
        ...,
        min_length=1,
        description="List of variable names that must appear as placeholders in the template.",
    )

    @model_validator(mode="after")
    def _validate_template_variables(self) -> "PromptTemplateConfig":
        """Ensure every declared input_variable appears in the template_string."""
        # Extract {var_name} placeholders (ignoring {{escaped}} braces)
        found_vars = set(re.findall(r"(?<!\{)\{(\w+)\}(?!\})", self.template_string))
        declared = set(self.input_variables)

        missing_in_template = declared - found_vars
        if missing_in_template:
            raise ValueError(
                f"Declared input_variables {missing_in_template} are not present "
                f"as {{placeholder}} tokens in template_string."
            )

        undeclared_in_template = found_vars - declared
        if undeclared_in_template:
            raise ValueError(
                f"Template contains placeholders {undeclared_in_template} that are "
                f"not listed in input_variables."
            )

        return self
