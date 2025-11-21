"""
Example: How to use ParadigmClient standalone in client workflows

This file demonstrates how clients will use the standalone ParadigmClient
in their deployed workflow applications.
"""

import asyncio
from paradigm_client_standalone import ParadigmClient


# Example 1: Simple document search
async def example_simple_search():
    """Search for information in uploaded documents."""

    # Initialize client (this will be done in workflow packages)
    client = ParadigmClient(
        api_key="your_api_key_here",  # Replaced with actual key in deployment
        base_url="https://api.lighton.ai"
    )

    # Search in specific files
    result = await client.document_search(
        query="What is the total amount?",
        file_ids=[123, 456]  # File IDs from uploaded documents
    )

    print(f"Answer: {result['answer']}")
    print(f"Found {len(result['documents'])} documents")


# Example 2: Search with vision fallback (robust extraction)
async def example_smart_search():
    """Use smart search with automatic vision fallback."""

    client = ParadigmClient(api_key="your_api_key_here")

    # This will automatically try vision if normal search fails
    result = await client.search_with_vision_fallback(
        query="Extract the invoice total",
        file_ids=[789]
    )

    print(f"Answer: {result['answer']}")


# Example 3: Document analysis with polling (long-running)
async def example_document_analysis():
    """Analyze documents with automatic polling."""

    client = ParadigmClient(api_key="your_api_key_here")

    # This waits automatically until analysis is done (up to 5 minutes)
    analysis = await client.analyze_documents_with_polling(
        query="Analyze this invoice and extract all key information",
        document_ids=[123, 456, 789]
    )

    print(f"Analysis result:\n{analysis}")


# Example 4: Multiple queries with fallback (like Milo's implementation)
async def example_multiple_queries_fallback():
    """Try multiple queries with fallback strategies."""

    client = ParadigmClient(api_key="your_api_key_here")

    # Try multiple query formulations
    queries = [
        "Extract the total payment amount requested in this payment request.",
        "What is the total monetary value being requested for payment?",
        "Find the payment amount or sum to be paid."
    ]

    content = ""
    for query in queries:
        result = await client.document_search(query, file_ids=[123])
        answer = result.get("answer", "").strip()

        if answer and "not found" not in answer.lower():
            content = answer
            break

    # If still no content, try vision fallback
    if not content:
        print("⚠️ Normal queries failed, trying vision...")
        result = await client.search_with_vision_fallback(
            "Extract the total payment amount",
            file_ids=[123]
        )
        content = result.get("answer", "")

    print(f"Final answer: {content}")


# Example 5: Complete workflow (like payment request validation)
async def example_complete_workflow():
    """
    Example workflow similar to Milo's payment request validation.

    This shows how all pieces work together in a real workflow.
    """
    client = ParadigmClient(api_key="your_api_key_here")

    # Assume we have file IDs from globals (injected by executor)
    attached_file_ids = [101, 102, 103]  # Example IDs

    # First file = payment request, rest = invoices
    payment_request_id = attached_file_ids[0]
    invoice_ids = attached_file_ids[1:]

    # Step 1: Extract payment amount with fallback
    payment_result = await client.search_with_vision_fallback(
        "Extract the total payment amount",
        file_ids=[payment_request_id]
    )
    payment_content = payment_result.get("answer", "")

    # Step 2: Use chat completion to extract structured data
    extraction_prompt = f"""Extract payment information as JSON:

    {{
      "total_amount": number or null,
      "currency": string or null
    }}

    Content: {payment_content}

    JSON:"""

    payment_json = await client.chat_completion(extraction_prompt)
    print(f"Payment data: {payment_json}")

    # Step 3: Process each invoice
    total_invoice_amount = 0
    for invoice_id in invoice_ids:
        invoice_result = await client.search_with_vision_fallback(
            "What is the total amount on this invoice?",
            file_ids=[invoice_id]
        )
        # Extract amount and add to total...
        print(f"Invoice {invoice_id}: {invoice_result['answer']}")

    # Step 4: Generate final report
    return f"""VALIDATION REPORT
Payment Request Amount: {payment_content}
Total Invoice Amount: {total_invoice_amount}
Status: {'PASS' if True else 'FAIL'}
"""


# Example 6: File upload and analysis
async def example_upload_and_analyze():
    """Upload a file and analyze it."""

    client = ParadigmClient(api_key="your_api_key_here")

    # Upload file
    with open("invoice.pdf", "rb") as f:
        file_content = f.read()

    upload_result = await client.upload_file(
        file_content=file_content,
        filename="invoice.pdf",
        collection_type="private"
    )

    file_id = upload_result["id"]
    print(f"File uploaded: ID={file_id}")

    # Wait a bit for processing
    await asyncio.sleep(5)

    # Search in uploaded file
    result = await client.document_search(
        "Find the invoice total",
        file_ids=[file_id]
    )

    print(f"Result: {result['answer']}")


# Main execution
async def main():
    """Run examples."""
    print("=" * 60)
    print("ParadigmClient Standalone - Usage Examples")
    print("=" * 60)

    # Uncomment the example you want to run:

    # await example_simple_search()
    # await example_smart_search()
    # await example_document_analysis()
    # await example_multiple_queries_fallback()
    # await example_complete_workflow()
    # await example_upload_and_analyze()

    print("\n✅ Examples completed!")


if __name__ == "__main__":
    # Note: In actual workflows, this will be called by the executor
    asyncio.run(main())
