import os

from supabase import create_client  # type: ignore
from supabase.client import Client


def get_supabase_client() -> Client:
    # Supabase client setup
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase = create_client(supabase_url, supabase_key)
    return supabase
