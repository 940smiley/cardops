from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from cardops_api.config import AppSettings, get_settings

DEFAULT_STATE_PREFIX = "cardops"
DEFAULT_GITHUB_PAGES_OWNER = "940smiley"
DEFAULT_GITHUB_PAGES_REPO = "cardops"


@dataclass(frozen=True)
class EbayOAuthConfig:
    environment: str
    client_id: str | None
    redirect_uri: str
    runame: str | None
    scopes: list[str]
    auth_accepted_url: str
    auth_declined_url: str


def github_pages_callback_url(
    *,
    owner: str = DEFAULT_GITHUB_PAGES_OWNER,
    repo: str = DEFAULT_GITHUB_PAGES_REPO,
) -> str:
    owner = owner.strip().strip("/")
    repo = repo.strip().strip("/")
    if not owner:
        raise ValueError("GitHub owner is required.")
    if not repo:
        raise ValueError("GitHub repo is required.")
    return f"https://{owner}.github.io/{repo}/ebay/callback/"


def get_ebay_oauth_config(settings: AppSettings | None = None) -> EbayOAuthConfig:
    settings = settings or get_settings()
    expected_callback = github_pages_callback_url()
    redirect_uri = settings.ebay_redirect_uri or expected_callback
    return EbayOAuthConfig(
        environment=settings.ebay_environment,
        client_id=settings.ebay_client_id,
        redirect_uri=redirect_uri,
        runame=settings.ebay_runame,
        scopes=[scope for scope in settings.ebay_scopes.split() if scope],
        auth_accepted_url=settings.ebay_auth_accepted_url or redirect_uri,
        auth_declined_url=settings.ebay_auth_declined_url or redirect_uri,
    )


def authorization_endpoint(environment: str) -> str:
    normalized = environment.strip().lower()
    if normalized == "production":
        return "https://auth.ebay.com/oauth2/authorize"
    return "https://auth.sandbox.ebay.com/oauth2/authorize"


def generate_oauth_state(prefix: str = DEFAULT_STATE_PREFIX) -> str:
    return f"{prefix}-{secrets.token_urlsafe(24)}"


def build_authorization_url(
    *,
    client_id: str,
    redirect_value: str,
    scopes: list[str],
    environment: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_value,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{authorization_endpoint(environment)}?{urlencode(params)}"


def build_configured_authorization_url(
    settings: AppSettings | None = None,
    *,
    state: str | None = None,
) -> dict[str, str | bool | None]:
    config = get_ebay_oauth_config(settings)
    if not config.client_id:
        raise ValueError("EBAY_CLIENT_ID is not configured.")
    state = state or generate_oauth_state()

    # eBay authorization requests normally require the eBay-generated RuName in
    # redirect_uri. EBAY_REDIRECT_URI remains the real accepted/declined URL.
    redirect_value = config.runame or config.redirect_uri
    return {
        "authorization_url": build_authorization_url(
            client_id=config.client_id,
            redirect_value=redirect_value,
            scopes=config.scopes,
            environment=config.environment,
            state=state,
        ),
        "state": state,
        "redirect_uri": config.redirect_uri,
        "redirect_value_used": redirect_value,
        "runame_configured": bool(config.runame),
        "auth_accepted_url": config.auth_accepted_url,
        "auth_declined_url": config.auth_declined_url,
    }


def redact_oauth_code(code: str | None) -> dict[str, str | int | bool | None]:
    if not code:
        return {"present": False, "length": 0, "sha256": None, "prefix": None}
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return {
        "present": True,
        "length": len(code),
        "sha256": digest,
        "prefix": code[:6],
    }
