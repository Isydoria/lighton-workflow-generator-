/*
 * Logging and Monitoring Functions
 *
 * Provides:
 * - Real-time API call logging
 * - Color-coded log entries by type
 * - Detailed workflow execution tracking
 * - Log management (add, update, clear)
 */

// Global log counter
let logCounter = 0;

/**
 * Add a new log entry to the monitoring console.
 * Provides real-time feedback on API calls and workflow execution.
 *
 * @param {string} message - Log message to display
 * @param {string} type - Log type for color coding
 * @returns {number} Log entry ID for potential updates
 */
function addLog(message, type = 'info') {
    const logsContainer = document.getElementById('logsContainer');
    const timestamp = new Date().toLocaleTimeString();
    const logId = ++logCounter;

    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.id = `log-${logId}`;

    let className = 'log-response';
    switch(type) {
        case 'api': className = 'log-api-call'; break;
        case 'query': className = 'log-query'; break;
        case 'docs': className = 'log-doc-ids'; break;
        case 'error': className = 'log-error'; break;
        case 'response': className = 'log-response'; break;
        case 'workflow-step': className = 'log-workflow-step'; break;
        case 'endpoint': className = 'log-endpoint'; break;
        case 'payload': className = 'log-payload'; break;
        case 'chunk': className = 'log-chunk'; break;
        case 'detailed': className = 'log-detailed'; break;
    }

    logEntry.innerHTML = `
        <span class="log-timestamp">[${timestamp}]</span>
        <span class="${className}">${message}</span>
    `;

    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
    return logId;
}

/**
 * Update an existing log entry with new information.
 * Used to update status of ongoing operations.
 *
 * @param {number} logId - ID of log entry to update
 * @param {string} message - New message content
 * @param {string} type - Log type for color coding
 */
function updateLog(logId, message, type = 'response') {
    const logEntry = document.getElementById(`log-${logId}`);
    if (logEntry) {
        const timestamp = new Date().toLocaleTimeString();
        let className = 'log-response';
        if (type === 'error') className = 'log-error';

        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="${className}">${message}</span>
        `;
    }
}

/**
 * Clear all log entries and reset the monitoring console.
 */
function clearLogs() {
    const logsContainer = document.getElementById('logsContainer');
    logsContainer.innerHTML = `
        <div class="log-entry">
            <span class="log-timestamp">[Ready]</span>
            <span class="log-response">Logs cleared. Waiting for API activity...</span>
        </div>
    `;
    logCounter = 0;
}
