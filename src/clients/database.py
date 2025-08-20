from supabase import Client
import os

def get_supabase_client():
    # Supabase client setup
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase = Client(supabase_url, supabase_key)
    return supabase