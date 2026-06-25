from __future__ import annotations

from dataclasses import dataclass

from cardops_api.card_analysis import detect_tesseract
from cardops_api.config import get_settings


@dataclass(frozen=True)
class ProviderCapability:
    name: str
    status: str
    capabilities: list[str]
    limitations: list[str]


def detect_capabilities() -> list[ProviderCapability]:
    settings = get_settings()
    tesseract = detect_tesseract()
    return [
        ProviderCapability(
            name="MockEbayProvider",
            status="available",
            capabilities=["offline listing fixtures", "safe import snapshots"],
            limitations=["No live seller account access", "No publishing"],
        ),
        ProviderCapability(
            name=f"Ebay{settings.ebay_environment.title()}Provider",
            status=(
                "configured"
                if settings.ebay_client_id_present and settings.ebay_client_secret_present
                else "missing_credentials"
            ),
            capabilities=["OAuth", "seller sync", "listing import", "Sandbox publishing"],
            limitations=["Requires eBay developer credentials and explicit user authorization"],
        ),
        ProviderCapability(
            name="LocalOnlyVisionProvider",
            status="available",
            capabilities=["image metadata", "hashing", "thumbnail generation"],
            limitations=["No cloud visual card identity inference"],
        ),
        ProviderCapability(
            name="OpenAIVisionProvider",
            status=(
                "configured"
                if settings.openai_api_key_present and settings.cloud_ai_enabled
                else "disabled"
            ),
            capabilities=["structured image identity candidates", "deeper uncertain-card analysis"],
            limitations=["Cloud AI is opt-in and disabled by default"],
        ),
        ProviderCapability(
            name="TesseractOcrProvider",
            status="available" if tesseract.status == "available" else "restricted",
            capabilities=["local OCR"] if tesseract.status == "available" else [],
            limitations=[] if tesseract.status == "available" else [tesseract.detail],
        ),
        ProviderCapability(
            name="MockPricingProvider",
            status="available",
            capabilities=["demo own sale", "demo active listing", "manual values"],
            limitations=["Demo data is not live market data"],
        ),
    ]
