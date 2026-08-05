from pathlib import Path

from app.services.book_repository import BookRepository
from app.services.ingestion_service import IngestionService


class FakeLLM:
	def create_embedding(self, text: str) -> list[float]:
		return [float(len(text))]


class FakeStore:
	def upsert(self, ids, documents, embeddings, metadatas):
		self.records = (ids, documents, embeddings, metadatas)
		return {ids[0]}


def test_ingestion_is_repeatable_and_reports_added_and_updated(tmp_path: Path) -> None:
	data_path = tmp_path / "books.json"
	data_path.write_text(
		'[{"title":"Book","author":"Author","summary":"Summary"}]', encoding="utf-8"
	)
	store = FakeStore()
	service = IngestionService(BookRepository(data_path), FakeLLM(), store)

	report = service.ingest()

	assert report.added == 0
	assert report.updated == 1
	assert report.skipped == 0
	assert report.failed == 0
	assert store.records[3][0]["title"] == "Book"