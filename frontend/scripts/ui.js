/*
 * User Interface Functions
 *
 * Provides:
 * - Page initialization
 * - Example text handling for textareas
 * - Dynamic UI updates based on state
 */

/**
 * Initialize the page with example workflows and default state.
 */
window.onload = function() {
    const examples = [
        "Search for documents about the user's question, then analyze those documents to provide a detailed summary.",
        "For each sentence in the user input, search for relevant documents, then format results as Question and Answer pairs.",
        "Search for documents, extract key information using chat completion, then analyze specific documents for deeper insights."
    ];

    // Set up example text behavior for raw workflow description
    const rawWorkflowTextarea = document.getElementById('rawWorkflowDescription');
    const rawExampleText = "I want to search for documents about my question and then analyze them to provide a summary.";

    // Set initial example text for raw description
    rawWorkflowTextarea.value = rawExampleText;
    rawWorkflowTextarea.style.color = '#999';

    // Handle focus - clear example text when user starts typing
    rawWorkflowTextarea.addEventListener('focus', function() {
        if (this.value === rawExampleText) {
            this.value = '';
            this.style.color = '#333';
        }
    });

    // Handle blur - restore example text if field is empty
    rawWorkflowTextarea.addEventListener('blur', function() {
        if (this.value.trim() === '') {
            this.value = rawExampleText;
            this.style.color = '#999';
        }
    });

    // Handle input - change color when user types
    rawWorkflowTextarea.addEventListener('input', function() {
        if (this.value !== rawExampleText) {
            this.style.color = '#333';
        }
    });

    // Set up example text behavior for enhanced workflow description
    const workflowTextarea = document.getElementById('workflowDescription');
    const exampleText = "Enhanced workflow description will appear here...";

    // Set initial example text
    workflowTextarea.value = exampleText;
    workflowTextarea.style.color = '#999';

    // Handle focus - clear example text when user starts typing
    workflowTextarea.addEventListener('focus', function() {
        if (this.value === exampleText) {
            this.value = '';
            this.style.color = '#333';
        }
    });

    // Handle blur - restore example text if field is empty
    workflowTextarea.addEventListener('blur', function() {
        if (this.value.trim() === '') {
            this.value = exampleText;
            this.style.color = '#999';
        }
    });

    // Handle input - change color when user types
    workflowTextarea.addEventListener('input', function() {
        if (this.value !== exampleText) {
            this.style.color = '#333';
        }
    });

    document.getElementById('testButton').textContent = 'Test Workflow';
};
