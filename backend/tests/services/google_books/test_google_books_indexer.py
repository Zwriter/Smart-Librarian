from types import SimpleNamespace

from app.domain.google_book import GoogleBook
from app.services.google_books.google_books_indexer import GoogleBooksIndexer


class FakeLLM:
	def __init__(self) -> None:
		self.texts: list[str] = []

	def create_embedding(self, text: str) -> SimpleNamespace:
		self.texts.append(text)
		return SimpleNamespace(embedding=[float(len(self.texts))])


class FakeStore:
	def __init__(self, existing: set[str]) -> None:
		self.existing = existing
		self.upserted: (
			tuple[list[str], list[str], list[list[float]], list[dict[str, str]]] | None
		) = None

	def existing_ids(self, ids: list[str]) -> set[str]:
		return set(ids) & self.existing

	def upsert(
		self,
		ids: list[str],
		documents: list[str],
		embeddings: list[list[float]],
		metadatas: list[dict[str, str]],
	) -> set[str]:
		self.upserted = (ids, documents, embeddings, metadatas)
		return self.existing


def make_book(volume_id: str) -> GoogleBook:
	return GoogleBook(volume_id=volume_id, title=f"Book {volume_id}", authors=("Author",))


def test_indexer_embeds_and_upserts_only_new_volume_ids() -> None:
	llm = FakeLLM()
	store = FakeStore({"google-volume:cached"})

	GoogleBooksIndexer(llm, store).index((make_book("cached"), make_book("new")))

	assert len(llm.texts) == 1
	assert store.upserted is not None
	assert store.upserted[0] == ["google-volume:new"]
	assert store.upserted[3][0]["source"] == "google_books"


def test_indexer_does_not_embed_when_all_volume_ids_exist() -> None:
	llm = FakeLLM()
	store = FakeStore({"google-volume:cached"})

	GoogleBooksIndexer(llm, store).index((make_book("cached"),))

	assert llm.texts == []
	assert store.upserted is None


def test_indexer_ignores_empty_book_results() -> None:
	llm = FakeLLM()
	store = FakeStore(set())

	GoogleBooksIndexer(llm, store).index(())

	assert llm.texts == []
	assert store.upserted is None


def test_indexer_deduplicates_duplicate_volume_ids_before_embedding() -> None:
	llm = FakeLLM()
	store = FakeStore(set())

	GoogleBooksIndexer(llm, store).index((make_book("new"), make_book("new")))

	assert len(llm.texts) == 1
	assert store.upserted is not None
	assert store.upserted[0] == ["google-volume:new"]