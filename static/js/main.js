document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const reindexBtn = document.getElementById('reindexBtn');
    const resetBtn = document.getElementById('resetBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const refreshPreviewBtn = document.getElementById('refreshPreviewBtn');
    const formatSelect = document.getElementById('formatSelect');
    const previewContainer = document.getElementById('previewContainer');
    const scriptCounter = document.getElementById('scriptCounter');
    const requirementBadge = document.getElementById('requirementBadge');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingMessage = document.getElementById('loadingMessage');
    const chatSpinner = document.getElementById('chatSpinner');
    
    // Modal elements
    const alertModal = new bootstrap.Modal(document.getElementById('alertModal'));
    const alertModalBody = document.getElementById('alertModalBody');
    
    // Connection to websocket for real-time updates
    const socket = io();
    
    // State
    let sessionId = null;
    let scriptGenerated = false;
    let currentDownloadUrl = null;
    
    // Initialize by connecting to the backend
    initializeApp();
    
    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
    
    reindexBtn.addEventListener('click', reindexDocuments);
    resetBtn.addEventListener('click', resetConversation);
    downloadBtn.addEventListener('click', downloadScript);
    refreshPreviewBtn.addEventListener('click', refreshPreview);
    
    // Socket event listeners
    socket.on('connect', function() {
        console.log('Connected to WebSocket');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from WebSocket');
    });
    
    // Functions
    
    /**
     * Initialize the application by starting a conversation
     */
    function initializeApp() {
        showLoading('Initialisiere Anwendung...');
        
        fetch('/api/start-conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessionId = data.session_id;
                addMessage(data.message, 'assistant');
                userInput.disabled = false;
                sendBtn.disabled = false;
                fetchStats();
            } else {
                showAlert('Fehler beim Starten der Konversation: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Starten der Konversation: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    }
    
    /**
     * Send a message to the backend
     */
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Disable input while processing
        userInput.disabled = true;
        sendBtn.disabled = true;
        chatSpinner.classList.remove('d-none');
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input field
        userInput.value = '';
        
        // Send to backend
        fetch('/api/send-message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add assistant's response to chat
                addMessage(data.message, 'assistant');
                
                // Check if script was generated
                if (data.script_generated && !scriptGenerated) {
                    scriptGenerated = true;
                    resetBtn.disabled = false;
                    downloadBtn.disabled = false;
                    refreshPreviewBtn.disabled = false;
                    refreshPreview();
                    fetchStats();
                }
            } else {
                showAlert('Fehler bei der Verarbeitung der Nachricht: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Senden der Nachricht: ' + error.message);
        })
        .finally(() => {
            // Re-enable input
            userInput.disabled = false;
            sendBtn.disabled = false;
            chatSpinner.classList.add('d-none');
            userInput.focus();
        });
    }
    
    /**
     * Add a message to the chat container
     */
    function addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;
        
        // Format content - convert markdown-style headers and code blocks
        let formattedContent = content;
        
        // Format headers (# Header)
        formattedContent = formattedContent.replace(/^(#{1,3})\s+(.+)$/gm, function(match, hashes, text) {
            const level = hashes.length;
            return `<h${level}>${text}</h${level}>`;
        });
        
        // Format code blocks
        formattedContent = formattedContent.replace(/```([a-z]*)\n([\s\S]*?)```/g, function(match, language, code) {
            return `<pre><code class="language-${language}">${code}</code></pre>`;
        });
        
        // Add line breaks
        formattedContent = formattedContent.replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = formattedContent;
        
        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = now.toLocaleTimeString();
        messageDiv.appendChild(timeDiv);
        
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    /**
     * Reindex the documents
     */
    function reindexDocuments() {
        if (!confirm('Sind Sie sicher, dass Sie alle Dokumente neu indexieren möchten? Dieser Vorgang kann einige Zeit dauern.')) {
            return;
        }
        
        showLoading('Indexiere Dokumente...');
        reindexBtn.disabled = true;
        
        fetch('/api/reindex-documents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Erfolg: ' + data.message);
                // Reset the conversation after reindexing
                resetConversation();
            } else {
                showAlert('Fehler beim Neuindexieren der Dokumente: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Neuindexieren der Dokumente: ' + error.message);
        })
        .finally(() => {
            hideLoading();
            reindexBtn.disabled = false;
        });
    }
    
    /**
     * Reset the conversation
     */
    function resetConversation() {
        showLoading('Starte neue Konversation...');
        
        fetch('/api/reset-conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear chat container
                chatContainer.innerHTML = '';
                
                // Add first message
                addMessage(data.message, 'assistant');
                
                // Reset state
                scriptGenerated = false;
                resetBtn.disabled = true;
                downloadBtn.disabled = true;
                refreshPreviewBtn.disabled = true;
                
                // Clear preview
                previewContainer.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-file-earmark-text display-1"></i>
                        <p class="mt-3">Hier wird die Vorschau des generierten Skripts angezeigt, sobald es erstellt wurde.</p>
                    </div>
                `;
                
                // Enable input
                userInput.disabled = false;
                sendBtn.disabled = false;
            } else {
                showAlert('Fehler beim Zurücksetzen der Konversation: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Zurücksetzen der Konversation: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    }
    
    /**
     * Refresh the script preview
     */
    function refreshPreview() {
        if (!scriptGenerated) return;
        
        const format = formatSelect.value;
        
        fetch('/api/preview-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                format: format
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.content_type === 'html') {
                    // Display HTML content
                    previewContainer.innerHTML = `<div class="preview-html">${data.content}</div>`;
                } else {
                    // Display text content with formatting
                    let formattedContent = data.content;
                    
                    // Format headers (# Header)
                    formattedContent = formattedContent.replace(/^(#{1,3})\s+(.+)$/gm, function(match, hashes, text) {
                        const level = hashes.length;
                        return `<h${level}>${text}</h${level}>`;
                    });
                    
                    // Format code blocks
                    formattedContent = formattedContent.replace(/```([a-z]*)\n([\s\S]*?)```/g, function(match, language, code) {
                        return `<pre><code class="language-${language}">${code}</code></pre>`;
                    });
                    
                    // Add line breaks
                    formattedContent = formattedContent.replace(/\n/g, '<br>');
                    
                    previewContainer.innerHTML = `<div class="preview-text">${formattedContent}</div>`;
                }
            } else {
                showAlert('Fehler beim Laden der Vorschau: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Laden der Vorschau: ' + error.message);
        });
    }
    
    /**
     * Download the generated script
     */
    function downloadScript() {
        if (!scriptGenerated) return;
        
        const format = formatSelect.value;
        
        showLoading('Bereite Download vor...');
        
        fetch('/api/save-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                format: format
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Option 1: Open the result page in a new tab
                window.open(`/result/${sessionId}?format=${format}`, '_blank');
                
                // Option 2: Create and click a download link directly
                // const downloadLink = document.createElement('a');
                // downloadLink.href = data.download_url;
                // downloadLink.download = data.filename;
                // document.body.appendChild(downloadLink);
                // downloadLink.click();
                // document.body.removeChild(downloadLink);
            } else {
                showAlert('Fehler beim Speichern des Skripts: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Fehler beim Speichern des Skripts: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    }
    
    /**
     * Fetch statistics from the backend
     */
    function fetchStats() {
        fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                scriptCounter.textContent = data.generated_scripts_count;
                
                // Show requirement badge if 5 or more scripts generated
                if (data.generated_scripts_count >= 5) {
                    requirementBadge.classList.remove('d-none');
                    requirementBadge.classList.remove('bg-secondary');
                    requirementBadge.classList.add('bg-success');
                }
            }
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
        });
    }
    
    /**
     * Show the loading overlay
     */
    function showLoading(message) {
        loadingMessage.textContent = message || 'Verarbeite...';
        loadingOverlay.classList.remove('d-none');
    }
    
    /**
     * Hide the loading overlay
     */
    function hideLoading() {
        loadingOverlay.classList.add('d-none');
    }
    
    /**
     * Show an alert message
     */
    function showAlert(message) {
        alertModalBody.textContent = message;
        alertModal.show();
    }
    
    // Update preview when format changes
    formatSelect.addEventListener('change', function() {
        if (scriptGenerated) {
            refreshPreview();
        }
    });
});