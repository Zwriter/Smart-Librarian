from chromadb.config import System
from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class NoOpTelemetry(ProductTelemetryClient):
	"""Disable Chroma product telemetry for this self-hosted service."""

	def __init__(self, system: System) -> None:
		super().__init__(system)

	@override
	def capture(self, event: ProductTelemetryEvent) -> None:
		return
