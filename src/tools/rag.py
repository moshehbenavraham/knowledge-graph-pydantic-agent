import os

from openai import AsyncOpenAI

from supabase.client import Client

embedding_model = os.getenv("EMBEDDING_MODEL_CHOICE") or "text-embedding-3-small"


async def get_embedding(text: str, embedding_client: AsyncOpenAI) -> list[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await embedding_client.embeddings.create(model=embedding_model, input=text)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error


async def retrieve_relevant_documents_tool(
    supabase: Client, embedding_client: AsyncOpenAI, user_query: str
) -> str:
    """
    Function to retrieve relevant document chunks with RAG.
    This is called by the retrieve_relevant_documents tool for the agent.

    Returns:
        List[str]: List of relevant document chunks with metadata
    """
    try:
        # Get the embedding for the query
        query_embedding = await get_embedding(user_query, embedding_client)

        # Query Supabase for relevant documents
        result = supabase.rpc(
            "match_documents", {"query_embedding": query_embedding, "match_count": 4}
        ).execute()

        if not result.data:
            return "No relevant documents found."

        # Format the results
        formatted_chunks = []
        for doc in result.data:
            chunk_text = f"""
# Document ID: {doc['metadata'].get('file_id', 'unknown')}
# Document Title: {doc['metadata'].get('file_title', 'unknown')}
# Document URL: {doc['metadata'].get('file_url', 'unknown')}

{doc['content']}
"""
            formatted_chunks.append(chunk_text)

        # Join all chunks with a separator
        return "\n\n---\n\n".join(formatted_chunks)

    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return f"Error retrieving documents: {e!s}"


async def list_documents_tool(supabase: Client) -> list[str]:
    """
    Function to retrieve a list of all available documents.
    This is called by the list_documents tool for the agent.

    Returns:
        List[str]: List of documents including their metadata (URL/path, source, etc.)
    """
    try:
        # Query Supabase for unique documents from the documents table
        result = supabase.from_("documents").select("id, title, source, created_at").execute()

        if not result.data:
            return []

        # Format the data as a list of strings
        documents = []
        for doc in result.data:
            doc_str = f"Title: {doc.get('title', 'Untitled')}, Source: {doc.get('source', 'N/A')}"
            documents.append(doc_str)

        return documents

    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return []


async def get_document_content_tool(supabase: Client, document_id: str) -> str:
    """
    Retrieve the full content of a specific document by combining all its chunks.
    This is called by the get_document_content tool for the agent.

    Returns:
        str: The complete content of the document with all chunks combined in order
    """
    try:
        # Query Supabase for all chunks for this document
        result = (
            supabase.from_("documents")
            .select("id, content, metadata")
            .eq("metadata->>file_id", document_id)
            .order("id")
            .execute()
        )

        if not result.data:
            return f"No content found for document: {document_id}"

        # Format the document with its title and all chunks
        document_title = result.data[0]["metadata"]["file_title"].split(" - ")[
            0
        ]  # Get the main title
        formatted_content = [f"# {document_title}\n"] + [chunk["content"] for chunk in result.data]

        # Join everything together but limit the characters in case the document is massive
        return "\n\n".join(formatted_content)[:20000]

    except Exception as e:
        print(f"Error retrieving document content: {e}")
        return f"Error retrieving document content: {e!s}"
