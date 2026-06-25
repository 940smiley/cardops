from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from cardops_api.config import AppSettings, get_settings
from cardops_api.ebay_oauth import get_ebay_oauth_config


class EbayAuthorizationRequired(RuntimeError):
    pass


class EbayApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class EbayTokenStatus:
    connected: bool
    environment: str
    token_path: str
    has_access_token: bool
    has_refresh_token: bool
    access_token_expires_at: str | None
    refresh_token_expires_at: str | None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _token_path(settings: AppSettings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.data_dir / "ebay-oauth-token.json"


def _token_endpoint(environment: str) -> str:
    if environment.strip().lower() == "production":
        return "https://api.ebay.com/identity/v1/oauth2/token"
    return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"


def _api_base(environment: str) -> str:
    if environment.strip().lower() == "production":
        return "https://api.ebay.com"
    return "https://api.sandbox.ebay.com"


def _basic_auth(settings: AppSettings) -> str:
    if not settings.ebay_client_id or not settings.ebay_client_secret:
        raise EbayAuthorizationRequired("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required.")
    raw = f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _ebay_error_detail(response: httpx.Response) -> str:
    base = f"eBay request failed with HTTP {response.status_code}."
    try:
        body = response.json()
    except ValueError:
        text = response.text.strip()
        return f"{base} {text[:300]}" if text else base
    if not isinstance(body, dict):
        return base
    safe_parts = []
    for key in ("error", "error_description"):
        value = body.get(key)
        if value:
            safe_parts.append(f"{key}={value}")
    errors = body.get("errors")
    if isinstance(errors, list):
        for error in errors[:3]:
            if isinstance(error, dict):
                message = error.get("message") or error.get("longMessage")
                error_id = error.get("errorId")
                if message:
                    prefix = f"errorId={error_id}, " if error_id else ""
                    safe_parts.append(f"{prefix}message={message}")
    return f"{base} {'; '.join(safe_parts)}" if safe_parts else base


def _ebay_response_error_detail(response: httpx.Response, *, path: str) -> str:
    detail = _ebay_error_detail(response)
    return detail.replace("eBay request failed", f"eBay API request failed for {path}", 1)


def _load_token(settings: AppSettings | None = None) -> dict[str, Any]:
    path = _token_path(settings)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_token(token: dict[str, Any], settings: AppSettings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = _token_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_token(settings)
    merged = {**existing, **token}
    now = _utc_now()
    merged["stored_at"] = now.isoformat()
    merged["environment"] = settings.ebay_environment
    if "expires_in" in merged:
        merged["access_token_expires_at"] = (now + timedelta(seconds=int(merged["expires_in"]))).isoformat()
    if "refresh_token_expires_in" in merged:
        merged["refresh_token_expires_at"] = (
            now + timedelta(seconds=int(merged["refresh_token_expires_in"]))
        ).isoformat()
    path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
    return merged


def clear_ebay_token(settings: AppSettings | None = None) -> None:
    path = _token_path(settings)
    if path.exists():
        path.unlink()


def ebay_token_status(settings: AppSettings | None = None) -> EbayTokenStatus:
    settings = settings or get_settings()
    token = _load_token(settings)
    access_expires = _parse_datetime(token.get("access_token_expires_at"))
    connected = bool(token.get("refresh_token")) or (
        bool(token.get("access_token")) and bool(access_expires and access_expires > _utc_now())
    )
    return EbayTokenStatus(
        connected=connected,
        environment=settings.ebay_environment,
        token_path=str(_token_path(settings)),
        has_access_token=bool(token.get("access_token")),
        has_refresh_token=bool(token.get("refresh_token")),
        access_token_expires_at=token.get("access_token_expires_at"),
        refresh_token_expires_at=token.get("refresh_token_expires_at"),
    )


def _request_token(data: dict[str, str], settings: AppSettings) -> dict[str, Any]:
    headers = {
        "Authorization": _basic_auth(settings),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    try:
        response = httpx.post(_token_endpoint(settings.ebay_environment), data=data, headers=headers, timeout=30)
    except httpx.HTTPError as exc:
        raise EbayApiError(f"eBay token request failed: {exc}") from exc
    if response.status_code >= 400:
        raise EbayApiError(
            _ebay_error_detail(response).replace("eBay request failed", "eBay token request failed", 1),
            status_code=response.status_code,
        )
    return response.json()


def exchange_authorization_code(code: str, settings: AppSettings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    oauth = get_ebay_oauth_config(settings)
    redirect_value = oauth.runame or oauth.redirect_uri
    token = _request_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_value,
        },
        settings,
    )
    saved = _save_token(token, settings)
    return {
        "connected": True,
        "token_type": saved.get("token_type"),
        "expires_at": saved.get("access_token_expires_at"),
        "refresh_expires_at": saved.get("refresh_token_expires_at"),
        "scope": saved.get("scope"),
    }


def _refresh_access_token(settings: AppSettings, token: dict[str, Any]) -> dict[str, Any]:
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise EbayAuthorizationRequired("No eBay refresh token is stored. Connect eBay first.")
    oauth = get_ebay_oauth_config(settings)
    refreshed = _request_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(oauth.scopes),
        },
        settings,
    )
    refreshed.setdefault("refresh_token", refresh_token)
    if token.get("refresh_token_expires_at"):
        refreshed.setdefault("refresh_token_expires_at", token["refresh_token_expires_at"])
    return _save_token(refreshed, settings)


def get_access_token(settings: AppSettings | None = None) -> str:
    settings = settings or get_settings()
    token = _load_token(settings)
    access_token = token.get("access_token")
    access_expires = _parse_datetime(token.get("access_token_expires_at"))
    if access_token and access_expires and access_expires > _utc_now() + timedelta(seconds=90):
        return str(access_token)
    refreshed = _refresh_access_token(settings, token)
    access_token = refreshed.get("access_token")
    if not access_token:
        raise EbayAuthorizationRequired("No eBay access token is available. Connect eBay first.")
    return str(access_token)


def _get_ebay_json(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    access_token = get_access_token(settings)
    url = _api_base(settings.ebay_environment) + path
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.get(url, headers=headers, params=params, timeout=30)
    except httpx.HTTPError as exc:
        raise EbayApiError(f"eBay API request failed: {exc}") from exc
    if response.status_code >= 400:
        raise EbayApiError(_ebay_response_error_detail(response, path=path), status_code=response.status_code)
    return response.json()


def get_inventory_items(*, limit: int = 25, offset: int = 0) -> dict[str, Any]:
    return _get_ebay_json(
        "/sell/inventory/v1/inventory_item",
        params={"limit": max(1, min(limit, 200)), "offset": max(0, offset)},
    )


def get_offers(*, sku: str | None = None, limit: int = 25, offset: int = 0) -> dict[str, Any]:
    if not sku:
        raise ValueError("eBay Inventory getOffers requires a seller SKU.")
    params: dict[str, Any] = {"limit": max(1, min(limit, 200)), "offset": max(0, offset)}
    params["sku"] = sku
    return _get_ebay_json("/sell/inventory/v1/offer", params=params)


def _is_offer_not_available(exc: EbayApiError) -> bool:
    message = str(exc)
    return exc.status_code == 404 and ("errorId=25713" in message or "This Offer is not available" in message)


def get_offers_for_inventory_items(inventory: dict[str, Any], *, limit: int = 25) -> dict[str, Any]:
    items = inventory.get("inventoryItems")
    if not isinstance(items, list):
        items = []
    skus = [str(item.get("sku")) for item in items if isinstance(item, dict) and item.get("sku")]
    if not skus:
        return {
            "total": 0,
            "size": 0,
            "offers": [],
            "errors": [],
            "inventoryOnlySkus": [],
            "message": "No eBay Inventory API SKUs were returned, so offer lookup was skipped.",
        }

    offers: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    inventory_only_skus: list[str] = []
    for sku in skus[: max(1, min(limit, 25))]:
        try:
            response = get_offers(sku=sku, limit=25, offset=0)
        except EbayApiError as exc:
            if _is_offer_not_available(exc):
                inventory_only_skus.append(sku)
                continue
            errors.append({"sku": sku, "error": str(exc)})
            continue
        sku_offers = response.get("offers")
        if isinstance(sku_offers, list):
            offers.extend([offer for offer in sku_offers if isinstance(offer, dict)])

    return {
        "total": len(offers),
        "size": len(offers),
        "offers": offers,
        "errors": errors,
        "inventoryOnlySkus": inventory_only_skus,
        "message": None if not errors else "Some SKU offer lookups failed; see errors.",
    }
