import logging
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.core.config import Settings, get_settings
from app.core.correlation import (
	CORRELATION_HEADER,
	create_correlation_id,
	get_correlation_id,
	reset_correlation_id,
	set_correlation_id,
)
from app.core.exceptions import (
	BookDataError,
	BookNotFoundError,
	ChatServiceError,
	FilterConfigurationError,
	InputRejectedError,
	InputValidationError,
	LLMClientError,
	RetrievalError,
	ToolCallError,
)
from app.core.logging_config import configure_logging
from app.core.safe_logging import safe_log
from app.services.usage_aggregation import (
	DEFAULT_MODEL_PRICING,
	UsageAggregator,
	reset_usage_aggregator,
	set_usage_aggregator,
)

DEFAULT_CORS_ORIGINS = [
	"http://localhost:5173",
	"http://127.0.0.1:5173",
	"http://localhost:3000",
	"http://127.0.0.1:3000",
]
logger = logging.getLogger("app.api")


def create_app(
	settings: Settings | None = None,
	vector_store_factory: Callable[[Path, str], object] | None = None,
) -> FastAPI:
	"""Create the API application without requiring an API key at import time."""
	application = FastAPI(title="Smart Librarian API", version="0.1.0")
	if settings is not None:
		settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
		configure_logging(
			settings.log_level,
			settings.log_file_path,
			settings.log_max_bytes,
			settings.log_backup_count,
			settings.log_console_enabled,
			settings.log_file_enabled,
		)
	origins = settings.cors_allowed_origins if settings else DEFAULT_CORS_ORIGINS
	application.add_middleware(
		CORSMiddleware,
		allow_origins=origins,
		allow_credentials=True,
		allow_methods=["GET", "POST"],
		allow_headers=["*"],
	)
	application.include_router(chat_router)

	@application.middleware("http")
	async def request_lifecycle_logging(request: Request, call_next: Any) -> Any:
		correlation_id = create_correlation_id(request.headers.get(CORRELATION_HEADER))
		token = set_correlation_id(correlation_id)
		pricing = (
			settings.model_pricing
			if settings and settings.model_pricing
			else DEFAULT_MODEL_PRICING
		)
		aggregator = UsageAggregator(pricing)
		usage_token = set_usage_aggregator(aggregator)
		started_at = perf_counter()
		max_body_bytes = settings.max_request_body_bytes if settings else 100_000
		content_length = request.headers.get("content-length")
		if (
			content_length is not None
			and content_length.isdigit()
			and int(content_length) > max_body_bytes
		):
			response = JSONResponse(
				status_code=413,
				content={"detail": "Request body exceeds the maximum allowed size."},
			)
			response.headers[CORRELATION_HEADER] = correlation_id
			reset_usage_aggregator(usage_token)
			reset_correlation_id(token)
			return response
		safe_log(
			logger,
			logging.INFO,
			"Request started",
			extra={
				"event": "request_started",
				"correlation_id": correlation_id,
				"method": request.method,
				"path": request.url.path,
			},
		)
		try:
			response = await call_next(request)
			duration_ms = round((perf_counter() - started_at) * 1_000, 2)
			safe_log(
				logger,
				logging.INFO,
				"Request completed",
				extra={
					"event": "request_completed",
					"correlation_id": correlation_id,
					"method": request.method,
					"path": request.url.path,
					"status_code": response.status_code,
					"duration_ms": duration_ms,
				},
			)
			response.headers[CORRELATION_HEADER] = correlation_id
			return response
		except Exception:
			safe_log(
				logger,
				logging.ERROR,
				"Request failed",
				extra={
					"event": "request_failed",
					"correlation_id": correlation_id,
					"method": request.method,
					"path": request.url.path,
					"duration_ms": round((perf_counter() - started_at) * 1_000, 2),
				},
				exc_info=True,
			)
			raise
		finally:
			usage_summary = aggregator.summary()
			safe_log(
				logger,
				logging.INFO,
				"Request AI usage aggregated",
				extra={
					"event": "request_usage_aggregated",
					"correlation_id": correlation_id,
					"input_tokens": usage_summary.input_tokens,
					"output_tokens": usage_summary.output_tokens,
					"total_tokens": usage_summary.total_tokens,
					"operation_count": usage_summary.operation_count,
					"estimated_cost": usage_summary.estimated_cost,
					"cost_available": usage_summary.cost_available,
					"cost_unavailable_reason": usage_summary.cost_unavailable_reason,
				},
			)
			reset_usage_aggregator(usage_token)
			reset_correlation_id(token)

	@application.exception_handler(InputValidationError)
	async def handle_input_validation(
		_request: Request, error: InputValidationError
	) -> JSONResponse:
		safe_log(
			logger,
			logging.WARNING,
			"Request rejected",
			extra={"event": "request_rejected", "correlation_id": get_correlation_id()},
		)
		return JSONResponse(status_code=400, content={"detail": str(error)})

	@application.exception_handler(InputRejectedError)
	async def handle_input_rejection(_request: Request, error: InputRejectedError) -> JSONResponse:
		return JSONResponse(status_code=400, content={"detail": str(error)})

	@application.exception_handler(BookNotFoundError)
	async def handle_missing_book(_request: Request, error: BookNotFoundError) -> JSONResponse:
		return JSONResponse(status_code=404, content={"detail": str(error)})

	async def handle_service_failure(_request: Request, _error: Exception) -> JSONResponse:
		return JSONResponse(
			status_code=502,
			content={"detail": "The recommendation service is temporarily unavailable."},
		)

	application.add_exception_handler(LLMClientError, handle_service_failure)
	application.add_exception_handler(RetrievalError, handle_service_failure)
	application.add_exception_handler(ToolCallError, handle_service_failure)
	application.add_exception_handler(ChatServiceError, handle_service_failure)
	application.add_exception_handler(BookDataError, handle_service_failure)
	application.add_exception_handler(FilterConfigurationError, handle_service_failure)

	@application.get("/health", tags=["health"])
	def health() -> dict[str, str]:
		return {"status": "ok"}

	@application.get("/ready", tags=["health"])
	def ready() -> dict[str, str]:
		try:
			factory = vector_store_factory
			readiness_settings = settings or get_settings()
			if not readiness_settings.openai_api_key.get_secret_value().strip():
				raise ValueError("OpenAI API key is empty")
			if not readiness_settings.book_data_path.is_file():
				raise FileNotFoundError("Book data is unavailable")
			if not readiness_settings.filter_config_path.is_file():
				raise FileNotFoundError("Filter configuration is unavailable")

			if factory is None:
				from app.services.chroma_store import ChromaVectorStore

				factory = ChromaVectorStore
			factory(
				readiness_settings.chroma_persist_directory,
				readiness_settings.chroma_collection_name,
			)
		except Exception as error:
			application.state.readiness_error_type = type(error).__name__
			from fastapi import HTTPException

			raise HTTPException(
				status_code=503,
				detail="The application is not ready.",
			) from error
		application.state.readiness_error_type = None
		return {"status": "ready"}

	return application


app = create_app()