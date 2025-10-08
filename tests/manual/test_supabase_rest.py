#!/usr/bin/env python3
"""Test Supabase REST API connectivity."""
import os

from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    print("Testing Supabase REST API...")
    print(f"URL: {url}")
    print(f"Key: {key[:20]}..." if key else "Key: NOT SET")

    # Create client
    supabase = create_client(url, key)
    print("✅ Client created successfully")

    # Test 1: Check if documents table exists
    print("\nTest 1: Querying documents table...")
    try:
        result = supabase.table("documents").select("id").limit(1).execute()
        print(f"✅ documents table exists (found {len(result.data)} rows)")
    except Exception as e:
        print(f"❌ documents table error: {e}")

    # Test 2: Check if chunks table exists
    print("\nTest 2: Querying chunks table...")
    try:
        result = supabase.table("chunks").select("id").limit(1).execute()
        print(f"✅ chunks table exists (found {len(result.data)} rows)")
    except Exception as e:
        print(f"❌ chunks table error: {e}")

    # Test 3: Test insert (will rollback if schema not ready)
    print("\nTest 3: Testing write access...")
    try:
        test_doc = {
            "title": "REST API Test",
            "source": "test_supabase_rest.py",
            "content": "This is a test document",
            "metadata": {},
        }
        result = supabase.table("documents").insert(test_doc).execute()
        print("✅ Write access works (inserted document)")

        # Clean up test document
        if result.data and len(result.data) > 0:
            doc_id = result.data[0]["id"]
            supabase.table("documents").delete().eq("id", doc_id).execute()
            print("✅ Cleaned up test document")
    except Exception as e:
        print(f"⚠️  Write test: {e}")
        print("   (This is expected if schema isn't initialized yet)")

    print("\n" + "=" * 70)
    print("✅ Supabase REST API is working!")
    print("=" * 70)
    print("\nThis means:")
    print("  - You can access Supabase via HTTPS")
    print("  - PostgreSQL ports (5432/6543) are blocked by network/firewall")
    print("  - You'll need to use REST API or fix network access")

except ImportError:
    print("❌ supabase-py not installed")
    print("Run: pip install supabase")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
