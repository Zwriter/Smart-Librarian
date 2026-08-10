from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

InputSafetyCategory = Literal[
	"allowed",
	"profanity",
	"obscene",
	"prompt_injection",
	"unsafe",
]


class InputSafetyResult(BaseModel):
	model_config = ConfigDict(extra="forbid")

	allowed: bool
	category: InputSafetyCategory
	reason: str | None = Field(default=None, max_length=200)

	@model_validator(mode="after")
	def validate_consistency(self) -> "InputSafetyResult":
		if self.allowed != (self.category == "allowed"):
			raise ValueError("Safety result allowed flag conflicts with category")
		return self
