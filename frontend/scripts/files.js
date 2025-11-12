/*
 * File Management Functions
 *
 * Provides:
 * - Drag-and-drop file uploads
 * - File attachment to queries
 * - File deletion and management
 * - Document cleanup after workflow execution
 */

// Global state for attached files
let queryAttachedFiles = [];

/**
 * Handle drag-and-drop file uploads for query attachments.
 * Prevents default drag behavior and processes dropped files.
 */
function handleQueryDrop(event) {
    event.preventDefault();
    event.stopPropagation();

    const uploadArea = document.getElementById('queryUploadArea');
    uploadArea.classList.remove('dragover');

    const files = Array.from(event.dataTransfer.files);
    uploadQueryFiles(files);
}

/**
 * Handle drag-over events for file upload areas.
 * Provides visual feedback during drag operations.
 */
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();

    const uploadArea = event.target.closest('.file-upload-area');
    if (uploadArea) {
        uploadArea.classList.add('dragover');
    }
}

/**
 * Handle drag-leave events for file upload areas.
 * Removes visual feedback when drag leaves the area.
 */
function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();

    const uploadArea = event.target.closest('.file-upload-area');
    if (uploadArea) {
        uploadArea.classList.remove('dragover');
    }
}

/**
 * Handle file selection from file input element.
 * Processes files selected via browse button.
 */
function handleQueryFileSelect(event) {
    const files = Array.from(event.target.files);
    uploadQueryFiles(files);
}

/**
 * Upload files to the backend and attach them to queries.
 * Handles multiple files, updates UI, and manages error states.
 *
 * @param {FileList} files - Files to upload
 */
async function uploadQueryFiles(files) {
    const statusDiv = document.getElementById('queryUploadStatus');
    const filesList = document.getElementById('queryFilesList');

    for (const file of files) {
        try {
            statusDiv.innerHTML = `<div class="result loading">Uploading ${file.name}...</div>`;
            addLog(`📤 Uploading query attachment: ${file.name} (${file.size} bytes)`, 'info');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('collection_type', 'private');

            const { response, data } = await loggedFetch(`${API_BASE}/files/upload`, {
                method: 'POST',
                body: formData
            }, `UPLOAD QUERY FILE: ${file.name}`);

            if (response.ok) {
                // Add to query attached files list
                queryAttachedFiles.push(data);

                // Update UI
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <div class="file-info">
                        <strong>${data.filename}</strong> (ID: ${data.id})
                        <br><small>${data.bytes} bytes • Status: ${data.status}</small>
                    </div>
                    <div class="file-actions">
                        <button onclick="removeQueryFile(${data.id})" class="remove-file" title="Remove attachment">🗑️</button>
                    </div>
                `;
                filesList.appendChild(listItem);

                statusDiv.innerHTML = `<div class="result success">✅ ${file.name} attached to query!</div>`;
                addLog(`✅ Query file uploaded successfully: ID ${data.id}`, 'response');

            } else {
                statusDiv.innerHTML = `<div class="result error">❌ Failed to upload ${file.name}</div>`;
                addLog(`❌ Query upload failed: ${data.detail || 'Unknown error'}`, 'error');
            }

        } catch (error) {
            statusDiv.innerHTML = `<div class="result error">❌ Network error uploading ${file.name}</div>`;
            addLog(`❌ Query upload network error: ${error.message}`, 'error');
        }
    }

    // Clear file input
    document.getElementById('queryFileInput').value = '';
}

/**
 * Remove a file attachment from the current query.
 * Deletes the file from backend and updates local state.
 *
 * @param {number} fileId - ID of the file to remove
 */
async function removeQueryFile(fileId) {
    if (!confirm('Are you sure you want to remove this attachment?')) return;

    try {
        addLog(`🗑️ Removing query attachment ID: ${fileId}`, 'info');

        const { response, data } = await loggedFetch(`${API_BASE}/files/${fileId}`, {
            method: 'DELETE'
        }, `DELETE QUERY FILE: ${fileId}`);

        if (response.ok) {
            // Remove from query attached files array
            queryAttachedFiles = queryAttachedFiles.filter(file => file.id !== fileId);

            // Remove from UI
            const filesList = document.getElementById('queryFilesList');
            const items = filesList.querySelectorAll('li');
            items.forEach(item => {
                if (item.innerHTML.includes(`ID: ${fileId}`)) {
                    item.remove();
                }
            });

            addLog(`✅ Query attachment removed: ID ${fileId}`, 'response');

        } else {
            addLog(`❌ Remove attachment error: ${data.detail}`, 'error');
        }

    } catch (error) {
        addLog(`❌ Remove attachment network error: ${error.message}`, 'error');
    }
}

/**
 * Automatically clean up uploaded documents from Paradigm after workflow testing.
 * This ensures documents uploaded for testing don't accumulate in the user's workspace.
 *
 * @param {number[]} documentIds - Array of document IDs to delete
 */
async function cleanupUploadedDocuments(documentIds) {
    if (!documentIds || documentIds.length === 0) {
        return; // No documents to clean up
    }

    addLog(`🧹 Starting automatic cleanup of ${documentIds.length} test document(s)...`, 'info');

    let cleanupSuccessCount = 0;
    let cleanupFailCount = 0;

    for (const documentId of documentIds) {
        try {
            const { response } = await loggedFetch(`${API_BASE}/files/${documentId}`, {
                method: 'DELETE'
            }, `CLEANUP TEST DOCUMENT: ${documentId}`);

            if (response.ok || response.status === 404) {
                // 404 means already deleted, which is fine
                cleanupSuccessCount++;
                addLog(`🗑️ Test document ${documentId} deleted successfully`, 'response');
            } else {
                cleanupFailCount++;
                addLog(`⚠️ Failed to delete test document ${documentId} (status: ${response.status})`, 'error');
            }
        } catch (error) {
            cleanupFailCount++;
            addLog(`⚠️ Error deleting test document ${documentId}: ${error.message}`, 'error');
        }
    }

    if (cleanupSuccessCount > 0) {
        addLog(`✅ Cleanup completed: ${cleanupSuccessCount} document(s) deleted from Paradigm`, 'response');
    }

    if (cleanupFailCount > 0) {
        addLog(`⚠️ Cleanup issues: ${cleanupFailCount} document(s) could not be deleted`, 'error');
    }
}
