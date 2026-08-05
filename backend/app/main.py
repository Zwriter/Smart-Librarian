from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
	BookNotFoundError,
	ChatServiceError,
	InputRejectedError,
	InputValidationError,
	LLMClientError,
	RetrievalError,
	ToolCallError,
)

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def create_app(
	settings: Settings | None = None,
	vector_store_factory: Callable[[Path, str], object] | None = None,
) -> FastAPI:
	"""Create the API application without requiring an API key at import time."""
	application = FastAPI(title="Smart Librarian API", version="0.1.0")
	origins = settings.cors_allowed_origins if settings else DEFAULT_CORS_ORIGINS
	application.add_middleware(
		CORSMiddleware,
		allow_origins=origins,
		allow_credentials=True,
		allow_methods=["GET", "POST"],
		allow_headers=["*"],
	)
	application.include_router(chat_router)

	@application.exception_handler(InputValidationError)
	async def handle_input_validation(
		_request: Request, error: InputValidationError
	) -> JSONResponse:
		return JSONResponse(status_code=400, content={"detail": str(error)})

	@application.exception_handler(InputRejectedError)
	async def handle_input_rejection(_request: Request, error: InputRejectedError) -> JSONResponse:
		return JSONResponse(status_code=400, content={"detail": str(error)})

	@application.exception_handler(BookNotFoundError)
	async def handle_missing_book(_request: Request, error: BookNotFoundError) -> JSONResponse:
		return JSONResponse(status_code=404, content={"detail": str(error)})

	async def handle_service_failure(_request: Request, _error: RuntimeError) -> JSONResponse:
		return JSONResponse(
			status_code=502,
			content={"detail": "The recommendation service is temporarily unavailable."},
		)

	application.add_exception_handler(LLMClientError, handle_service_failure)
	application.add_exception_handler(RetrievalError, handle_service_failure)
	application.add_exception_handler(ToolCallError, handle_service_failure)
	application.add_exception_handler(ChatServiceError, handle_service_failure)

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
			application.state.readiness_error = error
			from fastapi import HTTPException

			raise HTTPException(
				status_code=503,
				detail="The application is not ready.",
			) from error
		application.state.readiness_error = None
		return {"status": "ready"}

	return application


app = create_app()