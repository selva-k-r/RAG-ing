/**
 * UI Transformer - Morphs search page into chat interface
 * Like a car transforming into a transformer robot!
 */

class UITransformer {
    constructor() {
        this.isSearchMode = true;
        this.isTransforming = false;
        this.chatHistory = [];
        this.progressTracker = null;
    }

    async transformToChat(query) {
        if (this.isTransforming || !this.isSearchMode) return;
        
        console.log('🚗→🤖 Starting UI transformation to chat mode');
        this.isTransforming = true;
        
        // Add the query to chat history
        this.chatHistory.push({
            type: 'user',
            content: query,
            timestamp: new Date()
        });

        // Step 1: Add transforming class for animation
        document.body.classList.add('transforming');
        
        // Step 2: Create chat messages container
        this.createChatContainer();
        
        // Step 3: Transform layout with staggered animations
        await this.animateTransformation();
        
        // Step 4: Switch to chat mode
        this.switchToChatMode();
        
        // Step 5: Show user message
        this.addUserMessage(query);
        
        // Step 6: Start progress tracking for AI response
        this.startAIResponse(query);
        
        this.isTransforming = false;
        this.isSearchMode = false;
        
        console.log('✅ Transformation complete - Now in chat mode');
    }

    createChatContainer() {
        // Create chat messages container if it doesn't exist
        let chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) {
            chatContainer = document.createElement('div');
            chatContainer.id = 'chatMessages';
            chatContainer.className = 'chat-messages-container';
            
            // Insert into app container
            const appContainer = document.querySelector('.container') || document.body;
            appContainer.appendChild(chatContainer);
        }
    }

    async animateTransformation() {
        // Animate header shrinking and moving to top
        const headerContainer = document.querySelector('.fixed-header');
        const mainTitle = document.querySelector('.main-title');
        const subtitle = document.querySelector('.subtitle');
        
        if (headerContainer) {
            headerContainer.style.transform = 'translateY(-7vh) scale(0.4)';
            headerContainer.style.background = 'linear-gradient(135deg, #1e88e5 0%, #26a69a 100%)';
            headerContainer.style.borderRadius = '0';
            headerContainer.style.padding = '10px 20px';
        }
        
        if (mainTitle) {
            mainTitle.style.fontSize = '24px';
            mainTitle.style.color = 'white';
            mainTitle.style.textAlign = 'left';
        }
        
        if (subtitle) {
            subtitle.style.fontSize = '12px';
            subtitle.style.color = 'rgba(255, 255, 255, 0.8)';
            subtitle.style.textAlign = 'left';
        }

        // Animate search section moving to bottom
        const searchSection = document.querySelector('.search-section-wrapper');
        if (searchSection) {
            searchSection.style.transform = 'translateY(calc(100vh - 120px))';
            searchSection.style.position = 'fixed';
            searchSection.style.bottom = '0';
            searchSection.style.left = '0';
            searchSection.style.right = '0';
            searchSection.style.background = 'white';
            searchSection.style.padding = '15px 20px';
            searchSection.style.borderTop = '1px solid #e9ecef';
            searchSection.style.boxShadow = '0 -2px 10px rgba(0, 0, 0, 0.1)';
        }

        // Animate source filters to mini icons
        const sourceFilters = document.querySelector('.source-filters');
        if (sourceFilters) {
            sourceFilters.style.transform = 'scale(0.7) translateY(-10px)';
            sourceFilters.style.gap = '6px';
            
            // Make source options smaller
            const sourceOptions = document.querySelectorAll('.source-option');
            sourceOptions.forEach(option => {
                option.style.padding = '6px 8px';
                option.style.fontSize = '10px';
                option.style.borderRadius = '15px';
            });
        }

        // Hide FAQ section with fade out
        const faqSection = document.querySelector('.faq-section');
        if (faqSection) {
            faqSection.style.opacity = '0';
            faqSection.style.transform = 'translateY(50px)';
            faqSection.style.pointerEvents = 'none';
        }

        // Wait for animations to complete
        await new Promise(resolve => setTimeout(resolve, 800));
    }

    switchToChatMode() {
        // Switch container classes
        const appContainer = document.querySelector('.container');
        if (appContainer) {
            appContainer.classList.remove('search-mode');
            appContainer.classList.add('chat-mode');
        }
        
        // Update body class
        document.body.classList.remove('search-mode');
        document.body.classList.add('chat-mode');
        document.body.classList.remove('transforming');
        
        // Show chat messages container
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.style.display = 'block';
            chatContainer.style.opacity = '1';
        }
        
        // Add reset button to header
        this.addResetButton();
    }

    addResetButton() {
        const headerRight = document.querySelector('.header-right');
        if (headerRight && !document.getElementById('resetBtn')) {
            const resetBtn = document.createElement('button');
            resetBtn.id = 'resetBtn';
            resetBtn.innerHTML = '🔄';
            resetBtn.style.cssText = `
                background: rgba(255, 255, 255, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: white;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 16px;
            `;
            resetBtn.title = 'New Conversation';
            resetBtn.onclick = () => this.resetToSearchMode();
            
            resetBtn.addEventListener('mouseenter', () => {
                resetBtn.style.background = 'rgba(255, 255, 255, 0.3)';
                resetBtn.style.transform = 'scale(1.1)';
            });
            
            resetBtn.addEventListener('mouseleave', () => {
                resetBtn.style.background = 'rgba(255, 255, 255, 0.2)';
                resetBtn.style.transform = 'scale(1)';
            });
            
            headerRight.style.display = 'flex';
            headerRight.appendChild(resetBtn);
        }
    }

    addUserMessage(query) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const messageHTML = `
            <div class="chat-message user-message" style="animation: messageSlideIn 0.4s ease;">
                <div class="message-avatar user-avatar">👤</div>
                <div class="message-content">
                    <div class="message-text">${query}</div>
                    <div class="message-time">${new Date().toLocaleTimeString()}</div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }

    async startAIResponse(query) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        // Add AI message with typing indicator
        const aiMessageHTML = `
            <div class="chat-message ai-message" id="currentAIMessage" style="animation: messageSlideIn 0.4s ease;">
                <div class="message-avatar ai-avatar">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator" id="typingIndicator">
                        <div class="typing-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <span class="typing-text">AI is thinking...</span>
                    </div>
                    <div class="message-text" id="aiResponseText" style="display: none;"></div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', aiMessageHTML);
        this.scrollToBottom();

        // Start the actual search with progress
        try {
            const sources = this.getSelectedSources();
            await this.startSearchWithChatIntegration(query, sources);
            
        } catch (error) {
            console.error('Error starting AI response:', error);
            this.showAIError('Sorry, I encountered an error processing your request.');
        }
    }

    async startSearchWithChatIntegration(query, sources) {
        try {
            // Start the search
            const response = await fetch('/api/search-with-progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    audience: 'technical',
                    sources: sources
                })
            });

            const data = await response.json();
            const sessionId = data.session_id;

            // Connect to progress stream
            const eventSource = new EventSource(`/api/progress/${sessionId}`);

            eventSource.onmessage = (event) => {
                try {
                    const progressData = JSON.parse(event.data);
                    
                    // Update typing indicator text
                    this.updateTypingIndicator(progressData);
                    
                    if (progressData.type === 'complete') {
                        eventSource.close();
                        this.loadAndStreamResponse(sessionId);
                    }
                    
                } catch (error) {
                    console.error('Progress parsing error:', error);
                }
            };

            eventSource.onerror = (error) => {
                console.error('Progress stream error:', error);
                eventSource.close();
                this.showAIError('Connection error occurred.');
            };

        } catch (error) {
            console.error('Search initiation error:', error);
            this.showAIError('Failed to start search.');
        }
    }

    updateTypingIndicator(progressData) {
        const typingText = document.querySelector('.typing-text');
        if (!typingText) return;

        const messages = [
            "AI is initializing...",
            "Searching knowledge base...",
            "Analyzing documents...",
            "Processing context...",
            "Generating response...",
            "Finalizing answer..."
        ];

        const step = progressData.step || 0;
        if (step < messages.length) {
            typingText.textContent = messages[step];
        }
    }

    async loadAndStreamResponse(sessionId) {
        try {
            const response = await fetch(`/api/result/${sessionId}`);
            const result = await response.json();
            
            if (result.error) {
                this.showAIError(result.error);
                return;
            }

            // Hide typing indicator and show streaming text
            const typingIndicator = document.getElementById('typingIndicator');
            const responseText = document.getElementById('aiResponseText');
            
            if (typingIndicator) typingIndicator.style.display = 'none';
            if (responseText) responseText.style.display = 'block';

            // Stream the response text
            await this.streamText(result.response, responseText);
            
            // Add sources after streaming completes
            this.addSourcesMessage(result.sources, result.metadata);

        } catch (error) {
            console.error('Error loading final result:', error);
            this.showAIError('Failed to load response.');
        }
    }

    async streamText(text, container) {
        if (!container) return;

        let index = 0;
        const speed = 25; // 25ms per character for smooth streaming

        return new Promise((resolve) => {
            const typeWriter = () => {
                if (index < text.length) {
                    container.innerHTML = this.formatText(text.substring(0, index + 1));
                    index++;
                    this.scrollToBottom();
                    setTimeout(typeWriter, speed);
                } else {
                    resolve();
                }
            };
            typeWriter();
        });
    }

    formatText(text) {
        // Convert markdown-like formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }

    addSourcesMessage(sources, metadata) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer || !sources || sources.length === 0) return;

        const processingTime = metadata?.processing_time || 0;
        const confidenceScore = metadata?.confidence_score || 0.8;

        const sourcesHTML = `
            <div class="chat-message ai-message" style="animation: messageSlideIn 0.4s ease;">
                <div class="message-avatar ai-avatar">📚</div>
                <div class="message-content">
                    <div class="sources-header">
                        <div class="confidence-badge ${this.getConfidenceClass(confidenceScore)}">
                            🎯 ${Math.round(confidenceScore * 100)}% Confidence
                        </div>
                        <div class="processing-stats">
                            ⏱️ ${Math.round(processingTime)}s • 📖 ${sources.length} sources
                        </div>
                    </div>
                    <div class="sources-list">
                        ${this.formatSources(sources.slice(0, 3))}
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', sourcesHTML);
        this.scrollToBottom();
    }

    formatSources(sources) {
        return sources.map((source, index) => `
            <div class="source-item" style="margin: 8px 0; padding: 10px; background: #f8f9fa; border-radius: 8px; border-left: 3px solid #007bff;">
                <div style="font-weight: 600; color: #2c3e50; font-size: 13px; margin-bottom: 4px;">
                    ${index + 1}. ${source.metadata?.title || 'Document'}
                </div>
                <div style="color: #6c757d; font-size: 12px; line-height: 1.4;">
                    ${source.content.substring(0, 120)}...
                </div>
            </div>
        `).join('');
    }

    getConfidenceClass(score) {
        if (score >= 0.8) return 'confidence-high';
        if (score >= 0.6) return 'confidence-medium';
        return 'confidence-low';
    }

    showAIError(message) {
        const typingIndicator = document.getElementById('typingIndicator');
        const responseText = document.getElementById('aiResponseText');
        
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (responseText) {
            responseText.style.display = 'block';
            responseText.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 8px; border: 1px solid #f5c6cb;">❌ ${message}</div>`;
        }
    }

    getSelectedSources() {
        const selectedSources = [];
        const activeOptions = document.querySelectorAll('.source-option.active');
        activeOptions.forEach(option => {
            selectedSources.push(option.dataset.source);
        });
        return selectedSources.length > 0 ? selectedSources : ['confluence', 'jira', 'internal'];
    }

    scrollToBottom() {
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // Handle new searches in chat mode
    async handleChatSearch(query) {
        if (this.isSearchMode) {
            // First search - transform to chat
            await this.transformToChat(query);
        } else {
            // Subsequent searches - just add to chat
            this.addUserMessage(query);
            this.startAIResponse(query);
        }
    }

    // Reset to search mode (for new session)
    resetToSearchMode() {
        console.log('🤖→🚗 Transforming back to search mode');
        
        // Reset classes
        document.body.classList.remove('chat-mode', 'transforming');
        document.body.classList.add('search-mode');
        
        const appContainer = document.querySelector('.container');
        if (appContainer) {
            appContainer.classList.remove('chat-mode');
            appContainer.classList.add('search-mode');
        }

        // Reset header
        const headerContainer = document.querySelector('.fixed-header');
        if (headerContainer) {
            headerContainer.style.transform = '';
            headerContainer.style.background = '';
            headerContainer.style.borderRadius = '';
            headerContainer.style.padding = '';
        }

        // Reset search section
        const searchSection = document.querySelector('.search-section-wrapper');
        if (searchSection) {
            searchSection.style.transform = '';
            searchSection.style.position = '';
            searchSection.style.bottom = '';
            searchSection.style.background = '';
            searchSection.style.padding = '';
            searchSection.style.borderTop = '';
            searchSection.style.boxShadow = '';
        }

        // Show FAQ section
        const faqSection = document.querySelector('.faq-section');
        if (faqSection) {
            faqSection.style.opacity = '1';
            faqSection.style.transform = '';
            faqSection.style.pointerEvents = '';
        }

        // Clear chat messages
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
            chatContainer.style.display = 'none';
        }

        // Reset state
        this.isSearchMode = true;
        this.chatHistory = [];
        
        // Clear search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
    }
}

// Global transformer instance
const uiTransformer = new UITransformer();

// Enhanced search function that triggers transformation
window.handleTransformerSearch = async function(event) {
    if (event && event.preventDefault) event.preventDefault();
    
    const searchInput = document.getElementById('searchInput');
    const query = searchInput ? searchInput.value.trim() : '';
    
    if (!query) {
        alert('Please enter a search query');
        return;
    }

    console.log('🚀 Starting transformer search:', query);
    
    // Get selected sources
    const selectedSources = [];
    const activeOptions = document.querySelectorAll('.source-option.active');
    activeOptions.forEach(option => {
        selectedSources.push(option.dataset.source);
    });
    
    if (selectedSources.length === 0) {
        alert('Please select at least one source to search!');
        return;
    }

    // Start the transformation and search
    await uiTransformer.handleChatSearch(query);
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set initial search mode
    document.body.classList.add('search-mode');
    const appContainer = document.querySelector('.container');
    if (appContainer) {
        appContainer.classList.add('search-mode');
    }
    
    // Add reset button for testing
    const headerRight = document.querySelector('.header-right');
    if (headerRight) {
        const resetBtn = document.createElement('button');
        resetBtn.innerHTML = '🔄';
        resetBtn.style.cssText = `
            background: none;
            border: 2px solid #007bff;
            color: #007bff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
            margin-left: 10px;
            transition: all 0.3s ease;
        `;
        resetBtn.title = 'Reset to search mode';
        resetBtn.onclick = () => uiTransformer.resetToSearchMode();
        headerRight.appendChild(resetBtn);
    }
    
    console.log('🎬 UI Transformer initialized');
});

// Add CSS for confidence badges
const style = document.createElement('style');
style.textContent = `
    .confidence-high { background: linear-gradient(135deg, #28a745, #20c997); color: white; }
    .confidence-medium { background: linear-gradient(135deg, #ffc107, #fd7e14); color: #2c3e50; }
    .confidence-low { background: linear-gradient(135deg, #dc3545, #c82333); color: white; }
    .confidence-badge { 
        padding: 4px 12px; 
        border-radius: 12px; 
        font-size: 11px; 
        font-weight: 600; 
        display: inline-block;
    }
    .sources-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 10px; 
        padding-bottom: 8px; 
        border-bottom: 1px solid #e9ecef; 
    }
    .processing-stats { 
        font-size: 11px; 
        color: #6c757d; 
    }
    .message-time {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 5px;
        text-align: right;
    }
    .ai-message .message-time {
        color: #6c757d;
    }
`;
document.head.appendChild(style);
