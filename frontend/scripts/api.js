/*
 * API Integration Functions
 *
 * Provides:
 * - loggedFetch: Enhanced fetch wrapper with comprehensive logging
 * - Error handling and response processing
 * - Cross-domain request handling
 */

// Global configuration
//const API_BASE = 'http://localhost:8000/api'  // Local backend API base URL with /api prefix
const API_BASE = '/api'  // Same-domain API base URL for Vercel deployment

/**
 * Enhanced fetch wrapper with comprehensive logging.
 * Logs all API calls, responses, and errors for debugging.
 *
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, headers, body)
 * @param {string} description - Human-readable description of the call
 * @returns {object} Response object with data and status
 */
async function loggedFetch(url, options = {}, description = '') {
    const logId = addLog(`🌐 API CALL: ${description || url}`, 'api');

    try {
        // Log request details
        if (options.body) {
            try {
                const bodyData = JSON.parse(options.body);
                if (bodyData.description) {
                    addLog(`📝 WORKFLOW DESC: ${bodyData.description.substring(0, 100)}...`, 'query');
                }
                if (bodyData.user_input) {
                    addLog(`🔍 USER QUERY: ${bodyData.user_input}`, 'query');
                }
            } catch (e) {
                // Not JSON, skip parsing
            }
        }

        const response = await fetch(url, options);
        const data = await response.json();

        // Log response details
        if (response.ok) {
            updateLog(logId, `✅ ${description || 'API CALL'} - SUCCESS (${response.status})`, 'response');

            // Log specific response details
            if (url.includes('/workflows') && !url.includes('/execute')) {
                addLog(`🔧 WORKFLOW ID: ${data.id}`, 'response');
                if (data.generated_code) {
                    addLog(`💻 CODE GENERATED: ${data.generated_code.length} characters`, 'response');
                }
            }

            if (url.includes('/execute')) {
                addLog(`⚡ EXECUTION ID: ${data.execution_id}`, 'response');
                addLog(`📊 STATUS: ${data.status}`, 'response');
                if (data.execution_time) {
                    addLog(`⏱️ EXECUTION TIME: ${data.execution_time.toFixed(2)}s`, 'response');
                }
            }
        } else {
            updateLog(logId, `❌ ${description || 'API CALL'} - ERROR (${response.status})`, 'error');
            addLog(`🚨 ERROR DETAILS: ${data.detail || 'Unknown error'}`, 'error');
        }

        return { response, data };

    } catch (error) {
        updateLog(logId, `❌ ${description || 'API CALL'} - NETWORK ERROR`, 'error');
        addLog(`🚨 NETWORK ERROR: ${error.message}`, 'error');
        throw error;
    }
}
