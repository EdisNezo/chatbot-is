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
    const vectorDbStatus = document.getElementById('vectorDbStatus');
    const refreshVectorDbBtn = document.getElementById('refreshVectorDbBtn');   
    const llmStatus = document.getElementById('llmStatus');
    const refreshLlmBtn = document.getElementById('refreshLlmBtn');
    
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
    fetchVectorDbStats();
    fetchLlmStatus();

    
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
    refreshVectorDbBtn.addEventListener('click', fetchVectorDbStats);
    refreshLlmBtn.addEventListener('click', fetchLlmStatus);
    
    // Socket event listeners
    socket.on('connect', function() {
        console.log('Connected to WebSocket');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from WebSocket');
    });
    
    // Functions

    function fetchLlmStatus() {
        llmStatus.innerHTML = `
          <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <span>Prüfe Status...</span>
          </div>
        `;
        
        fetch('/api/llm-status')
          .then(response => response.json())
          .then(data => {
            let statusClass, statusText, statusDetails;
            
            if (data.status === 'available') {
              statusClass = 'bg-success';
              statusText = 'Verfügbar';
              statusDetails = `<small class="text-muted d-block">Modell: ${data.model}</small>
                               <small class="text-muted d-block">Antwortzeit: ${data.response_time.toFixed(2)}s</small>`;
            } else if (data.status === 'degraded') {
              statusClass = 'bg-warning';
              statusText = 'Eingeschränkt';
              statusDetails = `<small class="text-muted d-block">Modell: ${data.model}</small>
                               <small class="text-muted d-block">Antwort: "${data.response}"</small>`;
            } else {
              statusClass = 'bg-danger';
              statusText = 'Nicht verfügbar';
              statusDetails = data.error ? 
                `<small class="text-danger d-block">Fehler: ${data.error}</small>` : 
                `<small class="text-muted d-block">LLM antwortet nicht</small>`;
            }
            
            llmStatus.innerHTML = `
              <div class="mb-2">
                <span class="badge ${statusClass} me-2">${statusText}</span>
              </div>
              ${statusDetails}
              ${data.status !== 'available' ? 
                `<div class="alert alert-warning mt-2 mb-0 py-1 px-2">
                  <small>Prüfen Sie, ob der Ollama-Service läuft und das Modell "${data.model || 'llama3.1'}" verfügbar ist.</small>
                </div>` : ''}
            `;
          })
          .catch(error => {
            console.error('Error:', error);
            llmStatus.innerHTML = `
              <div class="alert alert-danger mb-0">
                <small>Fehler beim Abrufen des Status: ${error.message}</small>
              </div>
            `;
          });
      }

    function fetchVectorDbStats() {
        vectorDbStatus.innerHTML = `
          <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <span>Checking status...</span>
          </div>
        `;
        
        fetch('/api/vectordb-stats')
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              const stats = data.stats;
              let statusHtml = `
                <div class="mb-2">
                  <span class="badge ${stats.document_count > 0 ? 'bg-success' : 'bg-danger'} me-2">
                    ${stats.document_count > 0 ? 'Active' : 'Empty'}
                  </span>
                  <strong>${stats.document_count}</strong> documents indexed
                </div>
                <small class="text-muted d-block">Path: ${stats.database_path}</small>
              `;
              
              if (stats.document_count === 0) {
                statusHtml += `
                  <div class="alert alert-warning mt-2 mb-0 py-1 px-2">
                    <small>Vector database is empty. Try reindexing documents.</small>
                  </div>
                `;
              }
              
              vectorDbStatus.innerHTML = statusHtml;
            } else {
              vectorDbStatus.innerHTML = `
                <div class="alert alert-danger mb-0">
                  Error: ${data.error}
                </div>
              `;
            }
          })
          .catch(error => {
            console.error('Error:', error);
            vectorDbStatus.innerHTML = `
              <div class="alert alert-danger mb-0">
                Error fetching statistics: ${error.message}
              </div>
            `;
          });
      }
    
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