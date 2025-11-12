/*
 * Workflow Management Functions
 *
 * Provides:
 * - Workflow description enhancement
 * - Workflow creation from user description
 * - Workflow execution with query and files
 * - Response parsing and display
 */

// Global workflow state
let currentWorkflowId = null;

/**
 * Display result messages in the UI with appropriate styling.
 *
 * @param {Element} element - DOM element to display result in
 * @param {string} message - Message to display
 * @param {string} type - Result type (success, error, loading)
 */
function showResult(element, message, type) {
    element.innerHTML = `<div class="result ${type}">${message}</div>`;
}

/**
 * Flexible parser for enhancement responses - handles various AI output formats
 * @param {Object} data - Raw response data from API
 * @returns {Object} Normalized enhancement data
 */
function parseEnhancementResponse(data) {
    const result = {
        description: '',
        questions: [],
        warnings: [],
        sections: []
    };

    // Handle standard JSON format
    if (data.enhanced_description && typeof data.enhanced_description === 'string') {
        result.description = data.enhanced_description;
        result.questions = Array.isArray(data.questions) ? data.questions : [];
        result.warnings = Array.isArray(data.warnings) ? data.warnings : [];

        // Try to parse structured description into sections
        result.sections = parseStructuredDescription(data.enhanced_description);
        return result;
    }

    // Handle direct string response
    if (typeof data === 'string') {
        result.description = data;
        result.sections = parseStructuredDescription(data);
        return result;
    }

    // Handle various object formats - be flexible with property names
    const possibleDescriptionFields = [
        'enhanced_description', 'description', 'workflow_description',
        'result', 'content', 'text', 'response'
    ];

    const possibleQuestionFields = [
        'questions', 'clarifications', 'needs_clarification', 'asks', 'queries'
    ];

    const possibleWarningFields = [
        'warnings', 'limitations', 'constraints', 'issues', 'notes', 'alerts'
    ];

    // Find description field
    for (const field of possibleDescriptionFields) {
        if (data[field] && typeof data[field] === 'string') {
            result.description = data[field];
            break;
        }
    }

    // Find questions field
    for (const field of possibleQuestionFields) {
        if (data[field] && Array.isArray(data[field])) {
            result.questions = data[field];
            break;
        } else if (data[field] && typeof data[field] === 'string') {
            result.questions = [data[field]];
            break;
        }
    }

    // Find warnings field
    for (const field of possibleWarningFields) {
        if (data[field] && Array.isArray(data[field])) {
            result.warnings = data[field];
            break;
        } else if (data[field] && typeof data[field] === 'string') {
            result.warnings = [data[field]];
            break;
        }
    }

    // Parse structured content
    if (result.description) {
        result.sections = parseStructuredDescription(result.description);
    }

    // Fallback: if no description found, stringify the entire response
    if (!result.description) {
        result.description = JSON.stringify(data, null, 2);
        result.warnings.push("Response format was not recognized. Displaying raw content.");
    }

    return result;
}

/**
 * Parse structured description text into sections for better display
 * @param {string} description - The enhanced description text
 * @returns {Array} Array of parsed sections
 */
function parseStructuredDescription(description) {
    const sections = [];

    if (!description || typeof description !== 'string') {
        return sections;
    }

    // Try to detect step-based format
    const stepMatches = description.match(/STEP \d+:.*?(?=STEP \d+:|$)/gs);
    if (stepMatches && stepMatches.length > 0) {
        stepMatches.forEach((stepText, index) => {
            const section = parseStepSection(stepText, index + 1);
            if (section) sections.push(section);
        });
        return sections;
    }

    // Try to detect numbered list format
    const numberedMatches = description.match(/^\d+\..+?(?=^\d+\.|$)/gm);
    if (numberedMatches && numberedMatches.length > 0) {
        numberedMatches.forEach((stepText, index) => {
            sections.push({
                type: 'numbered_step',
                number: index + 1,
                title: stepText.substring(0, 100).trim() + (stepText.length > 100 ? '...' : ''),
                content: stepText.trim(),
                context: null,
                questions: null,
                limitations: null
            });
        });
        return sections;
    }

    // Try to detect any other structured format with headers
    const headerMatches = description.match(/(^|\n)[A-Z][A-Z\s]{2,}:.*?(?=(^|\n)[A-Z][A-Z\s]{2,}:|$)/gs);
    if (headerMatches && headerMatches.length > 0) {
        headerMatches.forEach((sectionText, index) => {
            const lines = sectionText.trim().split('\n');
            const header = lines[0].replace(':', '').trim();
            const content = lines.slice(1).join('\n').trim();

            sections.push({
                type: 'header_section',
                number: index + 1,
                title: header,
                content: content || header,
                context: null,
                questions: null,
                limitations: null
            });
        });
        return sections;
    }

    // Fallback: treat as single section
    sections.push({
        type: 'single_section',
        number: 1,
        title: 'Enhanced Workflow Description',
        content: description,
        context: null,
        questions: null,
        limitations: null
    });

    return sections;
}

/**
 * Parse a STEP section with subsections
 * @param {string} stepText - Text of a single step
 * @param {number} stepNumber - Step number
 * @returns {Object} Parsed step section
 */
function parseStepSection(stepText, stepNumber) {
    const section = {
        type: 'detailed_step',
        number: stepNumber,
        title: '',
        content: '',
        context: null,
        questions: null,
        limitations: null
    };

    // Extract main step description
    const stepMatch = stepText.match(/STEP \d+:\s*([^\n]+)/);
    if (stepMatch) {
        section.title = stepMatch[1].trim();
    }

    // Extract QUESTIONS AND LIMITATIONS section
    const questionsAndLimitationsMatch = stepText.match(/QUESTIONS AND LIMITATIONS:\s*([\s\S]*?)$/i);
    if (questionsAndLimitationsMatch) {
        const qlText = questionsAndLimitationsMatch[1].trim();
        if (qlText.toLowerCase() !== 'none' && qlText.toLowerCase() !== 'none.') {
            // Parse both questions and limitations from the combined section
            const items = qlText.split('\n').filter(q => q.trim()).map(q => q.replace(/^-\s*/, '').trim());
            section.questions = items; // Store all items as questions for now
            section.limitations = items; // Display in both sections
        } else {
            section.questions = null;
            section.limitations = null;
        }
    }

    // Set content as the title if no other content
    section.content = section.title;

    return section;
}

/**
 * Render enhancement result with flexible formatting
 * @param {Object} enhancedData - Parsed enhancement data
 * @returns {string} HTML string for display
 */
function renderEnhancementResult(enhancedData) {
    let html = '<div class="result success">';
    html += '<h3 style="margin-top: 0; color: #28a745;">✅ Workflow description enhanced successfully!</h3>';

    // Render sections if available
    if (enhancedData.sections && enhancedData.sections.length > 0) {
        html += '<div style="margin: 15px 0;">';
        html += '<h4 style="color: #333; margin-bottom: 15px;">📋 Enhanced Workflow Steps:</h4>';

        enhancedData.sections.forEach(section => {
            html += renderSection(section);
        });

        html += '</div>';
    } else {
        // Fallback to simple description display
        html += '<div style="margin: 15px 0;">';
        html += '<h4 style="color: #333; margin-bottom: 10px;">📋 Enhanced Description:</h4>';
        html += `<div style="background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid #28a745; white-space: pre-line; font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5;">${enhancedData.description}</div>`;
        html += '</div>';
    }

    // Render global questions if any
    if (enhancedData.questions && enhancedData.questions.length > 0) {
        html += '<div style="margin: 15px 0;">';
        html += '<h4 style="color: #ff9900; margin-bottom: 10px;">❓ Overall Questions:</h4>';
        html += '<ul style="margin: 0; padding-left: 20px; background: #fff3cd; padding: 10px 10px 10px 30px; border-radius: 4px; border-left: 4px solid #ffc107;">';
        enhancedData.questions.forEach(q => {
            html += `<li style="margin-bottom: 5px; color: #856404;">${q}</li>`;
        });
        html += '</ul></div>';
    }

    // Render global warnings if any
    if (enhancedData.warnings && enhancedData.warnings.length > 0) {
        html += '<div style="margin: 15px 0;">';
        html += '<h4 style="color: #dc3545; margin-bottom: 10px;">⚠️ Overall Warnings:</h4>';
        html += '<ul style="margin: 0; padding-left: 20px; background: #f8d7da; padding: 10px 10px 10px 30px; border-radius: 4px; border-left: 4px solid #dc3545;">';
        enhancedData.warnings.forEach(w => {
            html += `<li style="margin-bottom: 5px; color: #721c24;">${w}</li>`;
        });
        html += '</ul></div>';
    }

    html += '</div>';
    return html;
}

/**
 * Render a single section with appropriate formatting
 * @param {Object} section - Section data
 * @returns {string} HTML string for the section
 */
function renderSection(section) {
    let html = '<div style="border: 1px solid #e9ecef; border-radius: 6px; margin-bottom: 15px; overflow: hidden;">';

    // Section header
    html += `<div style="background: #f8f9fa; padding: 12px 15px; border-bottom: 1px solid #e9ecef;">`;
    html += `<h5 style="margin: 0; color: #495057; font-weight: 600;">Step ${section.number}: ${section.title}</h5>`;
    html += '</div>';

    // Section content
    html += '<div style="padding: 15px;">';

    if (section.content && section.content !== section.title) {
        html += `<div style="margin-bottom: 12px; color: #333; line-height: 1.5;">${section.content.replace(/\n/g, '<br>')}</div>`;
    }

    // Additional context
    if (section.context) {
        html += '<div style="margin-bottom: 12px;">';
        html += '<strong style="color: #007bff; font-size: 14px;">📚 Additional Context:</strong>';
        html += `<div style="margin-top: 5px; padding: 10px; background: #f0f7ff; border-left: 3px solid #007bff; font-size: 13px; line-height: 1.4;">${section.context.replace(/\n/g, '<br>')}</div>`;
        html += '</div>';
    }

    // Questions and Limitations (combined section)
    if (section.questions && section.questions.length > 0) {
        html += '<div style="margin-bottom: 12px;">';
        html += '<strong style="color: #dc3545; font-size: 14px;">❓ Questions and Limitations:</strong>';
        html += '<ul style="margin: 5px 0 0 0; padding-left: 20px; background: #fff3e0; padding: 8px 8px 8px 25px; border-left: 3px solid #ff9900; font-size: 13px;">';
        section.questions.forEach(q => {
            html += `<li style="margin-bottom: 4px; color: #e65100;">${q}</li>`;
        });
        html += '</ul></div>';
    }

    html += '</div></div>';
    return html;
}

/**
 * Enhance the user's workflow description using Claude AI.
 * Takes raw user input and transforms it into an optimal workflow description.
 */
async function enhanceWorkflowDescription() {
    const rawDescription = document.getElementById('rawWorkflowDescription').value.trim();
    const resultDiv = document.getElementById('enhancedDescriptionResult');
    const enhancedDiv = document.getElementById('enhancedDescription');

    if (!rawDescription) {
        showResult(resultDiv, 'Please enter a workflow description', 'error');
        addLog('❌ No raw workflow description provided', 'error');
        return;
    }

    showResult(resultDiv, 'Enhancing workflow description...', 'loading');
    addLog('🚀 Starting workflow description enhancement...', 'info');

    try {
        const { response, data } = await loggedFetch(`${API_BASE}/workflows/enhance-description`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                description: rawDescription
            })
        }, 'ENHANCE WORKFLOW DESCRIPTION');

        if (response.ok) {
            // Flexible parsing - handle various response formats
            const enhancedData = parseEnhancementResponse(data);

            // Update the Create Workflow step with enhanced description
            document.getElementById('workflowDescription').value = enhancedData.description;
            document.getElementById('workflowDescription').style.color = '#333';

            // Store enhanced description
            enhancedDiv.innerHTML = enhancedData.description;

            // Create formatted display using flexible renderer
            const formattedHtml = renderEnhancementResult(enhancedData);
            resultDiv.innerHTML = formattedHtml;

            // Add instruction message
            const instructionDiv = document.createElement('div');
            instructionDiv.style.cssText = 'background: #e3f2fd; padding: 15px; border-radius: 4px; margin-top: 15px; border-left: 4px solid #2196f3; font-size: 14px;';
            instructionDiv.innerHTML = '<strong>💡 Next Steps:</strong><br>' +
                '• If this workflow description looks good → Proceed to <strong>Step 2</strong> to create the workflow<br>' +
                '• If you need to address questions or warnings → Refine your input above and enhance again<br>' +
                '• You can also manually edit the description in Step 2 before generating code';
            resultDiv.appendChild(instructionDiv);

        } else {
            showResult(resultDiv, `❌ Error: ${data.detail || 'Failed to enhance workflow description'}`, 'error');
        }
    } catch (error) {
        showResult(resultDiv, `❌ Network Error: ${error.message}`, 'error');
    }
}

/**
 * Create a new workflow from user description.
 * Calls AI service to generate executable code from natural language.
 */
async function createWorkflow() {
    const description = document.getElementById('workflowDescription').value.trim();
    const name = document.getElementById('workflowName').value.trim();
    const resultDiv = document.getElementById('workflowResult');

    if (!description) {
        showResult(resultDiv, 'Please enter a workflow description', 'error');
        addLog('❌ No workflow description provided', 'error');
        return;
    }

    showResult(resultDiv, 'Creating workflow...', 'loading');
    addLog('🚀 Starting workflow creation...', 'info');

    try {
        const { response, data } = await loggedFetch(`${API_BASE}/workflows`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                description: description,
                name: name || null
            })
        }, 'CREATE WORKFLOW');

        if (response.ok) {
            currentWorkflowId = data.id;
            document.getElementById('testButton').disabled = false;

            const resultMessage = `✅ Workflow created successfully!\n\nID: ${data.id}\nName: ${data.name || 'Unnamed'}\nStatus: ${data.status}\n\nGenerated Code:\n${data.generated_code || 'No code generated'}`;

            showResult(resultDiv, resultMessage, 'success');
        } else {
            showResult(resultDiv, `❌ Error: ${data.detail || 'Failed to create workflow'}`, 'error');
        }
    } catch (error) {
        showResult(resultDiv, `❌ Network Error: ${error.message}`, 'error');
    }
}

/**
 * Execute a workflow with user query and optional file attachments.
 * Runs the generated workflow code and displays results with detailed logging.
 */
async function executeWorkflowWithQuery() {
    if (!currentWorkflowId) {
        alert('Please create a workflow first');
        addLog('❌ No workflow to execute', 'error');
        return;
    }

    const query = document.getElementById('testQuery').value.trim();
    const resultDiv = document.getElementById('testResult');

    if (!query) {
        showResult(resultDiv, 'Please enter a query', 'error');
        addLog('❌ No query provided', 'error');
        return;
    }

    // Check if files are attached
    const hasAttachments = queryAttachedFiles.length > 0;
    const attachmentIds = queryAttachedFiles.map(file => file.id);

    showResult(resultDiv, 'Executing workflow... (this may take up to 5 minutes for document analysis)', 'loading');
    addLog('🚀 Starting workflow execution...', 'info');
    addLog(`🎯 WORKFLOW ID: ${currentWorkflowId}`, 'response');
    addLog(`📝 USER QUERY: ${query}`, 'query');

    if (hasAttachments) {
        addLog(`📎 ATTACHED DOCUMENTS: ${attachmentIds.length} files [${attachmentIds.join(', ')}]`, 'docs');
    }

    try {
        // Prepare execution payload with attached files
        let executionPayload = {
            user_input: query
        };

        if (hasAttachments) {
            executionPayload.attached_file_ids = attachmentIds;
        }

        const { response, data } = await loggedFetch(`${API_BASE}/workflows/${currentWorkflowId}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(executionPayload)
        }, 'EXECUTE WORKFLOW WITH QUERY');

        if (response.ok) {
            const executionTime = data.execution_time ? `${data.execution_time.toFixed(2)}s` : 'N/A';

            addLog(`⚡ WORKFLOW EXECUTION COMPLETED in ${executionTime}`, 'workflow-step');

            // Enhanced workflow result parsing
            if (data.result) {
                addLog('📄 ANALYZING WORKFLOW EXECUTION DETAILS...', 'workflow-step');

                const result = data.result;

                // Look for specific workflow steps and log them with details
                if (result.includes('WORKFLOW STEP: Paradigm Search')) {
                    addLog('🔍 STEP DETECTED: Paradigm Document Search executed', 'workflow-step');
                }

                if (result.includes('WORKFLOW STEP: Document Analysis')) {
                    addLog('📊 STEP DETECTED: Document Analysis executed', 'workflow-step');
                }

                if (result.includes('WORKFLOW STEP: Ask Question About File')) {
                    addLog('❓ STEP DETECTED: File Question executed', 'workflow-step');
                }

                if (result.includes('WORKFLOW STEP: Chat Completion')) {
                    addLog('💬 STEP DETECTED: AI Chat Completion executed', 'workflow-step');
                }

                // Extract and log search queries
                const searchQueries = result.match(/SEARCH QUERY: ([^\n]+)/g);
                if (searchQueries) {
                    searchQueries.forEach((query, i) => {
                        const queryText = query.replace('SEARCH QUERY: ', '');
                        addLog(`🔍 SEARCH QUERY ${i+1}: ${queryText}`, 'query');
                    });
                }

                // Extract and log analysis queries
                const analysisQueries = result.match(/ANALYSIS QUERY: ([^\n]+)/g);
                if (analysisQueries) {
                    analysisQueries.forEach((query, i) => {
                        const queryText = query.replace('ANALYSIS QUERY: ', '');
                        addLog(`📊 ANALYSIS QUERY ${i+1}: ${queryText}`, 'query');
                    });
                }

                // Extract and log file questions
                const fileQuestions = result.match(/QUESTION: ([^\n]+)/g);
                if (fileQuestions) {
                    fileQuestions.forEach((question, i) => {
                        const questionText = question.replace('QUESTION: ', '');
                        addLog(`❓ FILE QUESTION ${i+1}: ${questionText}`, 'query');
                    });
                }

                // Extract and log document IDs
                const docIdMatches = result.match(/DOCUMENT IDS: ([^\n]+)/g);
                if (docIdMatches) {
                    docIdMatches.forEach((match, i) => {
                        const docIds = match.replace('DOCUMENT IDS: ', '');
                        addLog(`📋 DOCUMENT IDS USED ${i+1}: ${docIds}`, 'docs');
                    });
                }

                // Extract and log file IDs
                const fileIdMatches = result.match(/FILE ID: (\d+)/g);
                if (fileIdMatches) {
                    fileIdMatches.forEach((match, i) => {
                        const fileId = match.replace('FILE ID: ', '');
                        addLog(`📁 FILE ID PROCESSED ${i+1}: ${fileId}`, 'docs');
                    });
                }

                // Extract and log API endpoints
                const endpointMatches = result.match(/ENDPOINT: ([^\n]+)/g);
                if (endpointMatches) {
                    endpointMatches.forEach((match, i) => {
                        const endpoint = match.replace('ENDPOINT: ', '');
                        addLog(`📡 API ENDPOINT ${i+1}: ${endpoint}`, 'endpoint');
                    });
                }

                // Extract and log response content
                const responseMatches = result.match(/(SEARCH RESULT|ANALYSIS RESULT|FILE QUESTION RESULT): ([^\n]+)/g);
                if (responseMatches) {
                    responseMatches.forEach((match, i) => {
                        const [type, content] = match.split(': ');
                        addLog(`💬 ${type} ${i+1}: ${content.substring(0, 150)}...`, 'response');
                    });
                }

                // Look for error patterns
                const errorMatches = result.match(/❌ ([^\n]+)/g);
                if (errorMatches) {
                    errorMatches.forEach((match, i) => {
                        const error = match.replace('❌ ', '');
                        addLog(`❌ ERROR ${i+1}: ${error}`, 'error');
                    });
                }

                // Look for attached file processing
                if (hasAttachments) {
                    addLog(`📎 PROCESSED ${attachmentIds.length} ATTACHED FILE(S): [${attachmentIds.join(', ')}]`, 'docs');
                }
            }

            if (data.status === 'completed') {
                addLog('✅ WORKFLOW EXECUTION COMPLETED SUCCESSFULLY', 'response');

                let resultMessage = `✅ Workflow executed successfully!\n\nExecution ID: ${data.execution_id}\nStatus: ${data.status}\nExecution Time: ${executionTime}`;

                if (hasAttachments) {
                    resultMessage += `\nProcessed ${attachmentIds.length} attached document(s)`;
                }

                resultMessage += `\n\n=== RESULT ===\n${data.result}`;

                showResult(resultDiv, resultMessage, 'success');

                // Add tip about Paradigm tool
                const tipDiv = document.createElement('div');
                tipDiv.style.cssText = 'background: #e3f2fd; padding: 10px; border-radius: 4px; margin-top: 10px; border-left: 4px solid #2196f3; font-size: 12px;';
                tipDiv.innerHTML = '<strong>💡 Tip:</strong> The demo workflow is available in Paradigm under the tool "Workflow demo". To run your newly generated workflow, go to Admin → Third Party Tools → Workflow demo tool and change the workflow ID in the URL address to the format shown above (e.g., "afe2e40e-3514-4445-b1c9-80ce24571837").';
                resultDiv.appendChild(tipDiv);

                // Automatically delete uploaded documents from Paradigm after testing
                if (hasAttachments) {
                    await cleanupUploadedDocuments(attachmentIds);
                }

                // Clear attachments after successful execution
                queryAttachedFiles = [];
                document.getElementById('queryFilesList').innerHTML = '';
                document.getElementById('queryUploadStatus').innerHTML = '';

            } else {
                addLog(`⚠️ WORKFLOW STATUS: ${data.status}`, 'error');
                showResult(resultDiv,
                    `⚠️ Workflow execution status: ${data.status}\n\nExecution ID: ${data.execution_id}\nExecution Time: ${executionTime}\nError: ${data.error || 'Unknown error'}`,
                    'error'
                );

                // Clean up documents even if workflow failed
                if (hasAttachments) {
                    await cleanupUploadedDocuments(attachmentIds);
                    queryAttachedFiles = [];
                    document.getElementById('queryFilesList').innerHTML = '';
                    document.getElementById('queryUploadStatus').innerHTML = '';
                }
            }
        } else {
            showResult(resultDiv, `❌ Error: ${data.detail || 'Failed to execute workflow'}`, 'error');

            // Clean up documents even if API call failed
            if (hasAttachments) {
                await cleanupUploadedDocuments(attachmentIds);
                queryAttachedFiles = [];
                document.getElementById('queryFilesList').innerHTML = '';
                document.getElementById('queryUploadStatus').innerHTML = '';
            }
        }
    } catch (error) {
        showResult(resultDiv, `❌ Network Error: ${error.message}`, 'error');

        // Clean up documents even if network error occurred
        if (hasAttachments) {
            await cleanupUploadedDocuments(attachmentIds);
            queryAttachedFiles = [];
            document.getElementById('queryFilesList').innerHTML = '';
            document.getElementById('queryUploadStatus').innerHTML = '';
        }
    }
}
