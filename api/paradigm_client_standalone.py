"""
Standalone Paradigm API Client
================================

This file is a complete, self-contained Paradigm API client that can be copied
directly into client applications without any dependencies on the main codebase.

Purpose:
--------
This client will be included in generated workflow packages, allowing clients
to run workflows independently with full Paradigm API support.

Features:
---------
- Complete Paradigm API integration (search, analysis, chat, file upload)
- Asynchronous polling for long-running document analysis
- VisionDocumentSearch fallback for robust extraction
- Zero external dependencies (except aiohttp and standard library)

Usage in Client Packages:
--------------------------
When generating a standalone workflow package for a client, this entire file
is copied into the package. The client only needs to:
1. Set their API key
2. Import ParadigmClient
3. Use it in their workflow

Example:
--------
```python
from paradigm_client_standalone import ParadigmClient

# Initialize
paradigm = ParadigmClient(
    api_key="client_api_key_here",
    base_url="https://paradigm.lighton.ai"
)

# Use it
result = await paradigm.document_search("Find total amount", file_ids=[123])
analysis = await paradigm.analyze_documents_with_polling(
    "Analyze invoice",
    document_ids=[123, 456]
)
```

Version: 1.0.0
Date: 2025-11-21
Author: LightOn Workflow Builder Team
"""

import aiohttp
import asyncio
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ParadigmClient:
    """
    Complete standalone client for LightOn Paradigm API.

    This client can be copied as-is into any Python project and provides
    full access to Paradigm's document search, analysis, and chat capabilities.

    Attributes:
        api_key (str): Your Paradigm API authentication key
        base_url (str): The Paradigm API base URL (usually https://api.lighton.ai)
        headers (dict): HTTP headers for authentication

    Example:
        >>> client = ParadigmClient(api_key="sk-...", base_url="https://api.lighton.ai")
        >>> result = await client.document_search("Find the invoice total", file_ids=[123])
        >>> print(result["answer"])
    """

    def __init__(self, api_key: str, base_url: str = "https://paradigm.lighton.ai"):
        """
        Initialize the Paradigm client.

        Args:
            api_key: Your secret API key from Paradigm
            base_url: The Paradigm API address (default: https://paradigm.lighton.ai)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info(f"✅ ParadigmClient initialized: {base_url}")

    async def document_search(
        self,
        query: str,
        file_ids: Optional[List[int]] = None,
        workspace_ids: Optional[List[int]] = None,
        chat_session_id: Optional[str] = None,
        model: Optional[str] = None,
        company_scope: bool = False,
        private_scope: bool = True,
        tool: str = "DocumentSearch",
        private: bool = True
    ) -> Dict[str, Any]:
        """
        Search through documents using semantic search.

        Args:
            query: Your search question (e.g., "What is the total amount?")
            file_ids: Which files to search in (e.g., [123, 456])
            workspace_ids: Which workspaces to search (optional)
            chat_session_id: Chat session for context (optional)
            model: Specific AI model to use (optional)
            company_scope: Search company-wide documents
            private_scope: Search private documents
            tool: Search method ("DocumentSearch" or "VisionDocumentSearch")
            private: Whether this request is private

        Returns:
            dict: Search results with "answer", "documents", and metadata

        Note:
            If tool="VisionDocumentSearch", it analyzes documents as images
            instead of text. Useful for scanned or complex documents.
        """
        endpoint = f"{self.base_url}/api/v2/chat/document-search"

        payload = {
            "query": query,
            "company_scope": company_scope,
            "private_scope": private_scope,
            "tool": tool,
            "private": private
        }

        if file_ids:
            payload["file_ids"] = file_ids
        if workspace_ids:
            payload["workspace_ids"] = workspace_ids
        if chat_session_id:
            payload["chat_session_id"] = chat_session_id
        if model:
            payload["model"] = model

        try:
            logger.info(f"🔍 Document Search: {query[:50]}... (tool={tool})")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Search completed: {len(result.get('documents', []))} documents")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Search failed: {response.status} - {error_text}")
                        raise Exception(f"Document search failed: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"❌ Search error: {str(e)}")
            raise

    async def search_with_vision_fallback(
        self,
        query: str,
        file_ids: Optional[List[int]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Smart search with automatic fallback to VisionDocumentSearch.

        Tries normal search first, then falls back to vision search if results
        are unclear or empty. Vision search is more robust for scanned documents,
        complex layouts, and poor OCR quality.

        Args:
            query: Search question
            file_ids: Files to search in
            **kwargs: Additional search parameters

        Returns:
            dict: Search results from whichever method succeeded
        """
        try:
            logger.info("🔍 Smart search: trying normal search first...")

            # Try normal search
            result = await self.document_search(
                query,
                file_ids=file_ids,
                tool="DocumentSearch",
                **kwargs
            )

            # Check result quality
            answer = result.get("answer", "").strip()
            has_documents = len(result.get("documents", [])) > 0
            failure_indicators = ["not found", "no information", "cannot find", "unable to", "n/a"]
            seems_unsuccessful = any(indicator in answer.lower() for indicator in failure_indicators)

            if answer and has_documents and not seems_unsuccessful:
                logger.info("✅ Normal search succeeded")
                return result

            # Fallback to vision
            logger.info("⚠️ Normal search unclear, trying vision fallback...")
            vision_result = await self.document_search(
                query,
                file_ids=file_ids,
                tool="VisionDocumentSearch",
                **kwargs
            )

            logger.info("✅ Vision search completed")
            return vision_result

        except Exception as e:
            logger.error(f"❌ Smart search failed: {str(e)}")
            raise

    async def document_analysis_start(
        self,
        query: str,
        document_ids: List[int],
        model: Optional[str] = None,
        private: bool = True
    ) -> str:
        """
        Start a document analysis job (asynchronous).

        Returns a chat_response_id that can be used to poll for results.

        Args:
            query: Analysis question or instruction
            document_ids: Which documents to analyze
            model: Specific AI model (optional)
            private: Whether analysis should be private

        Returns:
            str: chat_response_id (tracking number for this analysis)
        """
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis"

        payload = {
            "query": query,
            "document_ids": document_ids
        }

        if model:
            payload["model"] = model

        try:
            logger.info(f"📊 Starting analysis: {query[:50]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        chat_response_id = result.get("chat_response_id")
                        logger.info(f"✅ Analysis started: {chat_response_id}")
                        return chat_response_id
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Analysis start failed: {response.status}")
                        raise Exception(f"Failed to start analysis: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"❌ Analysis start error: {str(e)}")
            raise

    async def document_analysis_get_result(self, chat_response_id: str) -> Dict[str, Any]:
        """
        Get the result of a running document analysis.

        Args:
            chat_response_id: The tracking number from document_analysis_start

        Returns:
            dict: Analysis result with "status", "result", and metadata
        """
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis/{chat_response_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return {"status": "processing"}
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to get analysis result: {response.status}")

        except Exception as e:
            logger.error(f"❌ Get result error: {str(e)}")
            raise

    async def analyze_documents_with_polling(
        self,
        query: str,
        document_ids: List[int],
        model: Optional[str] = None,
        private: bool = True,
        max_wait_time: int = 300,
        poll_interval: int = 5
    ) -> str:
        """
        Analyze documents and automatically wait for results (with polling).

        This is the "smart" version that handles everything:
        1. Starts the analysis
        2. Waits and checks every few seconds (polling)
        3. Returns the result when ready

        Args:
            query: Your analysis question
            document_ids: Which documents to analyze
            model: Specific AI model (optional)
            private: Whether analysis is private
            max_wait_time: Maximum seconds to wait (default: 300 = 5 minutes)
            poll_interval: Seconds between checks (default: 5)

        Returns:
            str: The analysis result text

        Raises:
            Exception: If analysis fails or times out

        Example:
            >>> result = await client.analyze_documents_with_polling(
            ...     "Analyze this invoice",
            ...     document_ids=[123, 456]
            ... )
            >>> print(result)  # Automatically waited for completion!
        """
        try:
            logger.info(f"📊 Analysis with polling: max={max_wait_time}s, interval={poll_interval}s")

            # Start the analysis
            chat_response_id = await self.document_analysis_start(
                query, document_ids, model, private
            )

            # Poll for results
            elapsed = 0
            while elapsed < max_wait_time:
                try:
                    result = await self.document_analysis_get_result(chat_response_id)
                    status = result.get("status", "").lower()

                    logger.info(f"🔄 Polling: {status} (elapsed: {elapsed}s)")

                    # Check if completed
                    if status in ["completed", "complete", "finished", "success"]:
                        analysis_result = result.get("result") or result.get("detailed_analysis")
                        if analysis_result:
                            logger.info(f"✅ Analysis done! ({len(analysis_result)} chars)")
                            return analysis_result
                        else:
                            return "Analysis completed but no result was returned"

                    # Check if failed
                    elif status in ["failed", "error"]:
                        logger.error(f"❌ Analysis failed: {status}")
                        raise Exception(f"Analysis failed with status: {status}")

                    # Still processing
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                except Exception as e:
                    if "not found" in str(e).lower() or "404" in str(e):
                        # Still processing
                        logger.info(f"⏳ Still running... ({elapsed}s)")
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                        continue
                    else:
                        raise

            # Timeout
            logger.error(f"⏰ Timeout after {max_wait_time}s")
            raise Exception(f"Analysis timed out after {max_wait_time} seconds")

        except Exception as e:
            logger.error(f"❌ Analysis with polling failed: {str(e)}")
            return f"Document analysis failed: {str(e)}"

    async def chat_completion(
        self,
        prompt: str,
        model: str = "alfred-4.2",
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Get a chat completion response (like ChatGPT).

        No documents involved - just a conversation with the AI.

        Args:
            prompt: Your question or instruction
            model: Which AI model to use (default: alfred-4.2)
            system_prompt: Optional instructions for the AI's behavior

        Returns:
            str: The AI's response
        """
        endpoint = f"{self.base_url}/api/v2/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages
        }

        try:
            logger.info(f"💬 Chat completion: {prompt[:50]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"]
                        logger.info(f"✅ Chat completed ({len(answer)} chars)")
                        return answer
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Chat failed: {response.status}")
                        raise Exception(f"Chat completion failed: {response.status}")

        except Exception as e:
            logger.error(f"❌ Chat error: {str(e)}")
            raise

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        collection_type: str = "private"
    ) -> Dict[str, Any]:
        """
        Upload a file to Paradigm for analysis.

        Args:
            file_content: The file data as bytes
            filename: Name of the file (e.g., "invoice.pdf")
            collection_type: Where to store ("private", "company", "workspace")

        Returns:
            dict: Upload result with file ID and metadata
        """
        endpoint = f"{self.base_url}/api/v2/files"

        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=filename)
        data.add_field('collection_type', collection_type)

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            logger.info(f"📁 Uploading: {filename} ({len(file_content)} bytes)")

            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, data=data, headers=headers) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        file_id = result.get("id") or result.get("file_id")
                        logger.info(f"✅ File uploaded: ID={file_id}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Upload failed: {response.status}")
                        raise Exception(f"File upload failed: {response.status}")

        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            raise

    async def analyze_image(
        self,
        query: str,
        document_ids: List[str],
        model: Optional[str] = None,
        private: bool = False
    ) -> str:
        """
        Analyze images using vision capabilities.

        Args:
            query: What to look for in the images
            document_ids: Image document IDs
            model: Specific vision model (optional)
            private: Privacy setting

        Returns:
            str: Analysis result
        """
        endpoint = f"{self.base_url}/api/v2/chat/image-analysis"

        payload = {
            "query": query,
            "document_ids": document_ids
        }
        if model:
            payload["model"] = model
        if private is not None:
            payload["private"] = private

        try:
            logger.info(f"🖼️ Image analysis: {query[:50]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result.get("answer", "No analysis result provided")
                        logger.info(f"✅ Image analysis completed")
                        return answer
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Image analysis failed: {response.status}")
                        raise Exception(f"Image analysis failed: {response.status}")

        except Exception as e:
            logger.error(f"❌ Image analysis error: {str(e)}")
            raise


# Module metadata
__version__ = "1.0.0"
__author__ = "LightOn Workflow Builder Team"
__all__ = ["ParadigmClient"]
