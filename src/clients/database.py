from src.config.clients import clients_config
from supabase import create_client  # type: ignore
from supabase.client import Client


def get_supabase_client() -> Client:
    # Supabase client setup
    supabase_url = clients_config.supabase_url
    supabase_key = clients_config.supabase_service_key
    supabase = create_client(supabase_url, supabase_key)
    return supabase
