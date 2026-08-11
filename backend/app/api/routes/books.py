from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_google_books_search_service
from app.domain.google_book_search import GoogleBookSearchResponse
from app.services.google_books.google_books_search import GoogleBooksSearchService

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search", response_model=GoogleBookSearchResponse)
def search_books(
	query: Annotated[str, Query(min_length=1, max_length=200)],
	service: Annotated[GoogleBooksSearchService, Depends(get_google_books_search_service)],
	limit: Annotated[int, Query(gt=0, le=40)] = 10,
) -> GoogleBookSearchResponse:
	books = service.search(query, limit)
	return GoogleBookSearchResponse(items=books, total=len(books))