import json

from app.core.config import get_settings
from app.services.catalogue.book_repository import BookRepository
from app.services.catalogue.ingestion_service import IngestionService
from app.services.llm.llm_client import OpenAIClient
from app.services.retrieval.chroma_store import ChromaVectorStore


def main() -> None:
	settings = get_settings()
	service = IngestionService(
		repository=BookRepository(settings.book_data_path),
		llm_client=OpenAIClient(
			api_key=settings.openai_api_key.get_secret_value(),
			chat_model=settings.openai_chat_model,
			embedding_model=settings.openai_embedding_model,
		),
		vector_store=ChromaVectorStore(
			persist_directory=settings.chroma_persist_directory,
			collection_name=settings.chroma_collection_name,
		),
	)
	print(json.dumps(service.ingest().__dict__, sort_keys=True))


if __name__ == "__main__":
	main()
