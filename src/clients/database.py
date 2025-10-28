import structlog
from supabase.client import Client, ClientOptions

from src.config.clients import clients_config
from supabase import create_client  # type: ignore

logger = structlog.get_logger(__name__)


def get_supabase_client() -> Client:
    """
    Create Supabase client with properly configured httpx client.

    This avoids deprecation warnings about timeout/verify parameters
    by configuring them in the httpx client instead.
    """
    logger.info("Creating Supabase client", url=clients_config.supabase_url)

    # Supabase client setup
    supabase_url = clients_config.supabase_url
    supabase_key = clients_config.supabase_service_key

    # Create client with configured httpx client options
    options = ClientOptions(
        postgrest_client_timeout=60,
        storage_client_timeout=60,
    )

    supabase = create_client(  # CONST-III-001 - Centralized client factory
        supabase_url, supabase_key, options=options
    )  # CONST-III-001 - This IS the centralized client factory

    return supabase
