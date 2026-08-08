from app.domain.recommendation import Recommendation
from app.domain.recommendation_option import RecommendationOption
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChatResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	recommendation: Recommendation | None = None
	recommendations: list[RecommendationOption] | None = None
	summary: str | None = Field(default=None, min_length=1)
	message: str | None = Field(default=None, min_length=1)

	@field_validator("summary", mode="before")
	@classmethod
	def strip_summary(cls, value: str | None) -> str | None:
		return value.strip() if value is not None else None

	@field_validator("message", mode="before")
	@classmethod
	def strip_message(cls, value: str | None) -> str | None:
		return value.strip() if value is not None else None

	@model_validator(mode="after")
	def validate_response_shape(self) -> "ChatResponse":
		is_recommendation = self.recommendation is not None and self.summary is not None
		is_message = self.message is not None and self.recommendations is None
		is_options = self.recommendations is not None and self.message is not None
		if is_options and len(self.recommendations or []) != 3:
			raise ValueError("Ambiguous responses must contain exactly three recommendations")
		if sum((is_recommendation, is_message, is_options)) != 1:
			raise ValueError("Response must contain either a recommendation, options, or message")
		return self