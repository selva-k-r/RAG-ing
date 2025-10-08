/**
 * Real-time progress tracking with flying words animation
 * Shows progress without slowing down the main processing
 */

class ProgressTracker {
    constructor() {
        this.eventSource = null;
        this.sessionId = null;
        this.startTime = null;
        this.flyingWordsInterval = null;
        this.chatSkeletonShown = false;
    }

    async startSearch(query, audience = 'technical', sources = ['confluence', 'jira', 'internal', 'salesforce']) {
        try {
            // Reset state
            this.chatSkeletonShown = false;
            
            // Step 1: Initiate search with progress tracking
            const response = await fetch('/api/search-with-progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, audience, sources })
            });

            const data = await response.json();
            this.sessionId = data.session_id;
            this.startTime = Date.now();

            // Step 2: Show progress UI
            this.showProgressUI();

            // Step 3: Connect to progress stream
            this.connectToProgressStream();

        } catch (error) {
            console.error('Failed to start search:', error);
            this.showError('Failed to start search');
        }
    }

    connectToProgressStream() {
        if (!this.sessionId) return;

        this.eventSource = new EventSource(`/api/progress/${this.sessionId}`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleProgressUpdate(data);
            } catch (error) {
                console.error('Error parsing progress data:', error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('Progress stream error:', error);
            this.eventSource.close();
        };
    }

    handleProgressUpdate(data) {
        switch (data.type) {
            case 'connected':
                console.log('Progress stream connected');
                break;
                
            case 'progress':
                this.updateProgressUI(data);
                
                // When LLM processing starts (step 4), show chat skeleton
                if (data.step === 4 && !this.chatSkeletonShown) {
                    this.showChatSkeleton();
                    this.chatSkeletonShown = true;
                }
                break;
                
            case 'complete':
                this.handleCompletion(data);
                break;
                
            case 'timeout':
                this.showError('Search timed out');
                break;
        }
    }

    showProgressUI() {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <div class="progress-container">
                <div class="progress-header">
                    <h3>🔍 Processing your query...</h3>
                    <div class="estimated-time">
                        Estimated time: <span id="timeRemaining">15-20 seconds</span>
                    </div>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                        <div class="progress-text" id="progressText">0%</div>
                    </div>
                </div>
                
                <div class="current-step">
                    <div class="step-name" id="stepName">Initializing...</div>
                    <div class="step-details" id="stepDetails">Setting up search parameters</div>
                </div>
                
                <div class="flying-words-container" id="flyingWords">
                    <!-- Flying words will be injected here -->
                </div>
                
                <div class="progress-stats">
                    <div class="stat">
                        <span class="stat-label">Elapsed:</span>
                        <span class="stat-value" id="elapsedTime">0s</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Step:</span>
                        <span class="stat-value" id="currentStepNum">1/6</span>
                    </div>
                </div>
            </div>
        `;

        // Start flying words animation
        this.startFlyingWordsAnimation();
    }

    updateProgressUI(data) {
        // Update progress bar
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        if (progressFill && progressText) {
            progressFill.style.width = `${data.progress}%`;
            progressText.textContent = `${Math.round(data.progress)}%`;
        }

        // Update step information
        const stepName = document.getElementById('stepName');
        const stepDetails = document.getElementById('stepDetails');
        const currentStepNum = document.getElementById('currentStepNum');
        
        if (stepName) stepName.textContent = data.step_name;
        if (stepDetails) stepDetails.textContent = data.details;
        if (currentStepNum) currentStepNum.textContent = `${data.step + 1}/6`;

        // Update elapsed time
        const elapsedTime = document.getElementById('elapsedTime');
        if (elapsedTime) {
            elapsedTime.textContent = `${Math.round(data.elapsed)}s`;
        }

        // Update estimated remaining time
        const timeRemaining = document.getElementById('timeRemaining');
        if (timeRemaining && data.estimated_remaining > 0) {
            timeRemaining.textContent = `${Math.round(data.estimated_remaining)}s remaining`;
        }

        // Update flying words based on current step
        this.updateFlyingWords(data.flying_words || []);
    }

    startFlyingWordsAnimation() {
        const container = document.getElementById('flyingWords');
        if (!container) return;

        // Create initial flying words
        this.flyingWordsInterval = setInterval(() => {
            this.createFlyingWord(container);
        }, 300); // New word every 300ms
    }

    updateFlyingWords(words) {
        this.currentWords = words;
    }

    createFlyingWord(container) {
        if (!this.currentWords || this.currentWords.length === 0) {
            this.currentWords = ["processing", "analyzing", "searching"];
        }

        const word = this.currentWords[Math.floor(Math.random() * this.currentWords.length)];
        const wordElement = document.createElement('div');
        wordElement.className = 'flying-word';
        wordElement.textContent = word;

        // Random starting position and animation
        const startX = Math.random() * (container.offsetWidth - 100);
        const startY = container.offsetHeight;
        const endX = startX + (Math.random() - 0.5) * 200;
        const endY = -50;

        wordElement.style.left = `${startX}px`;
        wordElement.style.top = `${startY}px`;
        wordElement.style.opacity = '0.8';

        container.appendChild(wordElement);

        // Animate the word
        wordElement.animate([
            { transform: `translate(0, 0)`, opacity: 0.8 },
            { transform: `translate(${endX - startX}px, ${endY - startY}px)`, opacity: 0 }
        ], {
            duration: 2000 + Math.random() * 1000, // 2-3 seconds
            easing: 'ease-out'
        }).onfinish = () => {
            wordElement.remove();
        };
    }

    async handleCompletion(data) {
        // Stop animations
        if (this.flyingWordsInterval) {
            clearInterval(this.flyingWordsInterval);
        }

        // Close event source
        if (this.eventSource) {
            this.eventSource.close();
        }

        // Show chat skeleton if not already shown
        if (!this.chatSkeletonShown) {
            this.showChatSkeleton();
            this.chatSkeletonShown = true;
        }

        // Get final result
        try {
            const response = await fetch(`/api/result/${this.sessionId}`);
            const result = await response.json();
            
            if (result.error) {
                this.showError(result.error);
                return;
            }

            // Display results in chat template with streaming text
            this.displayResultsInChatTemplate(result);
            
        } catch (error) {
            console.error('Error fetching final result:', error);
            this.showError('Failed to retrieve search results');
        }
    }

    displayFinalResults(result) {
        let resultsContainer = document.getElementById('results');
        if (!resultsContainer) {
            // Create results container if it doesn't exist
            resultsContainer = document.createElement('div');
            resultsContainer.id = 'results';
            resultsContainer.style.cssText = `
                margin-top: 20px;
                padding: 0;
            `;
            
            // Insert in the content area
            const contentWrapper = document.querySelector('.content-wrapper');
            if (contentWrapper) {
                contentWrapper.insertBefore(resultsContainer, contentWrapper.firstChild);
            } else {
                document.body.appendChild(resultsContainer);
            }
        }

        const processingTime = result.metadata?.processing_time || 0;
        const confidenceScore = result.metadata?.confidence_score || 0.8;
        const sourceCount = result.metadata?.source_count || 0;

        resultsContainer.innerHTML = `
            <div class="search-complete-animation">
                <div class="completion-badge">
                    ✅ Search Complete in ${Math.round(processingTime)}s
                </div>
            </div>
            
            <div class="card fade-in">
                <div class="results-header">
                    <div class="confidence-badge badge ${this.getConfidenceClass(confidenceScore)}">
                        🎯 ${Math.round(confidenceScore * 100)}% Confidence
                    </div>
                    <div class="source-count">
                        📚 ${sourceCount} sources analyzed
                    </div>
                </div>
                
                <div class="response-content">
                    <div class="response-text">
                        ${this.formatResponse(result.response)}
                    </div>
                </div>
                
                <div class="sources-section">
                    <h4>📖 Sources</h4>
                    ${this.formatSources(result.sources)}
                </div>
                
                <div class="action-buttons">
                    <button class="btn btn-secondary" onclick="this.copyToClipboard('${result.response}')">
                        📋 Copy Response
                    </button>
                    <button class="btn btn-primary" onclick="this.startNewSearch()">
                        🔍 New Search
                    </button>
                </div>
            </div>
        `;

        // Add fade-in animation
        setTimeout(() => {
            const card = resultsContainer.querySelector('.card');
            if (card) card.classList.add('visible');
        }, 100);
    }

    formatResponse(response) {
        // Convert markdown-like formatting to HTML
        return response
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }

    formatSources(sources) {
        if (!sources || sources.length === 0) {
            return '<p class="no-sources">No sources available</p>';
        }

        return sources.map((source, index) => `
            <div class="source-item">
                <div class="source-header">
                    <span class="source-number">${index + 1}</span>
                    <span class="source-title">${source.metadata?.title || 'Document'}</span>
                    <span class="relevance-score">${Math.round((source.relevance_score || 0.8) * 100)}% relevant</span>
                </div>
                <div class="source-content">
                    ${source.content}
                </div>
            </div>
        `).join('');
    }

    getConfidenceClass(score) {
        if (score >= 0.8) return 'high';
        if (score >= 0.6) return 'medium';
        return 'low';
    }

    showError(message) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <div class="error-container">
                <div class="error-icon">❌</div>
                <div class="error-message">${message}</div>
                <button class="btn btn-primary" onclick="location.reload()">
                    🔄 Try Again
                </button>
            </div>
        `;

        // Stop animations
        if (this.flyingWordsInterval) {
            clearInterval(this.flyingWordsInterval);
        }
        if (this.eventSource) {
            this.eventSource.close();
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            // Show temporary success message
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        });
    }

    showChatSkeleton() {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <div class="chat-skeleton">
                <div class="chat-message user-message">
                    <div class="message-avatar user-avatar">👤</div>
                    <div class="message-content">
                        <div class="message-text">${document.getElementById('searchInput').value}</div>
                    </div>
                </div>
                
                <div class="chat-message ai-message">
                    <div class="message-avatar ai-avatar">🤖</div>
                    <div class="message-content">
                        <div class="typing-indicator">
                            <div class="typing-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                            <div class="typing-text">AI is composing response...</div>
                        </div>
                        <div class="message-text" id="streamingText" style="display: none;"></div>
                    </div>
                </div>
            </div>
        `;
    }

    displayResultsInChatTemplate(result) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        const processingTime = result.metadata?.processing_time || 0;
        const confidenceScore = result.metadata?.confidence_score || 0.8;
        const sourceCount = result.metadata?.source_count || 0;

        // Hide typing indicator and show streaming text
        const typingIndicator = document.querySelector('.typing-indicator');
        const streamingText = document.getElementById('streamingText');
        
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (streamingText) streamingText.style.display = 'block';

        // Stream the text character by character
        this.streamText(result.response, streamingText, () => {
            // After text streaming is complete, add sources and actions
            this.addSourcesAndActions(result, processingTime, confidenceScore, sourceCount);
        });
    }

    streamText(text, container, onComplete) {
        if (!container) return;
        
        let index = 0;
        const speed = 3; // Much faster - 3ms per character
        
        const typeWriter = () => {
            if (index < text.length) {
                // Add multiple characters at once for faster rendering
                const charsToAdd = Math.min(5, text.length - index); // Add 5 chars at a time
                container.innerHTML = this.formatResponse(text.substring(0, index + charsToAdd));
                index += charsToAdd;
                setTimeout(typeWriter, speed);
            } else {
                // Streaming complete
                if (onComplete) onComplete();
            }
        };
        
        typeWriter();
    }

    addSourcesAndActions(result, processingTime, confidenceScore, sourceCount) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        // Add sources section after the streaming text
        const sourcesHTML = `
            <div class="chat-message ai-message">
                <div class="message-avatar ai-avatar">📚</div>
                <div class="message-content">
                    <div class="sources-header">
                        <div class="confidence-badge ${this.getConfidenceClass(confidenceScore)}">
                            🎯 ${Math.round(confidenceScore * 100)}% Confidence
                        </div>
                        <div class="processing-stats">
                            ⏱️ ${Math.round(processingTime)}s • 📖 ${sourceCount} sources
                        </div>
                    </div>
                    <div class="sources-list">
                        ${this.formatSourcesForChat(result.sources)}
                    </div>
                    <div class="chat-actions">
                        <button class="btn btn-secondary" onclick="progressTracker.copyToClipboard('${result.response.replace(/'/g, "\\'")}')">
                            📋 Copy
                        </button>
                        <button class="btn btn-primary" onclick="progressTracker.startNewSearch()">
                            🔍 New Search
                        </button>
                    </div>
                </div>
            </div>
        `;

        resultsContainer.insertAdjacentHTML('beforeend', sourcesHTML);
    }

    formatSourcesForChat(sources) {
        if (!sources || sources.length === 0) {
            return '<p class="no-sources">No sources available</p>';
        }

        return sources.slice(0, 3).map((source, index) => `
            <div class="source-item-chat">
                <div class="source-number">${index + 1}</div>
                <div class="source-content">
                    <div class="source-title">${source.metadata?.title || 'Document'}</div>
                    <div class="source-preview">${source.content.substring(0, 150)}...</div>
                </div>
            </div>
        `).join('');
    }

    startNewSearch() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
        
        const resultsContainer = document.getElementById('results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
    }
}

// Global progress tracker instance
const progressTracker = new ProgressTracker();

// Enhanced search function that uses progress tracking
window.handleSearchWithProgress = async function(event) {
    event.preventDefault();
    
    const searchInput = document.getElementById('searchInput');
    const audienceToggle = document.getElementById('audienceToggle');
    
    const query = searchInput.value.trim();
    if (!query) {
        alert('Please enter a search query');
        return;
    }

    const audience = audienceToggle ? audienceToggle.value : 'technical';
    
    // Get selected sources from the UI
    const selectedSources = [];
    const activeOptions = document.querySelectorAll('.source-option.active');
    activeOptions.forEach(option => {
        selectedSources.push(option.dataset.source);
    });
    
    if (selectedSources.length === 0) {
        alert('Please select at least one source to search!');
        return;
    }

    // Start the progress-tracked search
    await progressTracker.startSearch(query, audience, selectedSources);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize progress tracker globally
    window.progressTracker = new ProgressTracker();
    
    console.log('✅ Progress tracker initialized');
});
