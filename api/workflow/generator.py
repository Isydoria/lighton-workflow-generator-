import asyncio
import logging
import re
from typing import Optional, Dict, Any
from .models import Workflow
from anthropic import Anthropic
from ..config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# POST-PROCESSING FUNCTIONS FOR CODE GENERATION
# ============================================================================

def detect_workflow_type(description: str) -> str:
    """
    Detect workflow type based on description keywords.

    Returns:
        "extraction": Short structured documents (CV, forms, invoices) → use chat_completion()
        "summarization": Long documents (reports, articles) → use analyze_documents_with_polling()
        "unknown": Ambiguous case → default to "extraction" (faster and more reliable)
    """
    description_lower = description.lower()

    # Keywords indicating structured data extraction
    extraction_keywords = [
        'cv', 'resume', 'curriculum vitae', 'curricul',
        'form', 'formulaire', 'application',
        'invoice', 'facture', 'receipt', 'reçu',
        'extract', 'extraire', 'parse', 'parsing',
        'field', 'champ', 'structured', 'structuré',
        'candidat', 'candidate', 'recrutement', 'recruitment',
        'contract', 'contrat',
        'fiche', 'profil', 'profile'
    ]

    # Keywords indicating document summarization
    summarization_keywords = [
        'summarize', 'résumer', 'synthèse', 'synthesis',
        'long document', 'rapport', 'report',
        'research paper', 'article', 'white paper',
        'analyse approfondie', 'deep analysis',
        'comprehensive review'
    ]

    # Count keyword matches
    extraction_score = sum(1 for kw in extraction_keywords if kw in description_lower)
    summarization_score = sum(1 for kw in summarization_keywords if kw in description_lower)

    # Decision logic
    if extraction_score > 0 and extraction_score > summarization_score:
        return "extraction"
    elif summarization_score > extraction_score:
        return "summarization"
    else:
        # Default to extraction (faster, more reliable for most cases)
        return "extraction"


def count_api_calls(code: str) -> int:
    """
    Count the number of Paradigm API calls in generated code.
    Used to detect complex workflows that need staggering.
    """
    # Count async paradigm_client calls
    patterns = [
        r'await\s+paradigm_client\.\w+\(',
        r'paradigm_client\.\w+\([^)]+\)'
    ]

    total_calls = 0
    for pattern in patterns:
        matches = re.findall(pattern, code)
        total_calls += len(matches)

    return total_calls


def fix_extraction_workflow_apis(code: str, description: str) -> str:
    """
    Replace analyze_documents_with_polling() with chat_completion() + ask_question()
    for extraction workflows (CV, forms, invoices).

    This fixes the timeout issue where analyze_documents_with_polling takes 5 minutes
    instead of 5 seconds with chat_completion.
    """
    workflow_type = detect_workflow_type(description)

    if workflow_type != "extraction":
        # Not an extraction workflow, no changes needed
        return code

    if "analyze_documents_with_polling" not in code:
        # Already using correct APIs
        return code

    logger.info(f"🔧 Post-processing: Detected extraction workflow, fixing API calls")
    logger.info(f"   Description: {description[:100]}...")

    # Pattern to match: variable = await paradigm_client.analyze_documents_with_polling(query, [doc_id], ...)
    # We'll replace with chat_completion() pattern

    # Simple replacement strategy: Replace analyze_documents_with_polling with chat_completion
    # and add ask_question if needed

    fixed_code = code

    # Pattern 1: Single document analysis
    # result = await paradigm_client.analyze_documents_with_polling(query, [doc_id])
    pattern1 = r'(\s+)(\w+)\s*=\s*await\s+paradigm_client\.analyze_documents_with_polling\(\s*([^,]+),\s*\[([^\]]+)\]([^\)]*)\)'

    def replace_single_doc(match):
        indent = match.group(1)
        result_var = match.group(2)
        query_var = match.group(3).strip()
        doc_id = match.group(4).strip()

        # Generate replacement code using chat_completion
        # Note: We build the prompt string without f-string to avoid nested f-string issues
        replacement = f'''{indent}# Post-processing: Using chat_completion for fast extraction (instead of analyze_documents_with_polling)
{indent}# Get document content first
{indent}try:
{indent}    doc_content = await paradigm_client.ask_question(
{indent}        file_id=int({doc_id}),
{indent}        question="Return the full text and all structured information from this document"
{indent}    )
{indent}    # Extract structured data using chat_completion
{indent}    extraction_prompt = {query_var} + "\\n\\nDocument content:\\n" + doc_content['response']
{indent}    {result_var} = await paradigm_client.chat_completion(
{indent}        prompt=extraction_prompt,
{indent}        model="alfred-4.2"
{indent}    )
{indent}except Exception as e:
{indent}    logger.error(f"Extraction failed: {{e}}")
{indent}    {result_var} = f"Extraction error: {{str(e)}}"'''

        return replacement

    # Apply replacement
    fixed_code = re.sub(pattern1, replace_single_doc, fixed_code)

    if fixed_code != code:
        logger.info(f"✅ Post-processing: Replaced analyze_documents_with_polling with chat_completion")
        logger.info(f"   Expected speedup: 60x faster (5s instead of 300s)")

    return fixed_code


def add_staggering_to_workflow(code: str, description: str) -> str:
    """
    Add staggering (delays) between API calls for complex workflows.
    Prevents API overload and timeouts on workflows with many parallel calls.
    """
    api_call_count = count_api_calls(code)

    if api_call_count < 40:
        # Not a complex workflow, no staggering needed
        return code

    logger.info(f"🔧 Post-processing: Detected complex workflow ({api_call_count} API calls)")
    logger.info(f"   Adding staggering to prevent API overload")

    # Strategy: Add small delays between asyncio.gather() calls
    # Pattern: Find asyncio.gather() with many tasks and add delays

    # For now, we'll add a general instruction as a comment
    # More sophisticated implementation would parse AST and insert delays

    staggering_note = '''
# ⚠️ Post-processing note: This workflow has many API calls ({})
# Consider adding delays between groups of calls to prevent timeouts:
# await asyncio.sleep(2)  # Small delay between API call groups
'''.format(api_call_count)

    # Insert note after imports
    if "import asyncio" in code:
        code = code.replace("import asyncio", f"import asyncio{staggering_note}")

    logger.info(f"✅ Post-processing: Added staggering guidance for {api_call_count} API calls")

    return code


def fix_bracket_mismatches(code: str) -> str:
    """
    Detect and fix common bracket/parenthesis mismatches in generated code.

    Common patterns that cause issues:
    - await asyncio.gather(*[...]) instead of await asyncio.gather(...)
    - Mixing brackets and parentheses in function calls
    - Unmatched brackets in list comprehensions
    """
    import re

    fixed_code = code

    # Pattern 1: Fix asyncio.gather(*[...]) -> asyncio.gather(...)
    # This is a common mistake where Claude uses unpacking with list brackets
    pattern_gather = r'asyncio\.gather\(\s*\*\s*\[((?:[^[\]]*|\[[^\]]*\])*)\]\s*\)'

    def fix_gather(match):
        tasks = match.group(1)
        # Remove the unpacking operator and brackets
        return f'asyncio.gather({tasks})'

    fixed_code = re.sub(pattern_gather, fix_gather, fixed_code)

    # Pattern 2: Fix common mismatches in await statements
    # await func([...]) sometimes gets mistyped as await func(...)
    # We'll validate bracket balance on each line

    lines = fixed_code.split('\n')
    fixed_lines = []

    for line_num, line in enumerate(lines, 1):
        # Check bracket balance on this line
        if not is_balanced(line):
            # Try to fix simple cases
            fixed_line = attempt_fix_line(line)
            if is_balanced(fixed_line):
                logger.info(f"🔧 Post-processing: Fixed bracket mismatch on line {line_num}")
                fixed_lines.append(fixed_line)
            else:
                # Can't fix automatically, keep original
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    fixed_code = '\n'.join(fixed_lines)

    return fixed_code


def is_balanced(line: str) -> bool:
    """Check if brackets/parentheses are balanced on a line"""
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}

    # Skip strings to avoid false positives
    in_string = False
    escape = False
    string_char = None

    for char in line:
        if escape:
            escape = False
            continue

        if char == '\\':
            escape = True
            continue

        if char in ['"', "'"] and not in_string:
            in_string = True
            string_char = char
            continue
        elif in_string and char == string_char:
            in_string = False
            string_char = None
            continue

        if in_string:
            continue

        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack:
                return False
            opener = stack.pop()
            if pairs[opener] != char:
                return False

    return len(stack) == 0


def attempt_fix_line(line: str) -> str:
    """Attempt to automatically fix common bracket mismatches"""
    # Common fix 1: Replace ] with ) at end of function calls
    # Example: await func(...] -> await func(...)
    if 'await ' in line and line.rstrip().endswith(']'):
        # Count opening ( and [
        open_paren = line.count('(') - line.count(')')
        open_bracket = line.count('[') - line.count(']')

        if open_paren > 0 and open_bracket < 0:
            # More open ( than ), and extra closing ]
            # Replace last ] with )
            line = line.rstrip()[:-1] + ')'

    # Common fix 2: Replace ) with ] at end of list definitions
    # Example: my_list = [...) -> my_list = [...]
    if '= [' in line and line.rstrip().endswith(')'):
        open_bracket = line.count('[') - line.count(']')
        open_paren = line.count('(') - line.count(')')

        if open_bracket > 0 and open_paren < 0:
            # More open [ than ], and extra closing )
            # Replace last ) with ]
            line = line.rstrip()[:-1] + ']'

    return line


class WorkflowGenerator:
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)

    async def generate_workflow(
        self,
        description: str,
        name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Generate a workflow from a natural language description
        Args:
            description: Natural language description of the workflow
            name: Optional name for the workflow
            context: Additional context for code generation
        Returns:
            Workflow object with generated code
        """
        workflow = Workflow(
            name=name,
            description=description,
            context=context
        )
        
        try:
            workflow.update_status("generating")

            # Retry mechanism for code generation (up to 3 attempts)
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    # Generate the code using Anthropic API
                    generated_code = await self._generate_code(description, context)

                    # Validate the generated code
                    validation_result = await self._validate_code(generated_code)

                    if validation_result["valid"]:
                        # Success! Code is valid
                        workflow.generated_code = generated_code
                        workflow.update_status("ready")
                        return workflow
                    else:
                        # Validation failed, prepare for retry
                        last_error = validation_result['error']
                        if attempt < max_retries - 1:
                            # Add error context for next attempt
                            if context is None:
                                context = {}
                            context['previous_error'] = f"Previous attempt had syntax error: {last_error}"
                            continue
                        else:
                            # Last attempt failed
                            raise Exception(f"Generated code validation failed after {max_retries} attempts: {last_error}")

                except Exception as e:
                    if "validation failed" in str(e).lower():
                        # Re-raise validation errors
                        raise
                    # Other errors during generation
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        continue
                    raise

            # Should not reach here, but just in case
            raise Exception(f"Failed to generate valid code after {max_retries} attempts: {last_error}")

        except Exception as e:
            workflow.update_status("failed", str(e))
            raise e

    async def _generate_code(self, description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate Python code from workflow description
        """
        system_prompt = """You are a Python code generator for workflow automation systems.

CRITICAL INSTRUCTIONS:
1. Generate ONLY executable Python code - no markdown, no explanations, no comments
2. The code must define: async def execute_workflow(user_input: str) -> str
3. Include ALL necessary imports and API client code directly in the workflow
4. Make the workflow completely self-contained and portable
5. *** NEVER USE 'pass' OR PLACEHOLDER COMMENTS - IMPLEMENT ALL FUNCTIONS COMPLETELY ***
6. *** EVERY FUNCTION MUST BE FULLY IMPLEMENTED WITH WORKING CODE ***
7. *** NO STUB FUNCTIONS - ALL CODE MUST BE EXECUTABLE AND FUNCTIONAL ***
8. *** ALWAYS USE asyncio.gather() FOR INDEPENDENT PARALLEL TASKS - IMPROVES PERFORMANCE 3-10x ***
9. *** ParadigmClient MUST ALWAYS INCLUDE upload_file() METHOD - REQUIRED FOR FILE UPLOADS ***

REQUIRED STRUCTURE:
```python
import asyncio
import aiohttp
import json
import logging
import os
from typing import Optional, List, Dict, Any

# Configuration - reads from environment variables
LIGHTON_API_KEY = os.getenv("PARADIGM_API_KEY", "your_api_key_here")
LIGHTON_BASE_URL = os.getenv("PARADIGM_BASE_URL", "https://paradigm.lighton.ai")

logger = logging.getLogger(__name__)

class ParadigmClient:
    '''
    LightOn Paradigm API Client with session reuse for 5.55x performance improvement.

    Session reuse eliminates connection overhead (TCP handshake, SSL negotiation)
    on every API call, as recommended by Paradigm documentation.

    ⚠️ MANDATORY: ALWAYS include these methods in your generated code:
    - __init__
    - _get_session
    - close
    - document_search
    - analyze_documents_with_polling
    - document_analysis_start
    - document_analysis_get_result
    - chat_completion
    - upload_file  <-- CRITICAL: Always include this method!
    '''

    def __init__(self, api_key: str, base_url: str = "https://paradigm.lighton.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"✅ ParadigmClient initialized: {base_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        '''
        Get or create the shared aiohttp session.

        Reusing the same session across multiple requests provides 5.55x performance
        improvement by avoiding connection setup overhead on every call.

        Official benchmark (Paradigm docs):
        - With session reuse: 1.86s for 20 requests
        - Without session reuse: 10.33s for 20 requests
        '''
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.debug("🔌 Created new aiohttp session")
        return self._session

    async def close(self):
        '''
        Close the shared aiohttp session.

        IMPORTANT: Always call this method when done with the client,
        typically in a finally block to ensure cleanup.
        '''
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("🔌 Closed aiohttp session")
            self._session = None

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
        '''
        Search through documents using natural language queries.

        Args:
            query: Your search question (e.g., "What is the total amount?")
            file_ids: Which files to search in (e.g., [123, 456])
            workspace_ids: Which workspaces to search (optional)
            chat_session_id: Chat session for context (optional)
            model: Specific AI model to use (optional)
            company_scope: Search company-wide documents
            private_scope: Search private documents
            tool: Search method - "DocumentSearch" (default) or "VisionDocumentSearch"
                  Use "VisionDocumentSearch" for:
                  - Scanned documents or images
                  - Checkboxes or form fields
                  - Complex layouts or tables
                  - Poor OCR quality documents
            private: Whether this request is private

        Returns:
            dict: Search results with "answer", "documents", and metadata

        Example with Vision OCR:
            result = await paradigm_client.document_search(
                query="Quelle case est cochée dans la section C ?",
                file_ids=[123],
                tool="VisionDocumentSearch"
            )
        '''
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

            session = await self._get_session()
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
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis"

        payload = {
            "query": query,
            "document_ids": document_ids
        }

        if model:
            payload["model"] = model

        try:
            logger.info(f"📊 Starting analysis: {query[:50]}...")

            session = await self._get_session()
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
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis/{chat_response_id}"

        try:
            session = await self._get_session()
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
        '''
        Get a chat completion response (like ChatGPT).

        No documents involved - just a conversation with the AI.

        Args:
            prompt: Your question or instruction
            model: Which AI model to use (default: alfred-4.2)
            system_prompt: Optional instructions for the AI's behavior and output format
                          Use this to enforce specific formats like JSON-only responses

        Returns:
            str: The AI's response

        Example with JSON-only output:
            result = await paradigm_client.chat_completion(
                prompt="Vérifie que le nom de l'acheteur est identique dans les deux documents",
                system_prompt=\'\'\'Tu es un assistant qui réponds UNIQUEMENT au format JSON VALIDE.
                Le json doit contenir :
                "is_correct" : un booléen (true ou false)
                "details" : une phrase expliquant pourquoi la réponse est correcte ou non
                \'\'\'
            )
            # Returns: {"is_correct": true, "details": "Les noms sont identiques"}

        Example without system prompt:
            result = await paradigm_client.chat_completion(
                prompt="Explique-moi ce qu'est un SIRET"
            )
        '''
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

            session = await self._get_session()
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
        endpoint = f"{self.base_url}/api/v2/files"

        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=filename)
        data.add_field('collection_type', collection_type)

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            logger.info(f"📁 Uploading: {filename} ({len(file_content)} bytes)")

            session = await self._get_session()
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

    async def ask_question(
        self,
        file_id: int,
        question: str
    ) -> Dict[str, Any]:
        '''
        Ask a question about a specific uploaded file and get relevant chunks.

        This method is optimized for single-document queries. Use this instead of
        document_search when you're asking a question about ONE specific document.

        Endpoint: POST /api/v2/files/{id}/ask

        Args:
            file_id: The ID of the uploaded file to query
            question: The question to ask about the file

        Returns:
            Dict containing:
            - response: str - AI-generated answer to the question
            - chunks: List[Dict] - Relevant document chunks with metadata
                - id: int
                - uuid: str (e.g. "3f885f64-5747-4562-b3fc-2c963f66afa6")
                - content_id: str
                - text: str - The actual chunk text
                - metadata: Dict - Additional metadata
                - document: int - Document ID
                - chunk_type: str (e.g. "text")
                - created_at: str (ISO datetime)
                - updated_at: str (ISO datetime)

        When to use:
            ✅ Asking a question about ONE specific document
            ✅ Looping through documents individually
            ✅ Need both answer and source chunks

            ❌ Searching across MULTIPLE documents (use document_search instead)
            ❌ Need aggregated results from many files

        Example:
            # Single document query
            result = await paradigm.ask_question(
                file_id=123,
                question="What is the total amount on this invoice?"
            )
            print(f"Answer: {result['response']}")
            print(f"Found {len(result['chunks'])} relevant chunks")

            # Loop through multiple documents
            for doc_id in [123, 124, 125]:
                result = await paradigm.ask_question(
                    file_id=doc_id,
                    question="Extract the client name"
                )
                print(f"Document {doc_id}: {result['response']}")

        Raises:
            Exception: If the API call fails or returns an error

        Performance:
            Uses session reuse internally for 5.55x faster performance
            compared to creating a new session for each request.
        '''
        endpoint = f"{self.base_url}/api/v2/files/{file_id}/ask"

        payload = {
            "question": question
        }

        try:
            logger.info(f"📄 Asking question about file {file_id}")
            logger.info(f"❓ QUESTION: {question}")

            session = await self._get_session()
            async with session.post(
                endpoint,
                json=payload,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    num_chunks = len(result.get('chunks', []))
                    logger.info(f"✅ Got response with {num_chunks} chunks")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Ask question failed: {response.status}")
                    raise Exception(f"Ask question API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"❌ Ask question error: {str(e)}")
            raise

    async def filter_chunks(
        self,
        query: str,
        chunk_ids: List[str],
        n: Optional[int] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        '''
        Filter document chunks based on relevance to a query.

        This method takes a list of chunk UUIDs (typically from ask_question or
        document_search) and filters them to return only the most relevant ones
        based on semantic similarity to your query.

        Endpoint: POST /api/v2/filter/chunks

        Args:
            query: The query to filter chunks against
            chunk_ids: List of chunk UUIDs to filter (e.g., ["3f885f64-5747-4562-b3fc-2c963f66afa6", ...])
            n: Optional maximum number of chunks to return (returns top N most relevant)
            model: Optional model name to use for filtering

        Returns:
            Dict containing:
            - query: str - The original query used for filtering
            - chunks: List[Dict] - Filtered chunks sorted by relevance (highest first)
                - uuid: str - Chunk UUID
                - text: str - The chunk content
                - metadata: Dict - Additional metadata from the chunk
                - filter_score: float - Relevance score (higher = more relevant)

        When to use:
            ✅ You have many chunks from multiple documents and want only relevant ones
            ✅ Reducing noise in multi-document search results
            ✅ Need to rank chunks by relevance to a specific question
            ✅ Working with 20+ chunks and need the top 5-10

            ❌ You only have a few chunks (2-5) - filtering adds overhead
            ❌ Single document queries - ask_question already returns relevant chunks
            ❌ You need ALL chunks regardless of relevance

        Example - Basic filtering:
            # Get chunks from a document
            result = await paradigm.ask_question(
                file_id=123,
                question="Find all financial data"
            )

            # Extract chunk UUIDs
            chunk_uuids = [chunk['uuid'] for chunk in result['chunks']]

            # Filter to most relevant chunks for specific question
            filtered = await paradigm.filter_chunks(
                query="What is the total revenue?",
                chunk_ids=chunk_uuids,
                n=5  # Get top 5 most relevant
            )

            for chunk in filtered['chunks']:
                print(f"Score: {chunk['filter_score']}")
                print(f"Text: {chunk['text'][:100]}...")

        Example - Multi-document filtering:
            # Search across multiple documents
            search_result = await paradigm.document_search(
                query="Find contracts",
                file_ids=[101, 102, 103, 104, 105]
            )

            # Extract all chunk IDs from search results
            all_chunks = []
            for doc in search_result.get('documents', []):
                all_chunks.extend(doc.get('chunks', []))

            chunk_uuids = [chunk['uuid'] for chunk in all_chunks]

            # Filter to find chunks specifically about pricing
            pricing_chunks = await paradigm.filter_chunks(
                query="What are the pricing terms and payment conditions?",
                chunk_ids=chunk_uuids,
                n=10
            )

            print(f"Filtered {len(chunk_uuids)} chunks down to {len(pricing_chunks['chunks'])}")

        Example - Without session reuse (automatic):
            filtered = await paradigm.filter_chunks(
                query="technical specifications",
                chunk_ids=["uuid1", "uuid2", "uuid3"]
            )
            # Session reuse happens automatically via self._get_session()

        Raises:
            Exception: If the API call fails or returns an error

        Performance:
            Uses session reuse internally for 5.55x faster performance
            when making multiple filter_chunks calls in sequence.

        Impact:
            +20% precision on multi-document queries by removing irrelevant chunks
            and focusing on the most semantically similar content.
        '''
        endpoint = f"{self.base_url}/api/v2/filter/chunks"

        payload = {
            "query": query,
            "chunk_ids": chunk_ids
        }

        if n is not None:
            payload["n"] = n
        if model is not None:
            payload["model"] = model

        try:
            logger.info(f"🔍 Filtering {len(chunk_ids)} chunks")
            logger.info(f"❓ QUERY: {query}")

            session = await self._get_session()
            async with session.post(
                endpoint,
                json=payload,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    num_filtered = len(result.get('chunks', []))
                    logger.info(f"✅ Filter returned {num_filtered} chunks")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Filter chunks failed: {response.status}")
                    raise Exception(f"Filter chunks API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"❌ Filter chunks error: {str(e)}")
            raise

    async def get_file_chunks(
        self,
        file_id: int
    ) -> Dict[str, Any]:
        '''
        Retrieve all chunks for a given document file.

        Endpoint: GET /api/v2/files/{id}/chunks

        Args:
            file_id: The ID of the file to retrieve chunks from

        Returns:
            Dict containing document chunks and metadata

        Example:
            result = await paradigm.get_file_chunks(file_id=123)
            print(f"Found {len(result.get('chunks', []))} chunks")

        Performance:
            Uses session reuse internally for 5.55x faster performance
        '''
        endpoint = f"{self.base_url}/api/v2/files/{file_id}/chunks"

        try:
            logger.info(f"📄 Getting chunks for file {file_id}")

            session = await self._get_session()
            async with session.get(
                endpoint,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    num_chunks = len(result.get('chunks', []))
                    logger.info(f"✅ Retrieved {num_chunks} chunks from file {file_id}")
                    return result

                elif response.status == 404:
                    error_text = await response.text()
                    logger.error(f"❌ File {file_id} not found")
                    raise Exception(f"File {file_id} not found: {error_text}")

                else:
                    error_text = await response.text()
                    logger.error(f"❌ Get file chunks failed: {response.status}")
                    raise Exception(f"Get file chunks API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"❌ Get file chunks error: {str(e)}")
            raise

    async def query(
        self,
        query: str,
        collection: Optional[str] = None,
        n: Optional[int] = None
    ) -> Dict[str, Any]:
        '''
        Extract relevant chunks from knowledge base without AI-generated response.

        This endpoint retrieves semantically relevant chunks based on your query
        WITHOUT generating a synthetic answer. Use this when you only need the raw
        chunks for further processing, saving time and tokens compared to document_search.

        Endpoint: POST /api/v2/query

        Args:
            query: Search query (can be single string or list of strings)
            collection: Collection to query (defaults to base_collection if not specified)
            n: Number of chunks to return (defaults to 5 if not specified)

        Returns:
            Dict containing:
            - query: str - The original query
            - chunks: List[Dict] - Relevant chunks sorted by relevance
                - uuid: str - Chunk UUID
                - text: str - Chunk content
                - metadata: Dict - Additional chunk metadata
                - score: float - Relevance score (higher = more relevant)

        When to use:
            ✅ Need raw chunks without AI synthesis
            ✅ Processing chunks yourself (data extraction, pattern matching)
            ✅ Want to save time and tokens (no text generation)
            ✅ Building custom processing pipelines

            ❌ Need a synthesized answer - use document_search instead
            ❌ Need contextual summary - use document_search instead

        Example:
            # Get top 10 relevant chunks without AI response
            result = await paradigm.query(
                query="Find invoice amounts and dates",
                n=10
            )

            for chunk in result['chunks']:
                print(f"Score: {chunk['score']}")
                print(f"Text: {chunk['text']}")

        Performance:
            Uses session reuse internally for 5.55x faster performance
            ~30% faster than document_search (no AI generation overhead)
        '''
        endpoint = f"{self.base_url}/api/v2/query"

        payload = {"query": query}

        if collection is not None:
            payload["collection"] = collection
        if n is not None:
            payload["n"] = n

        try:
            logger.info(f"🔍 Querying knowledge base: {query}")
            if n:
                logger.info(f"📊 Requesting top {n} chunks")

            session = await self._get_session()
            async with session.post(
                endpoint,
                json=payload,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    num_chunks = len(result.get('chunks', []))
                    logger.info(f"✅ Query returned {num_chunks} chunks")
                    return result

                else:
                    error_text = await response.text()
                    logger.error(f"❌ Query failed: {response.status}")
                    raise Exception(f"Query API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"❌ Query error: {str(e)}")
            raise

    async def get_file(
        self,
        file_id: int,
        include_content: bool = False
    ) -> Dict[str, Any]:
        '''
        Retrieve file metadata and status from Paradigm.

        Endpoint: GET /api/v2/files/{id}

        Args:
            file_id: The ID of the file to retrieve
            include_content: Include the file content in the response (default: False)

        Returns:
            Dict containing file metadata including status field

        Example:
            file_info = await paradigm.get_file(file_id=123)
            print(f"Status: {file_info['status']}")

        Performance:
            Uses session reuse internally for 5.55x faster performance
        '''
        endpoint = f"{self.base_url}/api/v2/files/{file_id}"

        params = {}
        if include_content:
            params["include_content"] = "true"

        try:
            logger.info(f"📄 Getting file info for ID {file_id}")

            session = await self._get_session()
            async with session.get(
                endpoint,
                params=params,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    status = result.get('status', 'unknown')
                    filename = result.get('filename', 'N/A')
                    logger.info(f"✅ File {file_id} ({filename}): status={status}")
                    return result

                elif response.status == 404:
                    error_text = await response.text()
                    logger.error(f"❌ File {file_id} not found")
                    raise Exception(f"File {file_id} not found: {error_text}")

                else:
                    error_text = await response.text()
                    logger.error(f"❌ Get file failed: {response.status}")
                    raise Exception(f"Get file API error {response.status}: {error_text}")

        except Exception as e:
            logger.error(f"❌ Get file error: {str(e)}")
            raise

    async def wait_for_embedding(
        self,
        file_id: int,
        max_wait_time: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        '''
        Wait for a file to be fully embedded and ready for use.

        Args:
            file_id: The ID of the file to wait for
            max_wait_time: Maximum time to wait in seconds (default: 300)
            poll_interval: Time between status checks in seconds (default: 2)

        Returns:
            Dict: Final file info when status is 'embedded'

        Example:
            file_info = await paradigm.wait_for_embedding(file_id=123)
            print(f"File ready: {file_info['filename']}")

        Performance:
            Uses session reuse internally for efficient polling (5.55x faster)
        '''
        try:
            logger.info(f"⏳ Waiting for file {file_id} to be embedded (max={max_wait_time}s, interval={poll_interval}s)")

            elapsed = 0
            while elapsed < max_wait_time:
                file_info = await self.get_file(file_id)
                status = file_info.get('status', '').lower()
                filename = file_info.get('filename', 'N/A')

                logger.info(f"🔄 File {file_id} ({filename}): status={status} (elapsed: {elapsed}s)")

                if status == 'embedded':
                    logger.info(f"✅ File {file_id} is embedded and ready!")
                    return file_info

                elif status == 'failed':
                    logger.error(f"❌ File {file_id} embedding failed")
                    raise Exception(f"File {file_id} embedding failed")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            logger.error(f"⏰ Timeout waiting for file {file_id} after {max_wait_time}s")
            raise Exception(f"Timeout waiting for file {file_id} to be embedded")

        except Exception as e:
            logger.error(f"❌ Wait for embedding error: {str(e)}")
            raise

    async def analyze_image(
        self,
        query: str,
        document_ids: List[str],
        model: Optional[str] = None,
        private: bool = False
    ) -> str:
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

            session = await self._get_session()
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



# Initialize clients
paradigm_client = ParadigmClient(LIGHTON_API_KEY, LIGHTON_BASE_URL)

async def execute_workflow(user_input: str) -> str:
    '''
    Main workflow execution function.

    IMPORTANT: Always close the paradigm_client session when done,
    using a try/finally block to ensure cleanup even if errors occur.
    '''
    try:
        # Your workflow implementation here
        pass
    finally:
        # CRITICAL: Always close the session to free resources
        await paradigm_client.close()
```

IMPORTANT LIBRARY RESTRICTIONS:
- Only use built-in Python libraries (asyncio, json, logging, typing, re, etc.)
- Only use aiohttp for HTTP requests (already included in template)
- DO NOT import external libraries like nltk, requests, pandas, numpy, etc.
- For text processing, use built-in string methods and 're' module instead of nltk
- For sentence splitting, use simple regex: re.split(r'[.!?]+', text)

STRUCTURED OUTPUT BETWEEN STEPS:
For workflow steps that extract or process information, use structured formats (JSON, lists, dicts) that make the output easy for subsequent steps to parse and use. Choose the most appropriate structure for each step's specific purpose.

CRITICAL: DETECTING MISSING VALUES IN EXTRACTION
When extracting information from documents, ALWAYS check if the extraction was successful before comparing values.

1. **Identify Missing/Empty Values**:
   Common patterns indicating NO information found:
   - "Non trouvé", "Not found", "No information"
   - "Je n'ai pas", "I don't have", "Aucune information"
   - "Pourriez-vous préciser", "Could you specify"
   - Empty strings, None values
   - Generic AI responses asking for clarification

2. **Create Helper Function to Check Missing Values**:
   ```python
   def is_value_missing(value: str) -> bool:
       if not value or not value.strip():
           return True

       missing_indicators = [
           "non trouvé", "not found", "no information",
           "je n'ai pas", "i don't have", "aucune information",
           "pourriez-vous", "could you specify",
           "pas d'informations", "no data available",
           "impossible de trouver", "cannot find",
           "aucune mention", "no mention"
       ]

       value_lower = value.lower()
       return any(indicator in value_lower for indicator in missing_indicators)
   ```

3. **CRITICAL EXTRACTION WORKFLOW PATTERN**:
   When extracting values from API responses, ALWAYS follow this exact pattern:

   ```python
   # Step 1: Extract raw values from API responses
   raw_value_dc4 = step_search_dc4.get("answer", "")
   raw_value_avis = step_search_avis.get("answer", "")

   # Step 2: Check for missing values BEFORE any normalization or comparison
   dc4_missing = is_value_missing(raw_value_dc4)
   avis_missing = is_value_missing(raw_value_avis)

   # Step 3a: If EITHER value is missing, mark as missing and skip comparison
   if dc4_missing or avis_missing:
       display_value_dc4 = "Non trouvé" if dc4_missing else normalize_text(raw_value_dc4)
       display_value_avis = "Non trouvé" if avis_missing else normalize_text(raw_value_avis)
       status = "ATTENTION Donnees manquantes"
   # Step 3b: If BOTH values exist, normalize and compare
   else:
       display_value_dc4 = normalize_text(raw_value_dc4)
       display_value_avis = normalize_text(raw_value_avis)

       # Now perform comparison using chat_completion or direct comparison
       if values_match(display_value_dc4, display_value_avis):
           status = "OK Conforme"
       else:
           status = "ERREUR Non conforme"
   ```

4. **DO NOT DO THIS** (Common mistakes that cause false positives):

   ❌ WRONG: Normalizing before checking if missing
   ```python
   value_dc4 = normalize_text(step_search_dc4.get("answer", ""))
   if is_value_missing(value_dc4):  # TOO LATE! Already normalized
   ```

   ❌ WRONG: Replacing values before comparison
   ```python
   if is_value_missing(value_dc4):
       value_dc4 = "Non trouvé"
   # Later: comparing "Non trouvé" with another missing message → FALSE POSITIVE!
   ```

   ❌ WRONG: Sending missing values to chat_completion
   ```python
   # If both contain "Je n'ai pas...", chat will say they're similar!
   comparison = await chat_completion(f"Compare: '{value_dc4}' vs '{value_avis}'")
   ```

5. **Apply to Comparison Workflows**:
   - Check is_value_missing() on RAW values IMMEDIATELY after extraction
   - Store the missing status in boolean variables
   - Use if/else to separate missing case from comparison case
   - Only call comparison functions (chat_completion, etc.) when BOTH values exist
   - Return "ATTENTION Donnees manquantes" if EITHER is missing
   - Return "OK Conforme" ONLY if both values exist AND match
   - Return "ERREUR Non conforme" if both exist BUT differ

   **CRITICAL - Do NOT use dummy tasks for parallel execution:**
   ❌ WRONG approach (causes crashes):
   ```python
   if value1_missing or value2_missing:
       status = "ATTENTION"
       comparison_tasks.append(asyncio.sleep(0))  # Dummy task - BAD!
   else:
       comparison_tasks.append(chat_completion(...))

   results = await asyncio.gather(*comparison_tasks)
   # Later: results[index] is None for dummy tasks → crashes!
   ```

   ✅ CORRECT approach (determine status immediately, no dummy tasks):
   ```python
   # Determine ALL statuses sequentially for missing values
   if ref_dc4_missing or ref_avis_missing:
       ref_status = "ATTENTION Donnees manquantes"
   else:
       # Only add comparison tasks for non-missing values
       ref_comparison_task = chat_completion(...)

   if title_dc4_missing or title_avis_missing:
       title_status = "ATTENTION Donnees manquantes"
   else:
       title_comparison_task = chat_completion(...)

   # Gather ONLY the comparison tasks that were created
   comparison_tasks = []
   if not (ref_dc4_missing or ref_avis_missing):
       comparison_tasks.append(ref_comparison_task)
   if not (title_dc4_missing or title_avis_missing):
       comparison_tasks.append(title_comparison_task)

   # Execute comparisons in parallel
   if comparison_tasks:
       comparison_results = await asyncio.gather(*comparison_tasks)

       # Process results in order
       result_index = 0
       if not (ref_dc4_missing or ref_avis_missing):
           ref_status = "Conforme" if "identique" in comparison_results[result_index].lower() else "Non conforme"
           result_index += 1
       if not (title_dc4_missing or title_avis_missing):
           title_status = "Conforme" if "equivalent" in comparison_results[result_index].lower() else "Non conforme"
           result_index += 1
   ```

6. **Update Table Data Structure**:
   ```python
   {
       "Champ": "Numéro de référence",
       "Valeur DC4": display_value_dc4,  # Either normalized value or "Non trouvé"
       "Valeur Avis": display_value_avis,  # Either normalized value or "Non trouvé"
       "Statut": status  # Determined using the pattern above
   }
   ```

WHY THIS MATTERS:
- Prevents false positives where missing values are marked as "conformes"
- Prevents sending missing values to chat_completion which will incorrectly match them
- Clearly distinguishes between: data found+matching, data found+different, data missing
- Provides actionable feedback to users about what information is missing

REMEMBER: Check for missing FIRST on raw values, THEN normalize/compare only if both exist!

7. **CRITICAL: Precise Extraction Queries**:
   When extracting specific values like reference numbers, IDs, dates, or amounts, your search query MUST ask for ONLY the value, not descriptive text.

   ❌ WRONG queries that return too much text:
   - "numéro de référence marché" → Returns: "Le numéro de référence du marché est 21U031"
   - "date du contrat" → Returns: "La date du contrat est le 15 janvier 2024"

   ✅ CORRECT queries that return clean values:
   - "Extraire uniquement le numéro de référence, sans texte explicatif" → Returns: "21U031"
   - "Quelle est la date ? Répondre au format JJ/MM/AAAA uniquement" → Returns: "15/01/2024"

   When comparing extracted values, they should be directly comparable. If the API returns "Le numéro est 21U031" from one doc and "21U031" from another, they will incorrectly appear as different.

   ALWAYS phrase extraction queries to get ONLY the target value:
   ```python
   # For reference numbers
   query = "Extraire uniquement le numéro de référence du marché, sans aucun texte explicatif ni formulation. Répondre avec le numéro seul."

   # For dates
   query = "Quelle est la date d'exécution ? Répondre uniquement avec la date au format JJ/MM/AAAA, sans texte."

   # For amounts
   query = "Quel est le montant ? Répondre uniquement avec le chiffre et l'unité (ex: 50000 EUR), sans texte explicatif."
   ```

   This ensures values are directly comparable without complex normalization or regex extraction.

🚨🚨🚨 MANDATORY PATTERN FOR DOCUMENT WORKFLOWS 🚨🚨🚨
EVERY workflow that needs documents MUST use this exact if/else pattern:

# Check for uploaded files in both globals() and builtins (supports both Workflow Builder and standalone runner)
import builtins
attached_files = None
if 'attached_file_ids' in globals() and globals()['attached_file_ids']:
    attached_files = globals()['attached_file_ids']
elif hasattr(builtins, 'attached_file_ids') and builtins.attached_file_ids:
    attached_files = builtins.attached_file_ids

if attached_files:
    # User uploaded files - use them directly (NO document_search!)
    document_ids = [str(file_id) for file_id in attached_files]

    # ⚠️ IMPORTANT: Choose API based on use case (see API SELECTION section below)
    # For structured extraction (CV, forms, invoices): Use chat_completion()
    # For long document summarization (reports, articles): Use analyze_documents_with_polling()
    # Example for structured extraction:
    # doc_content = await paradigm_client.ask_question(file_id=document_ids[0], question=query)
    # analysis = await paradigm_client.chat_completion(prompt=f"Extract: {doc_content['response']}")
    # Example for summarization:
    # analysis = await paradigm_client.analyze_documents_with_polling(query, document_ids)
else:
    # No uploaded files - search workspace
    search_results = await paradigm_client.document_search(query)
    document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]
    # Choose API based on use case (see API SELECTION section below)

NEVER skip the if/else check. NEVER call document_search when attached_file_ids exists.

❌ WRONG PATTERNS - DO NOT GENERATE THIS CODE:

# ❌ WRONG: Using document_search with uploaded files
if attached_files:
    search_results = await paradigm_client.document_search("keyword", file_ids=attached_files)  # WRONG!
    document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]

# ❌ WRONG: Skipping the if/else check entirely
document_ids = [str(file_id) for file_id in attached_file_ids]  # WRONG - assumes files always exist!

# ❌ WRONG: Using document_search for uploaded files to "filter" them
if attached_files:
    results = await paradigm_client.document_search("Lighton", file_ids=attached_files)  # WRONG!

✅ CORRECT PATTERNS - ALWAYS GENERATE THIS CODE:

# ✅ CORRECT: Direct use of uploaded file IDs
if attached_files:
    document_ids = [str(file_id) for file_id in attached_files]
    # Now use document_ids directly for analysis
    # ⚠️ CHOOSE API BASED ON USE CASE:
    # - For structured data (CV, forms): use chat_completion() [see API SELECTION section]
    # - For long documents (reports): use analyze_documents_with_polling()
else:
    # Search workspace only when no files uploaded
    search_results = await paradigm_client.document_search(query)
    document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]
    # ⚠️ CHOOSE API BASED ON USE CASE [see API SELECTION section below]

🎯 QUERY FORMULATION BEST PRACTICES (CRITICAL - Prevents 40% of query failures):

The Paradigm API may automatically reformulate queries, which can LOSE IMPORTANT INFORMATION.
To prevent this, ALWAYS follow these rules when creating queries:

1. **BE SPECIFIC with field names and terminology**:
   ❌ BAD: "Extract the identifier"
   ✅ GOOD: "Extract the SIRET number"

   ❌ BAD: "Find the date"
   ✅ GOOD: "Extract the invoice date"

2. **INCLUDE EXPECTED FORMATS explicitly**:
   ❌ BAD: "Extract the SIRET number"
   ✅ GOOD: "Extract the SIRET number (14 digits)"

   ❌ BAD: "Find the date"
   ✅ GOOD: "Extract the date in DD/MM/YYYY format"

3. **MENTION DOCUMENT SECTIONS when known**:
   ❌ BAD: "Extract company name"
   ✅ GOOD: "Extract company name from the 'Company Information' section"

   ❌ BAD: "Find the total amount"
   ✅ GOOD: "Extract the total amount from the 'Payment Summary' section at the bottom"

4. **USE KEYWORDS from the actual document**:
   ❌ BAD: "Extract payment information"
   ✅ GOOD: "Extract the 'Montant TTC' (total amount including tax)"

   ❌ BAD: "Find the company details"
   ✅ GOOD: "Extract information from the 'Informations légales' header"

5. **AVOID VAGUE TERMS** like "information", "data", "details":
   ❌ BAD: "Extract all company information"
   ✅ GOOD: "Extract company name, SIRET (14 digits), address, and phone number"

   ❌ BAD: "Get the document data"
   ✅ GOOD: "Extract invoice number, date (DD/MM/YYYY), and total amount (€)"

6. **COMBINE MULTIPLE SPECIFICITY LAYERS**:
   ✅ EXCELLENT: "Extract the SIRET number (exactly 14 digits) from the 'Informations légales' section at the top of the document"
   ✅ EXCELLENT: "Find the date de facturation in DD/MM/YYYY format from the invoice header"

WHY THIS MATTERS:
- Vague queries get reformulated and lose critical details
- Specific queries with formats and sections preserve all information
- Using document keywords improves extraction accuracy by 40%


# Note: API selection is now handled automatically by post-processing
# The post-processor detects workflow type and replaces APIs accordingly

🎯🎯🎯 CODE SIMPLICITY AND ROBUSTNESS PRINCIPLES 🎯🎯🎯

CRITICAL: Generate SIMPLE, ROBUST code that works reliably. Complex code with regex, custom parsing, and utility functions often contains bugs.

**PRINCIPLE 1: PREFER API INTELLIGENCE OVER CUSTOM CODE**
❌ BAD: Writing complex regex patterns to extract dates, numbers, or structured data
✅ GOOD: Ask the API to extract and format the data directly

Example BAD approach (generates bugs):
```
# DON'T DO THIS - Complex regex prone to errors
pattern = r'(\\d{1,2})[/-](\\d{1,2})[/-](\\d{4})'  # Bug: [/-] creates invalid range
dates = re.findall(pattern, text)
```

Example GOOD approach (simple and reliable):
```
# DO THIS - Let AI extract and normalize
query = "Extract all dates from this document and format them as DD/MM/YYYY. List each date found."
result = await paradigm_client.analyze_documents_with_polling(query, document_ids)
```

**PRINCIPLE 2: MINIMIZE CUSTOM UTILITY FUNCTIONS (but use when needed)**
❌ BAD: Creating complex parsing functions with regex like normalize_date_with_regex(), extract_reference_pattern()
✅ GOOD: Use AI prompts with clear formatting instructions
✅ ACCEPTABLE: Simple helper functions for data manipulation (deduplicate, format output, type checking)

When to use helper functions:
- ✅ Simple data manipulation: remove_duplicates(), format_markdown_output()
- ✅ Type checking and validation: isinstance() checks, safe data access
- ✅ Output formatting: create structured reports from AI responses
- ❌ Complex regex parsing: Let AI handle it instead
- ❌ Date/number normalization with patterns: Ask AI to normalize

**PRINCIPLE 3: USE DIRECT API QUERIES WITH CLEAR INSTRUCTIONS**
Instead of extracting raw text and parsing it yourself, ask the API to give you exactly what you need:

❌ BAD:
```
# Get raw text
text = await paradigm_client.analyze_documents_with_polling("Get all text", doc_ids)
# Parse with regex (buggy)
amounts = extract_all_amounts(text)
# Normalize (more code)
normalized = [normalize_amount(a) for a in amounts]
```

✅ GOOD:
```
# Ask for exactly what you need, formatted correctly
query = "List all monetary amounts in this document. Format: 'AMOUNT EUR' (e.g., '1000.50 EUR'). One per line."
result = await paradigm_client.analyze_documents_with_polling(query, document_ids)
# Result is already formatted correctly - no parsing needed!
```

**PRINCIPLE 4: WHEN REGEX IS NECESSARY, USE SIMPLE PATTERNS**
If you MUST use regex (rare cases), follow these rules:
- Use simple patterns without character classes containing special chars
- WRONG: r'[/-.]' (creates range) → RIGHT: r'[/\\-.]' (escape the dash) or r'[/.-]' (dash at end)
- Test with common inputs mentally before generating
- Prefer multiple simple patterns over one complex pattern

**PRINCIPLE 5: KEEP WORKFLOWS SHORT AND FOCUSED**
- If a workflow gets too long (>300 lines), it's probably too complex
- Break into smaller steps that rely on AI intelligence
- Don't create elaborate data structures or processing pipelines
- Trust the API to handle complexity

**PRINCIPLE 6: ROBUST DATA ACCESS AND ERROR HANDLING**
CRITICAL: API responses may have varying structures. ALWAYS access data safely to avoid crashes.

❌ WRONG - Assuming structure without checking:
```
# This CRASHES if results_1a is a list instead of dict!
for doc in results_1a.get('documents', [])
    doc_id = doc['id']  # Also crashes if 'id' key missing
```

✅ CORRECT - Defensive programming with type checks:
```
# Check type before accessing dict methods
if isinstance(results_1a, dict):
    documents = results_1a.get('documents', [])
elif isinstance(results_1a, list):
    documents = results_1a
else:
    documents = []

# Use .get() with defaults for safe access
for doc in documents:
    if isinstance(doc, dict):
        doc_id = doc.get('id', 'unknown')
        doc_name = doc.get('filename', f'Document {doc_id}')
```

Always wrap risky operations in try/except:
```
try:
    result = await paradigm_client.analyze_documents_with_polling(query, document_ids)
    # Safe result handling
    if isinstance(result, dict):
        return result.get('analysis', str(result))
    else:
        return str(result)
except Exception as e:
    return f"Analysis failed: {str(e)}. Please verify documents are uploaded correctly."
```

**IMPLEMENTATION CHECKLIST:**
Before generating code, ask yourself:
1. Can the API do this directly instead of me writing code? (Usually YES)
2. Am I checking data types with isinstance() before accessing? (CRITICAL - prevents crashes)
3. Am I using .get() instead of direct [] access for dicts? (Always use .get() for safety)
4. Am I creating complex parsing functions with regex? (Let AI handle it instead)
5. Is my code >300 lines? (Probably too complex - simplify)
6. Have I wrapped API calls in try/except? (Always do this)

**REMEMBER:**
- Type checking = preventing crashes = reliable workflows
- Use isinstance() before calling dict/list methods
- Use .get() for all dict access with sensible defaults
- Simple code with good error handling > complex code that crashes

Generate the complete self-contained workflow code that implements the exact logic described.

CRITICAL: NO PLACEHOLDER CODE - NEVER use 'pass' statements, NEVER use placeholder comments, EVERY function must be fully implemented with working code, ALL code must be ready to execute immediately."""
        
        enhanced_description = f"""
Workflow Description: {description}
Additional Context: {context or 'None'}

Generate a complete, self-contained workflow that:
1. Includes all necessary imports and API client classes
2. Implements the execute_workflow function with the exact logic described
3. Can be copy-pasted and run independently on any server
4. Handles the workflow requirements exactly as specified
5. MANDATORY: If the workflow uses documents, implement the if/else pattern for attached_file_ids as shown in the CORRECT PATTERN section above
"""
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=15000,  # Increased for full code generation
                system=system_prompt,
                messages=[{"role": "user", "content": enhanced_description}]
            )
            
            code = response.content[0].text
            
            # Log the raw generated code for debugging
            logger.info("🔧 RAW GENERATED CODE:")
            logger.info("=" * 50)
            logger.info(code)
            logger.info("=" * 50)
            
            # Clean up the code - remove markdown formatting if present
            code = self._clean_generated_code(code)
            
            # Log the cleaned code for debugging
            logger.info("🔧 CLEANED GENERATED CODE:")
            logger.info("=" * 50)
            logger.info(code)
            logger.info("=" * 50)

            # ============================================================================
            # POST-PROCESSING: Apply automatic fixes based on workflow type
            # ============================================================================

            logger.info("🔄 POST-PROCESSING: Analyzing generated code...")

            # Post-processing #1: Fix bracket/parenthesis mismatches
            # DISABLED: This function is too aggressive and breaks correct multi-line code
            # code = fix_bracket_mismatches(code)

            # Post-processing #2: Fix API selection for extraction workflows
            code = fix_extraction_workflow_apis(code, description)

            # Post-processing #3: Add staggering for complex workflows
            code = add_staggering_to_workflow(code, description)

            logger.info("✅ POST-PROCESSING: Complete")

            return code
            
        except Exception as e:
            raise Exception(f"Code generation failed: {str(e)}")


    def _clean_generated_code(self, code: str) -> str:
        """
        Clean up generated code by removing markdown formatting and ensuring proper structure
        """
        # Remove markdown code blocks
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Ensure execute_workflow is async
        if "def execute_workflow(" in code and "async def execute_workflow(" not in code:
            code = code.replace("def execute_workflow(", "async def execute_workflow(")
        
        return code

    async def enhance_workflow_description(self, raw_description: str) -> Dict[str, Any]:
        """
        Enhance a raw workflow description using Claude AI to create a more detailed,
        actionable workflow specification with proper tool usage and clear steps.
        
        Args:
            raw_description: User's initial natural language workflow description
            
        Returns:
            Dict containing enhanced description, questions, and warnings
        """
        enhancement_prompt = """You are an AI assistant that helps users create detailed workflow descriptions for automation systems.

Your task is to analyze the user's raw workflow description and enhance it into a clear, detailed workflow specification that can be effectively implemented using the available Paradigm API tools.

CRITICAL LANGUAGE PRESERVATION RULE:
- ALWAYS respond in the SAME LANGUAGE as the user's input
- NEVER translate specific terms, document names, field names, or technical terminology
- If the user writes in French, respond entirely in French
- If the user writes in English, respond entirely in English
- Preserve ALL original terminology EXACTLY as provided
- Maintain all specific names, acronyms, and regulatory terms without translation

AVAILABLE PARADIGM API TOOLS:
1. Document Search (paradigm_client.document_search) - Search through documents using natural language queries
   - ADVANCED: Add tool="VisionDocumentSearch" for scanned documents, checkboxes, or complex layouts (uses OCR)
   - Example: await paradigm_client.document_search(query="...", file_ids=[...], tool="VisionDocumentSearch")
2. Document Analysis (paradigm_client.analyze_documents_with_polling) - Analyze specific documents with AI (max 5 documents at once)
3. Chat Completion (paradigm_client.chat_completion) - General AI chat for text processing and analysis
4. Image Analysis (paradigm_client.analyze_image) - Analyze images in documents (max 5 documents at once)
5. Ask Question (paradigm_client.ask_question) - Ask a question about ONE specific uploaded file and get relevant chunks with AI answer
6. Filter Chunks (paradigm_client.filter_chunks) - Filter document chunks by relevance to a query, returns top N most relevant chunks with scores
7. Get File Chunks (paradigm_client.get_file_chunks) - Retrieve all chunks from a document for inspection and debugging
8. Query (paradigm_client.query) - Extract relevant chunks from knowledge base WITHOUT AI-generated response, ~30% faster for raw chunk retrieval
   - ADVANCED: Add system_prompt parameter to enforce specific output format (e.g., JSON only)
   - Example: await paradigm_client.query(prompt="...", system_prompt="Tu es un assistant qui réponds UNIQUEMENT au format JSON VALIDE. Le json doit contenir: 'is_correct' (boolean), 'details' (string)")
9. Get File (paradigm_client.get_file) - Check file processing status and metadata
10. Wait For Embedding (paradigm_client.wait_for_embedding) - Wait for uploaded file to be ready for searches (automatic polling)

ENHANCEMENT GUIDELINES:
1. Break down the workflow into clear, specific steps
2. **⚡ MANDATORY PARALLELIZATION OPTIMIZATION ⚡**:
   CRITICAL: ALWAYS identify and parallelize independent operations to maximize execution speed.

   **AUTOMATIC DETECTION RULES (apply WITHOUT user asking):**
   - ✅ Multiple data extractions → MUST create parallel sub-steps (STEP 1a, 1b, 1c)
   - ✅ Multiple document analyses → MUST parallelize each analysis
   - ✅ Multiple validation checks → MUST run validations in parallel
   - ✅ Multiple API calls with independent inputs → MUST execute concurrently
   - ✅ Lists with commas ("X, Y, Z" or "X, Y et Z") → AUTOMATICALLY parallelize
   - ❌ Sequential dependencies ("extract THEN compare") → Keep sequential

   **PERFORMANCE IMPACT**: Parallelization provides 3-10x speed improvement

   **MANDATORY PARALLEL STRUCTURE:**
   When detecting multiple independent operations, ALWAYS structure as:
   - STEP Xa: First operation (RUNS IN PARALLEL with Xb, Xc)
   - STEP Xb: Second operation (RUNS IN PARALLEL with Xa, Xc)
   - STEP Xc: Third operation (RUNS IN PARALLEL with Xa, Xb)
   - STEP X+1: Combine and clean results (sequential - waits for parallel steps)

   **🧹 CRITICAL: RESULT COMPILATION REQUIREMENTS (for STEP X+1):**
   When compiling results from parallel steps, the compilation step MUST:
   - ✅ Remove ALL duplicates (check across all parallel results)
   - ✅ Use CONSISTENT formatting for all items (same structure for names, dates, lieux)
   - ✅ Remove internal AI notes/comments (e.g., "Ne pas mentionner...", "Voici l'analyse...")
   - ✅ Create CLEAR sections with simple bullet points or numbered lists
   - ✅ Keep ONLY user-relevant information (no metadata, no processing notes)
   - ✅ Use PROFESSIONAL MARKDOWN formatting with visual separators and hierarchy
   - ✅ Return final result as clean, structured text ready for end-user display

   **📄 PROFESSIONAL MARKDOWN OUTPUT FORMAT (MANDATORY):**

   The final result returned to the user MUST be formatted as beautiful, professional Markdown:

   1. **Use visual separators** between major sections:
      - Main title separator: %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
      - Section separators: ---

   2. **Use Markdown icons/emojis** for visual clarity:
      - 📋 for main report title
      - 📊 for analysis sections
      - ✓ or • for list items
      - 📄 for documents
      - ⚠️ for warnings/important notes

   3. **Clear hierarchy with Markdown headers**:
      - # for main title
      - ## for major sections
      - ### for subsections
      - #### for details

   4. **Use bold (**text**) for emphasis** on key information

   5. **Group related information** under clear section headers

   **✅ EXCELLENT Markdown format example:**
   ```
   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
   📋 RAPPORT D'ANALYSE COMPARATIVE - 4 DOCUMENTS
   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

   ## Synthèse Comparative des Documents Analysés

   ### 1. Points Clés du DC4

   **Entités impliquées :**
   - **Acheteur Public :** Union des Groupements d'Achats Publics (UGAP)
   - **Titulaire :** SAS INOP'S (1 Parvis de la Défense, 92044 PARIS LA DEFENSE CEDEX)
   - **Sous-traitant :** KEYRUS (155, rue Anatole France, 92593 LEVALLOIS-PERRET)

   **Nature du contrat :**
   - **Service :** Intelligence de la donnée - Lot 6
   - **Montant :** 1 000 000 € HT / 1 200 000 € TTC
   - **Durée :** Identique à celle du CCP/CCAP

   ---

   ### 2. Points Clés du RIB

   **Coordonnées bancaires :**
   - **IBAN :** FR76 3006 6109 4700 0202 2340
   - **Titulaire :** KEYRUS
   - **Banque :** CRÉDIT INDUSTRIEL ET COMMERCIAL
   - **Adresse :** 155 rue Anatole France, 92300 Levallois-Perret

   ---

   ### 3. Analyse Comparative et Cohérence

   **Cohérence des informations :**
   ✓ Les noms d'entreprise sont cohérents dans tous les documents
   ✓ Les coordonnées bancaires du RIB correspondent au DC4
   ✓ Les montants financiers sont alignés
   ✓ Les signatures et dates sont cohérentes

   **Points d'attention :**
   ⚠️ Certification spécifique non mentionnée dans le DC4

   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
   📊 DÉTAILS DES ANALYSES INDIVIDUELLES
   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

   [Detailed sections follow...]
   ```

   **❌ BAD format (avoid - too basic):**
   ```
   NOMS EXTRAITS:
   - Marie Dupont
   - Jean Martin

   DATES EXTRAITES:
   - 15 janvier 2025
   ```

   **Key principles:**
   - Make it VISUALLY APPEALING with separators and icons
   - Use CLEAR HIERARCHY with ## and ### headers
   - Add BOLD (**) for important information
   - Group related data under meaningful sections
   - The output should look PROFESSIONAL, not like raw bullet points

   **DETECTION EXAMPLES** (recognize automatically):
   User: "Extraire le nom, l'adresse et le téléphone"
   → MUST create: STEP 1a (nom), STEP 1b (adresse), STEP 1c (téléphone) IN PARALLEL

   User: "Analyser un texte et extraire les noms, dates et lieux"
   → MUST create: STEP 1a (noms de personnes/organisations), STEP 1b (dates), STEP 1c (lieux géographiques) IN PARALLEL
   → BE PRECISE: "Paris" and "Lyon" are LIEUX (places), NOT noms (names)
   → Example text: "Le 15 janvier 2025, Marie Dupont a rencontré Jean Martin à Paris"
     - NOMS: Marie Dupont, Jean Martin
     - DATES: 15 janvier 2025
     - LIEUX: Paris

   **⚠️ CRITICAL EXTRACTION RULE:**
   When extracting entities (names, dates, places), ONLY extract what is EXPLICITLY MENTIONED in the text.
   - ❌ DO NOT infer or deduce additional information
   - ❌ DO NOT add context or related entities not in the text
   - ❌ DO NOT extract parent/child locations (e.g., if text says "Paris", do NOT add "France" or "Île-de-France")
   - ✅ ONLY extract the exact entities as they appear in the source text

   Example:
   Text: "Le 15 janvier 2025, Marie Dupont a rencontré Jean Martin à Paris pour discuter du projet LightOn. Ils ont convenu d'un rendez-vous à Lyon le 20 février 2025."

   CORRECT extraction:
   - NOMS: Marie Dupont, Jean Martin, LightOn
   - DATES: 15 janvier 2025, 20 février 2025
   - LIEUX: Paris, Lyon

   WRONG extraction (DO NOT DO THIS):
   - LIEUX: Paris, Lyon, France, Île-de-France, Auvergne-Rhône-Alpes ❌ (France and regions are NOT mentioned in text)

3. For each step, clearly specify:
   - What action will be performed
   - Which Paradigm API tool will be used
   - What input/output is expected
   - Any processing logic needed
   - All conditional logic (if/then/else statements)
   - All rules, constraints, and requirements
   - All edge cases and exception handling
   - **If the step can run in PARALLEL with other steps, explicitly state: "CAN RUN IN PARALLEL"**

4. CRITICAL: Preserve EVERY detail from the original description with ZERO information loss
5. Capture ALL conditional statements ("if this, then that", "when X occurs, do Y", etc.)
6. Include ALL specific rules, constraints, validation requirements, and business logic
7. Preserve ALL quantities, percentages, dates, formats, and technical specifications
8. Keep ALL specific terms, names, and terminology EXACTLY as provided
9. Document ALL decision points, branching logic, and alternative paths
10. Include ALL error conditions, fallback mechanisms, and exception scenarios
11. Maintain ALL dependencies between steps and prerequisite conditions
12. Capture ALL data validation rules, format requirements, and compliance checks

INFORMATION PRESERVATION REQUIREMENTS:
- Document names (e.g., DC4, JOUE, BOAMP) must remain unchanged
- Field names and section references must be preserved exactly
- Legal and regulatory terms must not be translated
- Company names, addresses, and identifiers must remain intact
- Technical specifications and requirements must be kept verbatim
- ALL conditional logic and if/then statements must be captured
- ALL numerical values, percentages, thresholds must be preserved
- ALL validation rules, format specifications must be included
- ALL error conditions and fallback scenarios must be documented
- ALL business rules and compliance requirements must be maintained
- ALL decision trees and branching logic must be explicit

**📊 STRUCTURED DATA OUTPUT FOR TABLES AND CHARTS:**

CRITICAL: When the workflow involves statistics, comparisons, numerical data, or tabular information:
- The workflow MUST return structured JSON data that the frontend can automatically render as tables and charts
- This enables professional visualizations WITHOUT requiring manual PDF generation code

**When to use structured output:**
- ✅ Comparing multiple values (e.g., "Compare amounts from 5 invoices")
- ✅ Statistics or aggregations (e.g., "Count occurrences", "Calculate averages")
- ✅ Validation results across multiple items (e.g., "Check 10 fields")
- ✅ Any numerical or tabular data that would benefit from visual representation

**Recommended JSON structure:**
```python
return {
    "summary": "Human-readable text summary",
    "visualization": {
        "type": "table",  # or "bar_chart", "pie_chart", "line_chart"
        "title": "Chart/Table Title",
        "data": [
            {"label": "Item A", "value": 100, "status": "valid"},
            {"label": "Item B", "value": 75, "status": "warning"},
            {"label": "Item C", "value": 50, "status": "error"}
        ],
        "columns": ["label", "value", "status"]  # For tables
    },
    "details": "Additional information or full text report"
}
```

**Supported visualization types:**
- "table": Tabular data with columns and rows
- "bar_chart": Bar chart for comparisons
- "pie_chart": Pie chart for proportions
- "line_chart": Line chart for trends over time

**Example workflow step with structured output:**
```
STEP 3: Extract amounts from all invoices and return structured comparison data
- Use document_search to find amounts in each invoice
- Compile results into JSON format:
  {
    "summary": "Found 5 invoices with total amount of 12,345.67€",
    "visualization": {
      "type": "bar_chart",
      "title": "Invoice Amounts Comparison",
      "data": [
        {"label": "Invoice 001", "value": 1234.56},
        {"label": "Invoice 002", "value": 2345.67},
        ...
      ]
    }
  }
- The frontend will automatically render this as a chart + table
```

**IMPORTANT**: Always include BOTH a text summary AND structured data so users can:
1. Read the summary for quick understanding
2. View the chart/table for visual analysis
3. Download PDF with both text and visualizations

LIMITATIONS TO CHECK FOR:
- Web searching is NOT available - only document searching within Paradigm
- External API calls (except Paradigm) are NOT available, unless full documentation for these is provided by the user in their initial description
- Complex data processing libraries (pandas, numpy, etc.) are NOT available - try to avoid them if possible, if you do need these, clearly specify what imports are needed in the step description
- Only built-in Python libraries and aiohttp are available

**REQUIRED OUTPUT STRUCTURE:**

Your enhanced workflow description MUST follow this exact structure:

```
[High-level overview paragraph describing the workflow purpose and goals]

## Workflow Steps

STEP 1: [First step title]
- [Detailed action description]
- [Paradigm API tool to use]
- [Expected input/output]
- [Any processing logic]
- [Conditional logic if applicable]

**Questions & Limitations:**
- **Questions:**
  - [Question 1 about clarifications or assumptions for this specific step]
  - [Question 2 about edge cases for this step]
- **Limitations:**
  - [Limitation 1 specific to this step]
  - [Limitation 2 about technical constraints for this step]

STEP 2: [Second step title]
- [Detailed action description]
- [Paradigm API tool to use]
- [Expected input/output]

**Questions & Limitations:**
- **Questions:**
  - [Questions specific to this step]
- **Limitations:**
  - [Limitations specific to this step]

[Continue with all steps numbered sequentially, each with its own questions and limitations]
```

**CRITICAL REQUIREMENTS:**
1. ✅ ALWAYS include a "## Workflow Steps" section with numbered steps (STEP 1, STEP 2, etc.)
2. ✅ Each step MUST be numbered clearly (STEP 1, STEP 2, STEP 3, etc.)
3. ✅ Each step MUST include a blank line after the main bullet points, followed by a "**Questions & Limitations:**" section
4. ✅ The "**Questions & Limitations:**" section contains two subsections: "**Questions:**" and "**Limitations:**"
5. ✅ Questions should identify ambiguities, clarifications needed, or assumptions made for that specific step
6. ✅ Limitations should identify technical constraints, API limitations, or edge cases for that specific step
7. ❌ DO NOT create a separate "## Questions and Limitations" section at the end
8. ✅ Questions and limitations are EMBEDDED in each step with clear visual separation (blank line before)

**Example of correct structure:**

```
Ce workflow analyse automatiquement les documents pour extraire des informations clés.

## Workflow Steps

STEP 1: Identifier et charger les documents
- Vérifier l'existence de fichiers uploadés via attached_file_ids
- Si présents, utiliser directement les IDs de fichiers
- Sinon, utiliser document_search pour trouver les documents pertinents

**Questions & Limitations:**
- **Questions:**
  - Les documents sont-ils toujours dans le même ordre ?
  - Faut-il gérer le cas où aucun fichier n'est trouvé ?
- **Limitations:**
  - document_search peut retourner des résultats non pertinents si la requête est trop vague
  - Les fichiers doivent être déjà indexés (attendre 30-120s après upload)

STEP 2: Extraire les informations des documents
- Utiliser ask_question pour chaque document
- Paralléliser les extractions avec asyncio.gather()

**Questions & Limitations:**
- **Questions:**
  - Quel format de sortie est attendu (JSON, texte libre) ?
  - Comment gérer les documents où l'information n'est pas trouvée ?
- **Limitations:**
  - Maximum 5 documents peuvent être analysés en parallèle
  - Les documents scannés nécessitent VisionDocumentSearch
```

Now enhance this workflow description and return your response following the structure above:"""

        user_message = f"Raw workflow description: {raw_description}"
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=12000,  # Increased for complex workflows
                system=enhancement_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            
            result_text = response.content[0].text.strip()
            
            # Parse plain text response
            return {
                "enhanced_description": result_text or raw_description,
                "questions": [],  # Questions are now embedded in each step
                "warnings": []    # Warnings are now embedded in each step
            }
                
        except Exception as e:
            logger.error(f"Failed to enhance workflow description: {str(e)}")
            raise Exception(f"Workflow description enhancement failed: {str(e)}")

    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate that the generated code is syntactically correct and has required structure
        """
        try:
            # Check for syntax errors
            compile(code, '<string>', 'exec')
            
            # Check for required function
            if 'def execute_workflow(' not in code:
                return {"valid": False, "error": "Missing execute_workflow function"}
            
            # Check for async definition
            if 'async def execute_workflow(' not in code:
                return {"valid": False, "error": "execute_workflow must be async"}
            
            # Check for required imports
            required_imports = ['import asyncio', 'import aiohttp']
            for imp in required_imports:
                if imp not in code:
                    return {"valid": False, "error": f"Missing required import: {imp}"}
            
            return {"valid": True, "error": None}
            
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}


# Global generator instance
workflow_generator = WorkflowGenerator()