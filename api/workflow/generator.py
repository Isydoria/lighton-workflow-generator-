import asyncio
import logging
import re
from typing import Optional, Dict, Any
from .models import Workflow
from anthropic import Anthropic
from ..config import settings

logger = logging.getLogger(__name__)


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

REQUIRED STRUCTURE:
```python
import asyncio
import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any

# Configuration - replace with your actual values
LIGHTON_API_KEY = "your_api_key_here"
LIGHTON_BASE_URL = "https://api.lighton.ai"

logger = logging.getLogger(__name__)

class ParadigmClient:
    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def document_search(self, query: str, **kwargs) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/v2/chat/document-search"
        payload = {"query": query, **kwargs}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API error {response.status}: {await response.text()}")
    
    async def analyze_documents_with_polling(self, query: str, document_ids: List[int], **kwargs) -> str:
        # Start analysis
        endpoint = f"{self.base_url}/api/v2/chat/document-analysis"
        payload = {"query": query, "document_ids": document_ids, **kwargs}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    chat_response_id = result.get("chat_response_id")
                else:
                    raise Exception(f"Analysis API error {response.status}: {await response.text()}")
        
        # Poll for results
        max_wait = 300  # 5 minutes
        poll_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            endpoint = f"{self.base_url}/api/v2/chat/document-analysis/{chat_response_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get("status", "")
                        if status.lower() in ["completed", "complete", "finished", "success"]:
                            analysis_result = result.get("result") or result.get("detailed_analysis") or "Analysis completed"
                            return analysis_result
                        elif status.lower() in ["failed", "error"]:
                            raise Exception(f"Analysis failed: {status}")
                    elif response.status == 404:
                        # Analysis not ready yet, continue polling
                        pass
                    else:
                        raise Exception(f"Polling API error {response.status}: {await response.text()}")
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
        
        raise Exception("Analysis timed out")
    
    async def chat_completion(self, prompt: str, model: str = "alfred-4.2") -> str:
        endpoint = f"{self.base_url}/api/v2/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"Paradigm chat completion API error {response.status}: {await response.text()}")
    
    async def analyze_image(self, query: str, document_ids: List[str], model: str = None, private: bool = False) -> str:
        endpoint = f"{self.base_url}/api/v2/chat/image-analysis"
        payload = {
            "query": query,
            "document_ids": document_ids
        }
        if model:
            payload["model"] = model
        if private is not None:
            payload["private"] = private
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("answer", "No analysis result provided")
                else:
                    raise Exception(f"Image analysis API error {response.status}: {await response.text()}")

# Initialize clients
paradigm_client = ParadigmClient(LIGHTON_API_KEY, LIGHTON_BASE_URL)

async def execute_workflow(user_input: str) -> str:
    # Your workflow implementation here
    pass
```

IMPORTANT LIBRARY RESTRICTIONS:
- Only use built-in Python libraries (asyncio, json, logging, typing, re, etc.)
- Only use aiohttp for HTTP requests (already included in template)
- DO NOT import external libraries like nltk, requests, pandas, numpy, etc.
- For text processing, use built-in string methods and 're' module instead of nltk
- For sentence splitting, use simple regex: re.split(r'[.!?]+', text)

STRUCTURED OUTPUT BETWEEN STEPS:
For workflow steps that extract or process information, use structured formats (JSON, lists, dicts) that make the output easy for subsequent steps to parse and use. Choose the most appropriate structure for each step's specific purpose.

🚨🚨🚨 MANDATORY PATTERN FOR DOCUMENT WORKFLOWS 🚨🚨🚨
EVERY workflow that needs documents MUST use this exact if/else pattern:

if 'attached_file_ids' in globals() and attached_file_ids:
    # User uploaded files - use them directly (NO document_search!)
    document_ids = [str(file_id) for file_id in attached_file_ids]
    analysis = await paradigm_client.analyze_documents_with_polling(query, document_ids)
else:
    # No uploaded files - search workspace
    search_results = await paradigm_client.document_search(query)
    document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]
    analysis = await paradigm_client.analyze_documents_with_polling(query, document_ids)

NEVER skip the if/else check. NEVER call document_search when attached_file_ids exists.

AVAILABLE API METHODS:
1. await paradigm_client.document_search(query: str, workspace_ids=None, file_ids=None, company_scope=True, private_scope=True, tool="DocumentSearch", private=False)
   ⚠️ NEVER call this if attached_file_ids exists! Use the IDs directly instead.
2. await paradigm_client.analyze_documents_with_polling(query: str, document_ids: List[str], model=None)
   *** CRITICAL: document_ids can contain MAXIMUM 5 documents. If more than 5, use batching! ***
   *** IMPORTANT: For document type identification, analyze documents ONE BY ONE to get clear ID-to-type mapping ***
   *** NOTE: The API uses your authentication token to access both uploaded files and workspace documents automatically ***
3. await paradigm_client.chat_completion(prompt: str, model: str = "Alfred 4.2")
4. await paradigm_client.analyze_image(query: str, document_ids: List[str], model=None) - Analyze images in documents with AI-powered visual analysis
   *** CRITICAL: document_ids can contain MAXIMUM 5 documents. If more than 5, use batching! ***
   *** NOTE: The API uses your authentication token to access both uploaded files and workspace documents automatically ***

🚀 PARALLELIZATION: WHEN AND HOW TO USE asyncio.gather()

WHEN TO PARALLELIZE:
- ✅ Multiple INDEPENDENT tasks (tasks that don't depend on each other's results)
- ✅ Multiple document searches on different topics
- ✅ Multiple document analyses on different documents
- ✅ Multiple validation checks that can run simultaneously
- ❌ DON'T parallelize tasks where one depends on the output of another

CORRECT PARALLEL EXECUTION (using asyncio.gather()):
# Example: Checking 3 different fields in parallel
name_check, address_check, phone_check = await asyncio.gather(
    paradigm_client.document_search("Extract company name", file_ids=document_ids),
    paradigm_client.document_search("Extract company address", file_ids=document_ids),
    paradigm_client.document_search("Extract company phone", file_ids=document_ids)
)

# Example: Analyzing multiple documents in parallel (respecting 5-doc limit per call)
doc_analyses = await asyncio.gather(
    paradigm_client.analyze_documents_with_polling("Summarize document", [document_ids[0]]),
    paradigm_client.analyze_documents_with_polling("Extract key dates", [document_ids[1]]),
    paradigm_client.analyze_documents_with_polling("Find signatures", [document_ids[2]])
)

# Example: Multiple comparison checks in parallel
checks = await asyncio.gather(
    paradigm_client.chat_completion(f"Compare name: Doc1={name1} vs Doc2={name2}. Are they identical?"),
    paradigm_client.chat_completion(f"Compare address: Doc1={addr1} vs Doc2={addr2}. Are they identical?"),
    paradigm_client.chat_completion(f"Compare phone: Doc1={phone1} vs Doc2={phone2}. Are they identical?")
)

PERFORMANCE BENEFITS:
- Sequential: 3 tasks × 5 seconds each = 15 seconds total
- Parallel: max(5, 5, 5) seconds = 5 seconds total (3x faster!)

INCORRECT PARALLELIZATION (DON'T DO THIS):
# ❌ Task 2 depends on Task 1's result - MUST be sequential
result1 = await task1()
result2 = await task2(result1)  # Needs result1, can't parallelize

# ❌ Using asyncio.gather() when tasks are dependent
result1, result2 = await asyncio.gather(
    task1(),
    task2(result1)  # ERROR: result1 doesn't exist yet!
)

HYBRID APPROACH (parallel groups with sequential dependencies):
# Step 1: Parallel extraction from 3 documents
doc1_info, doc2_info, doc3_info = await asyncio.gather(
    paradigm_client.document_search("Extract info", file_ids=[doc1_id]),
    paradigm_client.document_search("Extract info", file_ids=[doc2_id]),
    paradigm_client.document_search("Extract info", file_ids=[doc3_id])
)

# Step 2: Sequential comparison using extracted data
comparison = await paradigm_client.chat_completion(
    f"Compare these documents: {doc1_info}, {doc2_info}, {doc3_info}"
)

🎯 INTELLIGENT PARALLELIZATION DETECTION:

Before generating code, ALWAYS analyze the workflow description to identify independent sub-tasks that can run in parallel.

DETECTION RULES:
1. **Multiple fields/attributes extraction** → PARALLELIZE each field
   Examples: "extract name, address, phone" → 3 parallel tasks

2. **Multiple documents with same operation** → PARALLELIZE per document
   Examples: "analyze 3 documents", "compare docs A, B, C" → parallel analysis

3. **Multiple independent checks/validations** → PARALLELIZE each check
   Examples: "verify name matches, check address format, validate phone" → 3 parallel validations

4. **Sequential dependencies** → DO NOT PARALLELIZE
   Examples: "extract data THEN compare THEN summarize" → must be sequential

LANGUAGE-AGNOSTIC DETECTION (works in French, English, etc.):

EXAMPLE 1 - French: "Extraire le nom, l'adresse et le téléphone du document"
→ ANALYSIS: User wants 3 fields (nom, adresse, téléphone)
→ DETECTION: 3 independent extraction tasks
→ CODE: Use asyncio.gather() with 3 document_search or analyze_documents_with_polling calls

EXAMPLE 2 - French: "Extraire le nom et l'adresse de 5 documents différents"
→ ANALYSIS: Same operation (extract name+address) on 5 documents
→ DETECTION: 5 independent document analyses
→ CODE: Use asyncio.gather() to process 5 documents in parallel

EXAMPLE 3 - English: "Compare company name from Doc A with Doc B"
→ ANALYSIS: Extract from A → Extract from B → Compare (sequential dependency)
→ DETECTION: Partial parallelization possible (extract A and B in parallel, then compare)
→ CODE: asyncio.gather(extract_A, extract_B) then compare_results

EXAMPLE 4 - French: "Vérifier que le nom correspond, l'adresse est valide et le téléphone est au bon format"
→ ANALYSIS: 3 independent validation checks
→ DETECTION: 3 parallel validation tasks
→ CODE: Use asyncio.gather() with 3 chat_completion calls for validation

KEYWORDS INDICATING MULTIPLE TASKS (detect in ANY language):
- Lists with commas: "X, Y, Z" or "X, Y et Z" or "X and Y"
- Multiple nouns: "nom adresse téléphone", "name address phone"
- Numbers: "3 documents", "5 checks", "plusieurs fichiers"
- Conjunctions: "et/and", "puis/then", "avec/with"

IMPLEMENTATION PATTERN:
# When you detect multiple independent tasks, ALWAYS structure code like this:
task1 = api_call_1()
task2 = api_call_2()
task3 = api_call_3()

result1, result2, result3 = await asyncio.gather(task1, task2, task3)

# NOT like this (sequential - slower):
result1 = await api_call_1()
result2 = await api_call_2()
result3 = await api_call_3()

CONTEXT PRESERVATION IN API PROMPTS:
When creating prompts for API calls, include relevant context from the original workflow description: examples, formatting requirements, specific field names, and business rules mentioned by the user.

WORKFLOW ACCESS TO ATTACHED FILES:
The global variable 'attached_file_ids: List[int]' is available when users upload files.
Your workflow MUST check for this variable and handle both cases (uploaded files OR workspace search).

CORRECT DOCUMENT TYPE IDENTIFICATION (analyze individually for clear mapping):
def extract_document_type_from_response(analysis_response, expected_types):
    \"\"\"
    Extract document type from AI analysis response by finding best match with expected types.
    Args:
        analysis_response: The AI's response text
        expected_types: List of expected document type names/keywords
    Returns:
        Best matching document type or "UNKNOWN" if no match found
    \"\"\"
    response_lower = analysis_response.lower()
    
    # Try exact matches first (case insensitive)
    for doc_type in expected_types:
        if doc_type.lower() in response_lower:
            return doc_type
    
    # Try partial matches for compound names
    for doc_type in expected_types:
        type_words = doc_type.lower().split()
        if len(type_words) > 1 and all(word in response_lower for word in type_words):
            return doc_type
    
    # Try keyword-based matching for common patterns
    type_keywords = {
        "invoice": ["facture", "invoice", "bill"],
        "contract": ["contrat", "contract", "agreement"],
        "report": ["rapport", "report", "summary"],
        "statement": ["relevé", "statement", "declaration"]
    }
    
    for doc_type in expected_types:
        type_lower = doc_type.lower()
        for category, keywords in type_keywords.items():
            if category in type_lower:
                if any(keyword in response_lower for keyword in keywords):
                    return doc_type
    
    return "UNKNOWN"

# Usage example for document identification:
expected_document_types = ["DC4", "BOAMP", "JOUE", "RIB", "Acte d'engagement"]  # Define based on workflow needs
doc_type_mapping = {}
for doc_id in document_ids:
    # Use specific prompt that asks for precise identification
    identification_prompt = f"Identifiez précisément le type de ce document. Répondez uniquement par le type exact parmi ces options : {', '.join(expected_document_types)}"
    
    type_analysis = await paradigm_client.analyze_documents_with_polling(
        identification_prompt, 
        [doc_id]  # Single document for clear mapping
    )
    doc_type_mapping[doc_id] = extract_document_type_from_response(type_analysis, expected_document_types)

INCORRECT DOCUMENT TYPE IDENTIFICATION (analyzing multiple docs together):
# DON'T DO THIS - loses document ID to type mapping
all_docs_analysis = await paradigm_client.analyze_documents_with_polling(
    "Identify document types", document_ids  # Multiple docs = unclear mapping
)

CRITICAL: DOCUMENT ANALYSIS 5-DOCUMENT LIMIT:
# Document analysis can only handle 5 documents at a time
# If you have more than 5 documents, you MUST split them into batches

# ALWAYS check document count before analysis:
if len(document_ids) > 5:
    # Process in batches of 5
    results = []
    for i in range(0, len(document_ids), 5):
        batch = document_ids[i:i+5]
        result = await paradigm_client.analyze_documents_with_polling(query, batch)
        results.append(result)
    final_analysis = "\\n\\n".join(results)
else:
    # Process all documents at once (5 or fewer)
    final_analysis = await paradigm_client.analyze_documents_with_polling(query, document_ids)

❌ WRONG PATTERN - THIS WILL FAIL:
# DON'T call document_search with attached files - it returns 0 documents!
search_results = await paradigm_client.document_search(query)
documents = search_results.get("documents", [])  # Returns [] for uploaded files
document_ids = [str(doc["id"]) for doc in documents]
analysis = await paradigm_client.analyze_documents_with_polling(query, document_ids)

✅ CORRECT PATTERN - ALWAYS USE THIS:
# Check for uploaded files first, then fallback to workspace search
if 'attached_file_ids' in globals() and attached_file_ids:
    # User uploaded files - use them directly (NO document_search!)
    document_ids = [str(file_id) for file_id in attached_file_ids]
    analysis = await paradigm_client.analyze_documents_with_polling(
        "Your analysis query here",
        document_ids
    )
else:
    # No uploaded files - search the workspace
    search_results = await paradigm_client.document_search("Your search query here")
    document_ids = [str(doc["id"]) for doc in search_results.get("documents", [])]
    analysis = await paradigm_client.analyze_documents_with_polling(
        "Your analysis query here",
        document_ids
    )

WHY THIS MATTERS:
- Uploaded files (attached_file_ids) are in your private collection
- document_search() searches the workspace, NOT private uploaded files
- Calling document_search with uploaded file IDs returns 0 documents
- You must use attached_file_ids directly when they exist
- The API automatically uses your auth token to access documents

CORRECT TEXT PROCESSING (using built-in libraries):
import re
def split_sentences(text):
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

CORRECT SEARCH RESULT USAGE:
search_result = await paradigm_client.document_search(**search_kwargs)
# Use the AI-generated answer from search results
answer = search_result.get("answer", "No answer provided")
# Don't try to extract raw document content - use the answer field

INCORRECT (DON'T DO THIS):
file_ids=attached_file_ids if 'attached_file_ids' in globals() else None  # API doesn't accept None
document_ids = [doc["id"] for doc in search_results.get("documents", [])]  # Should convert to strings
import nltk  # External library not available
answer = search_result["documents"][0].get("content", "")  # Raw content extraction

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
2. Document Analysis (paradigm_client.analyze_documents_with_polling) - Analyze specific documents with AI (max 5 documents at once)
3. Chat Completion (paradigm_client.chat_completion) - General AI chat for text processing and analysis
4. Image Analysis (paradigm_client.analyze_image) - Analyze images in documents (max 5 documents at once)

ENHANCEMENT GUIDELINES:
1. Break down the workflow into clear, specific steps
2. **PARALLELIZATION DETECTION**: When the user asks to extract/analyze/check MULTIPLE INDEPENDENT items:
   - ✅ DETECT: "extract name, address, phone" → 3 independent extractions
   - ✅ DETECT: "analyze documents A, B, C" → 3 independent analyses
   - ✅ DETECT: "verify field1, field2, field3" → 3 independent validations
   - ✅ CREATE SUB-STEPS: Break into parallel sub-steps (STEP 1a, 1b, 1c) with explicit note "These can run in PARALLEL"
   - ❌ DON'T SPLIT: "extract data THEN compare" → sequential dependency, keep as single step

   EXAMPLE of parallel detection:
   User: "Extraire le nom, l'adresse et le téléphone du document"
   → STEP 1a: Extract name (CAN RUN IN PARALLEL with 1b and 1c)
   → STEP 1b: Extract address (CAN RUN IN PARALLEL with 1a and 1c)
   → STEP 1c: Extract phone (CAN RUN IN PARALLEL with 1a and 1b)
   → STEP 2: Format and return results (sequential - waits for Step 1)

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

LIMITATIONS TO CHECK FOR:
- Web searching is NOT available - only document searching within Paradigm
- External API calls (except Paradigm) are NOT available, unless full documentation for these is provided by the user in their initial description
- Complex data processing libraries (pandas, numpy, etc.) are NOT available - try to avoid them if possible, if you do need these, clearly specify what imports are needed in the step description
- Only built-in Python libraries and aiohttp are available

OUTPUT FORMAT:
CRITICAL: Provide your response as PLAIN TEXT ONLY. 
DO NOT use JSON format. 
DO NOT wrap your response in ```json or ``` blocks.
DO NOT use curly braces { } or quotes around your response.
Return the enhanced workflow steps directly in plain text using the step format structure below.

STEP FORMAT STRUCTURE:
For each workflow step, use this exact format:

STEP X: [Highly detailed description of the workflow step with ALL information needed for an LLM to convert the step with all specific requirements (if/then statements, subtle rules, validation logic, API parameters, error conditions, etc.) into very clear code. There should be ABSOLUTELY NO information loss in this step description.]

QUESTIONS AND LIMITATIONS: 
- Write "None" if the step is crystal clear and entirely feasible with Paradigm tools alone. Think carefully about potential edge cases and missing information such as "if, then" statements that would clarify these. 
- Otherwise, clearly list:
  * Questions to clarify any ambiguities in the user's description
  * Questions to get extra information needed (external API documentation, business rules, data formats, etc.)
  * Indications that the step requires tools not available (web search, external APIs beyond Paradigm, etc.)

The goal is that STEP X contains everything needed for code generation, and QUESTIONS AND LIMITATIONS only points out what's missing or impossible.

EXAMPLES:

Simple Input: "Search for documents about my question and analyze them"
Plain Text Response:
STEP 1: Search for relevant documents using paradigm_client.document_search with the user's query as the search parameter, setting company_scope=True and private_scope=True to search across all available document collections, and store the returned search results which contain document metadata including IDs, titles, and relevance scores.

QUESTIONS AND LIMITATIONS: None

---

STEP 2: Extract document IDs from the search results by accessing the 'documents' array in the search response, converting each document's 'id' field to string format, and handling the API limitation that maximum 5 documents can be analyzed at once by implementing batching logic if more than 5 documents are found.

QUESTIONS AND LIMITATIONS: None

---

STEP 3: Analyze the found documents using paradigm_client.analyze_documents_with_polling with the user's original question as the analysis query, implementing the polling mechanism with up to 5-minute timeout, processing documents in batches of maximum 5 documents per API call, and collecting all analysis results which contain AI-generated insights based on document content.

QUESTIONS AND LIMITATIONS: None

---

STEP 4: Compile all analysis results from processed documents into a comprehensive summary by combining insights from all batches, formatting the response in clear, readable structure with proper line breaks and organization, including source document references for transparency, and returning the final formatted summary to the user.

QUESTIONS AND LIMITATIONS: None

Now enhance this workflow description and return ONLY the plain text response:"""

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