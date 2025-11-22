/**
 * Clean UI Transformer - Single avatar system, proper layout
 * Transforms search page to chat interface smoothly
 */

class CleanTransformer {
    constructor() {
        this.isSearchMode = true;
        this.isTransforming = false;
        this.currentSessionId = null;
    }

    /**
     * Sanitize text content to prevent XSS attacks
     * @param {string} text - The text to sanitize
     * @returns {string} - HTML-safe text
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Validate URL to prevent protocol attacks and ensure well-formed URLs
     * @param {string} url - The URL to validate
     * @returns {boolean} - True if URL is safe and well-formed
     */
    isValidUrl(url) {
        if (!url) return false;
        
        try {
            // Use URL constructor for proper validation
            const urlObj = new URL(url);
            
            // Only allow http and https protocols
            const allowedProtocols = ['http:', 'https:'];
            return allowedProtocols.includes(urlObj.protocol);
        } catch (e) {
            // Invalid URL format
            return false;
        }
    }

    async transformToChat(query) {
        if (this.isTransforming || !this.isSearchMode) {
            return this.addChatMessage(query); // Just add to existing chat
        }
        
        console.log('🚗→🤖 Starting clean transformation');
        this.isTransforming = true;
        
        // Fix #3: Clear search input on first search too
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
            console.log('✅ Cleared search input on first search');
        }
        
        // Step 1: Add transforming class
        document.body.classList.add('transforming');
        
        // Step 2: Animate all elements simultaneously
        await this.animateToChat();
        
        // Step 3: Switch to chat mode
        this.switchToChatMode();
        
        // Step 4: Add user message
        this.addUserMessage(query);
        
        // Step 5: Start AI response
        await this.startAIResponse(query);
        
        this.isTransforming = false;
        this.isSearchMode = false;
    }

    async animateToChat() {
        // Get all elements
        const header = document.querySelector('.fixed-header');
        const searchSection = document.querySelector('.search-section-wrapper');
        const sourceFilters = document.querySelector('.datasource-section-wrapper');
        const faqSection = document.querySelector('.content-wrapper');
        const userAvatar = document.querySelector('.original-user-avatar');
        
        // Animate header to top with high z-index to prevent overlap
        if (header) {
            header.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                height: 65px !important;
                background: linear-gradient(135deg, #1e88e5 0%, #26a69a 100%) !important;
                padding: 12px 20px !important;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
                transform: none !important;
                max-width: none !important;
                z-index: 1002 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
            `;
            
            // Update title styling
            const title = header.querySelector('.main-title');
            const subtitle = header.querySelector('.subtitle');
            
            if (title) {
                title.style.cssText += `
                    font-size: 24px !important;
                    color: white !important;
                    text-align: left !important;
                    background: none !important;
                    -webkit-text-fill-color: white !important;
                    margin: 0 !important;
                    font-weight: 300 !important;
                    letter-spacing: 1px !important;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
                `;
            }
            
            if (subtitle) {
                subtitle.style.cssText += `
                    font-size: 11px !important;
                    color: rgba(255, 255, 255, 0.9) !important;
                    text-align: left !important;
                    margin: 2px 0 0 0 !important;
                    font-weight: 400 !important;
                    text-shadow: 0 1px 1px rgba(0, 0, 0, 0.1) !important;
                    display: block !important;
                    opacity: 1 !important;
                `;
            }
        }
        
        // Animate search bar to bottom (completely repositioned)
        if (searchSection) {
            searchSection.style.cssText = `
                position: fixed !important;
                bottom: 45px !important;
                left: 0 !important;
                right: 0 !important;
                top: auto !important;
                background: white !important;
                padding: 12px 20px !important;
                border-top: 1px solid #e9ecef !important;
                box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1) !important;
                transform: none !important;
                width: auto !important;
                max-width: none !important;
                z-index: 999 !important;
                height: 65px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            `;
            
            // Update search input and button
            const searchInput = searchSection.querySelector('.search-input');
            const searchBtn = searchSection.querySelector('.search-btn');
            
            if (searchInput) {
                searchInput.style.cssText += `
                    width: 100% !important;
                    padding: 12px 50px 12px 20px !important;
                    font-size: 16px !important;
                    border-radius: 25px !important;
                    border: 2px solid #e9ecef !important;
                `;
            }
            
            if (searchBtn) {
                searchBtn.style.cssText += `
                    position: absolute !important;
                    right: 8px !important;
                    top: 50% !important;
                    transform: translateY(-50%) !important;
                    width: 36px !important;
                    height: 36px !important;
                    z-index: 1001 !important;
                `;
            }
        }
        
        // Animate source filters to bottom (under search bar with spacing)
        if (sourceFilters) {
            sourceFilters.style.cssText += `
                position: fixed !important;
                bottom: 0px !important;
                left: 0 !important;
                right: 0 !important;
                display: flex !important;
                justify-content: center !important;
                gap: 4px !important;
                z-index: 998 !important;
                background: #f8f9fa !important;
                padding: 8px 20px !important;
                border-top: 1px solid #e9ecef !important;
                height: 45px !important;
                transform: none !important;
            `;
            
            // Make source options smaller
            const sourceOptions = sourceFilters.querySelectorAll('.source-option');
            sourceOptions.forEach(option => {
                option.style.cssText += `
                    padding: 3px 6px !important;
                    font-size: 8px !important;
                    border-radius: 10px !important;
                    min-width: auto !important;
                    transform: scale(0.8) !important;
                    margin: 0 1px !important;
                `;
            });
        }
        
        // Hide FAQ section
        if (faqSection) {
            faqSection.style.cssText += `
                opacity: 0 !important;
                transform: translateY(50px) !important;
                pointer-events: none !important;
            `;
        }
        
        // Transform user avatar to chat indicator
        if (userAvatar) {
            userAvatar.style.cssText += `
                top: 15px !important;
                right: 70px !important;
                width: 35px !important;
                height: 35px !important;
                background: rgba(255, 255, 255, 0.2) !important;
                border: 2px solid rgba(255, 255, 255, 0.3) !important;
            `;
            userAvatar.innerHTML = '💬';
            userAvatar.title = 'Chat Mode';
        }
        
        // Wait for animations
        await new Promise(resolve => setTimeout(resolve, 800));
    }

    switchToChatMode() {
        document.body.classList.remove('search-mode', 'transforming');
        document.body.classList.add('chat-mode');
        
        // Show chat container with proper spacing to avoid overlap
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.style.cssText += `
                display: block !important;
                position: fixed !important;
                top: 75px !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 110px !important;
                overflow-y: auto !important;
                padding: 20px !important;
                background: #f8f9fa !important;
                opacity: 1 !important;
                z-index: 100 !important;
            `;
        }
        
        // Event delegation handles search button - no need for manual setup
    }

    addUserMessage(query) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        // Sanitize user query to prevent XSS
        const safeQuery = this.escapeHtml(query);

        const messageHTML = `
            <div class="chat-message user-message" style="animation: slideInRight 0.4s ease;">
                <div class="message-avatar user-chat-avatar">👤</div>
                <div class="message-content user-content">
                    <div class="message-text">${safeQuery}</div>
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
            <div class="chat-message ai-message" style="animation: slideInLeft 0.4s ease;">
                <div class="message-avatar ai-chat-avatar">🤖</div>
                <div class="message-content ai-content">
                    <div class="typing-indicator" id="typingIndicator">
                        <div class="typing-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <span class="typing-text">AI is analyzing your query...</span>
                    </div>
                    <div class="message-text" id="aiResponseText" style="display: none;"></div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', aiMessageHTML);
        this.scrollToBottom();

        // Start the search
        await this.performSearch(query);
    }

    async performSearch(query) {
        try {
            const sources = this.getSelectedSources();
            
            // Start search with progress
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
            this.currentSessionId = data.session_id;

            // Connect to progress stream
            this.connectToProgressStream();

        } catch (error) {
            console.error('Search error:', error);
            
            // Try to extract detailed error from response
            if (error.response) {
                try {
                    const errorData = await error.response.json();
                    this.showAIError(errorData.user_message || errorData.message || 'Failed to start search', errorData);
                } catch (e) {
                    this.showAIError('Failed to start search. Check console for details.', {error: error.message});
                }
            } else {
                this.showAIError('Failed to start search. Check console for details.', {error: error.message});
            }
        }
    }

    connectToProgressStream() {
        if (!this.currentSessionId) return;

        const eventSource = new EventSource(`/api/progress/${this.currentSessionId}`);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // Update typing indicator
                this.updateTypingIndicator(data);
                
                if (data.type === 'complete') {
                    eventSource.close();
                    this.loadFinalResponse();
                }
                
            } catch (error) {
                console.error('Progress error:', error);
            }
        };

        eventSource.onerror = () => {
            eventSource.close();
            this.showAIError('Connection error');
        };
    }

    updateTypingIndicator(data) {
        // Find the LAST (most recent) typing indicator
        const typingTexts = document.querySelectorAll('.typing-text');
        const typingText = typingTexts[typingTexts.length - 1]; // Get the last one
        
        if (!typingText) {
            console.warn('No typing indicator found');
            return;
        }

        const messages = [
            "AI is initializing...",
            "Searching knowledge base...",
            "Analyzing documents...",
            "Processing context...",
            "Generating response...",
            "Finalizing answer..."
        ];

        const step = data.step || 0;
        if (step < messages.length) {
            typingText.textContent = messages[step];
            console.log(`📊 Progress update: ${messages[step]} (${data.progress || 0}%)`);
        }
    }

    async loadFinalResponse() {
        try {
            const response = await fetch(`/api/result/${this.currentSessionId}`);
            const result = await response.json();
            
            if (result.error) {
                this.showAIError(result.error);
                return;
            }

            console.log('✅ Final response loaded, starting text streaming');
            console.log('📊 Result metadata:', result.metadata);
            console.log('📊 Sources count:', result.sources?.length);

            // Find the LAST (most recent) typing indicator and response text
            const typingIndicators = document.querySelectorAll('.typing-indicator');
            const responseTexts = document.querySelectorAll('#aiResponseText, .message-text[style*="display: none"]');
            
            const typingIndicator = typingIndicators[typingIndicators.length - 1];
            const responseText = responseTexts[responseTexts.length - 1];
            
            if (typingIndicator) {
                typingIndicator.style.display = 'none';
                console.log('✅ Typing indicator hidden');
            }
            
            if (responseText) {
                responseText.style.display = 'block';
                console.log('✅ Response text container shown');
                
                // Stream the text
                await this.streamText(result.response, responseText);
                console.log('✅ Text streaming completed');
            } else {
                console.error('❌ Response text container not found');
                this.showAIError('Could not display response');
                return;
            }
            
            // Add sources
            this.addSourcesMessage(result.sources, result.metadata);

        } catch (error) {
            console.error('Result error:', error);
            this.showAIError('Failed to load response');
        }
    }

    async streamText(text, container) {
        if (!container) return;

        let index = 0;
        const speed = 5; // Much faster - 5ms per character instead of 25ms

        return new Promise((resolve) => {
            const typeWriter = () => {
                if (index < text.length) {
                    // Add multiple characters at once for even faster rendering
                    const charsToAdd = Math.min(3, text.length - index); // Add 3 chars at a time
                    container.innerHTML = this.formatText(text.substring(0, index + charsToAdd));
                    index += charsToAdd;
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
        // Enhanced markdown formatting for human readability
        let formatted = text;
        
        // Handle tables first (before other formatting)
        formatted = this.formatTables(formatted);
        
        // Handle headers
        formatted = formatted.replace(/^### (.*$)/gm, '<h3 style="color: #2c3e50; font-size: 18px; font-weight: 600; margin: 20px 0 10px 0; border-bottom: 2px solid #e9ecef; padding-bottom: 5px;">$1</h3>');
        formatted = formatted.replace(/^## (.*$)/gm, '<h2 style="color: #1e88e5; font-size: 20px; font-weight: 600; margin: 25px 0 15px 0; border-bottom: 2px solid #1e88e5; padding-bottom: 8px;">$1</h2>');
        formatted = formatted.replace(/^# (.*$)/gm, '<h1 style="color: #1e88e5; font-size: 24px; font-weight: 700; margin: 30px 0 20px 0;">$1</h1>');
        
        // Handle bold and italic
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #2c3e50; font-weight: 600;">$1</strong>');
        formatted = formatted.replace(/\*(.*?)\*/g, '<em style="color: #495057; font-style: italic;">$1</em>');
        
        // Handle bullet points
        formatted = formatted.replace(/^- (.*$)/gm, '<li style="margin: 8px 0; padding-left: 5px;">$1</li>');
        formatted = formatted.replace(/(<li.*<\/li>)/s, '<ul style="margin: 15px 0; padding-left: 20px; list-style-type: disc;">$1</ul>');
        
        // Handle numbered lists
        formatted = formatted.replace(/^\d+\. (.*$)/gm, '<li style="margin: 8px 0; padding-left: 5px;">$1</li>');
        
        // Handle code blocks
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 15px; margin: 15px 0; overflow-x: auto; font-family: monospace; font-size: 13px; line-height: 1.4;"><code>$1</code></pre>');
        
        // Handle inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 3px; padding: 2px 6px; font-family: monospace; font-size: 13px; color: #e83e8c;">$1</code>');
        
        // Handle paragraphs with proper spacing
        formatted = formatted.replace(/\n\n/g, '</p><p style="margin: 15px 0; line-height: 1.6;">');
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Wrap in paragraph tags
        if (!formatted.startsWith('<h') && !formatted.startsWith('<ul') && !formatted.startsWith('<ol') && !formatted.startsWith('<pre') && !formatted.startsWith('<table')) {
            formatted = '<p style="margin: 15px 0; line-height: 1.6;">' + formatted + '</p>';
        }
        
        return formatted;
    }

    formatTables(text) {
        // Convert markdown tables to HTML tables
        const lines = text.split('\n');
        let inTable = false;
        let tableRows = [];
        let result = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Check if line contains table separators (|)
            if (line.includes('|') && line.split('|').length > 2) {
                if (!inTable) {
                    inTable = true;
                    tableRows = [];
                }
                
                // Clean up the line and split by |
                const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
                
                // Skip separator lines (like |---|---|---|)
                if (!cells[0].match(/^-+$/)) {
                    tableRows.push(cells);
                }
            } else {
                // End of table
                if (inTable && tableRows.length > 0) {
                    result.push(this.createHTMLTable(tableRows));
                    tableRows = [];
                    inTable = false;
                }
                result.push(line);
            }
        }
        
        // Handle table at end of text
        if (inTable && tableRows.length > 0) {
            result.push(this.createHTMLTable(tableRows));
        }
        
        return result.join('\n');
    }

    createHTMLTable(rows) {
        if (rows.length === 0) return '';
        
        let html = '<table style="width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;">';
        
        // Header row
        if (rows.length > 0) {
            html += '<thead style="background: linear-gradient(135deg, #1e88e5, #26a69a);">';
            html += '<tr>';
            rows[0].forEach(cell => {
                html += `<th style="padding: 12px 15px; color: white; font-weight: 600; text-align: left; border-bottom: 2px solid rgba(255,255,255,0.2);">${cell}</th>`;
            });
            html += '</tr>';
            html += '</thead>';
        }
        
        // Body rows
        if (rows.length > 1) {
            html += '<tbody>';
            for (let i = 1; i < rows.length; i++) {
                const isEven = (i - 1) % 2 === 0;
                const bgColor = isEven ? '#ffffff' : '#f8f9fa';
                
                html += `<tr style="background: ${bgColor};">`;
                rows[i].forEach(cell => {
                    html += `<td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; color: #2c3e50; font-size: 14px;">${cell}</td>`;
                });
                html += '</tr>';
            }
            html += '</tbody>';
        }
        
        html += '</table>';
        return html;
    }

    addSourcesMessage(sources, metadata) {
        if (!sources || sources.length === 0) return;

        const chatContainer = document.getElementById('chatMessages');
        
        // DEBUG: Log what we receive
        console.log('📊 addSourcesMessage called with:', {
            sourcesCount: sources.length,
            metadata: metadata
        });
        
        // Fix #2: Use response_time instead of processing_time
        const processingTime = metadata?.response_time || 0;
        console.log('⏱️ Processing time:', processingTime);
        
        // Fix #1: Calculate confidence dynamically from sources
        const confidenceScore = this.calculateConfidenceScore(sources, metadata);
        console.log('🎯 Calculated confidence:', confidenceScore);

        const sourcesHTML = `
            <div class="chat-message ai-message" style="animation: slideInLeft 0.4s ease;">
                <div class="message-avatar ai-chat-avatar">📚</div>
                <div class="message-content ai-content">
                    <div class="sources-header">
                        <span class="confidence-badge confidence-${this.getConfidenceLevel(confidenceScore)}">
                            🎯 ${Math.round(confidenceScore * 100)}% Confidence
                        </span>
                        <span class="processing-stats">
                            ⏱️ ${Math.round(processingTime)}s • 📖 ${sources.length} sources
                        </span>
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
        return sources.map((source, index) => {
            const metadata = source.metadata || {};
            const isCodeFile = metadata.type === 'azure_devops_file';
            const hasLineNumbers = metadata.start_line && metadata.end_line;
            
            // Sanitize all metadata fields to prevent XSS
            const safeTitle = this.escapeHtml(metadata.title || 'Document');
            const safeLanguage = this.escapeHtml(metadata.language || 'code');
            const safeRepo = this.escapeHtml(metadata.repository || 'Repository');
            const safeFilePath = this.escapeHtml(metadata.file_path || safeTitle);
            
            // Build source header
            let sourceHeader = `${index + 1}. ${safeTitle}`;
            
            // Add code-specific metadata
            let codeInfo = '';
            if (isCodeFile) {
                // Add language badge with sanitized content
                codeInfo += `<span style="display: inline-block; background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">${safeLanguage}</span>`;
                
                // Add line numbers if available (numbers are safe)
                if (hasLineNumbers) {
                    const startLine = parseInt(metadata.start_line, 10) || 0;
                    const endLine = parseInt(metadata.end_line, 10) || 0;
                    codeInfo += `<span style="display: inline-block; background: #f1f3f5; color: #495057; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 4px;">Lines ${startLine}-${endLine}</span>`;
                }
                
                // Add repository info with sanitized content
                sourceHeader = `${index + 1}. 📁 ${safeRepo} / ${safeFilePath}`;
            }
            
            // Build Azure DevOps link if available - validate URL first
            let linkHtml = '';
            if (metadata.url && isCodeFile && this.isValidUrl(metadata.url)) {
                // URL is validated and safe to use directly in href (no HTML escaping needed)
                // Determine display text based on hostname (not substring search)
                let displayText = 'View Source';
                try {
                    const urlObj = new URL(metadata.url);
                    // Check if hostname ends with dev.azure.com to avoid substring attacks
                    if (urlObj.hostname.endsWith('dev.azure.com')) {
                        displayText = 'View in Azure DevOps';
                    }
                } catch (e) {
                    // If URL parsing fails, use generic text (shouldn't happen as isValidUrl already checked)
                }
                const safeDisplayText = this.escapeHtml(displayText);
                linkHtml = `
                    <div style="margin-top: 6px;">
                        <a href="${metadata.url}" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: none; font-size: 11px; font-weight: 500;">
                            🔗 ${safeDisplayText} →
                        </a>
                    </div>
                `;
            }
            
            // Format content preview with sanitization
            const previewLength = isCodeFile ? 150 : 120;
            const rawContent = (source.content || '').substring(0, previewLength);
            const safeContent = this.escapeHtml(rawContent);
            
            // For code, preserve formatting
            let contentPreview;
            if (isCodeFile) {
                contentPreview = `<pre style="background: #ffffff; padding: 8px; border-radius: 4px; margin-top: 6px; overflow-x: auto; font-size: 11px; line-height: 1.4; white-space: pre-wrap;">${safeContent}...</pre>`;
            } else {
                contentPreview = `<div style="color: #6c757d; font-size: 12px; line-height: 1.4;">${safeContent}...</div>`;
            }
            
            return `
                <div class="source-item" style="margin: 8px 0; padding: 10px; background: #f1f3f5; border-radius: 8px; border-left: 3px solid ${isCodeFile ? '#4caf50' : '#007bff'};">
                    <div style="font-weight: 600; color: #2c3e50; font-size: 13px; margin-bottom: 4px;">
                        ${sourceHeader}${codeInfo}
                    </div>
                    ${contentPreview}
                    ${linkHtml}
                </div>
            `;
        }).join('');
    }

    calculateConfidenceScore(sources, metadata) {
        // Calculate confidence based on multiple factors
        if (!sources || sources.length === 0) return 0.5;
        
        // Factor 1: Number of sources (more sources = higher confidence)
        const sourceCountScore = Math.min(sources.length / 5, 1.0) * 0.3;
        
        // Factor 2: Source diversity (different sources = higher confidence)
        const uniqueSources = metadata?.unique_sources || sources.length;
        const diversityScore = Math.min(uniqueSources / 3, 1.0) * 0.3;
        
        // Factor 3: Response time (faster = higher confidence, though less weight)
        const responseTime = metadata?.response_time || 10;
        const speedScore = Math.max(1.0 - (responseTime / 20), 0) * 0.1;
        
        // Factor 4: Base confidence (has relevant docs)
        const baseScore = 0.3;
        
        const totalScore = baseScore + sourceCountScore + diversityScore + speedScore;
        
        // Return score between 0.5 and 1.0 for better UX
        return Math.max(0.5, Math.min(totalScore, 1.0));
    }

    getConfidenceLevel(score) {
        if (score >= 0.8) return 'high';
        if (score >= 0.6) return 'medium';
        return 'low';
    }

    showAIError(message, errorDetails = null) {
        // Find the most recent typing indicator and response text
        const typingIndicators = document.querySelectorAll('.typing-indicator');
        const responseTexts = document.querySelectorAll('#aiResponseText, .message-text');
        
        const typingIndicator = typingIndicators[typingIndicators.length - 1];
        const responseText = responseTexts[responseTexts.length - 1];
        
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (responseText) {
            responseText.style.display = 'block';
            
            // Sanitize error message first
            const safeMessage = this.escapeHtml(message);
            
            // If message contains markdown formatting, render it properly
            let formattedMessage;
            if (message.includes('##') || message.includes('**') || message.includes('- ') || message.includes('`')) {
                // Use the same markdown formatting as regular responses (on sanitized text)
                formattedMessage = this.formatText(safeMessage);
            } else {
                // Simple text error
                formattedMessage = `<div style="color: #dc3545;">${safeMessage}</div>`;
            }
            
            // Build error display
            let errorHtml = `
                <div style="background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #dc3545; margin-bottom: 15px;">
                    ${formattedMessage}
                </div>
            `;
            
            // Add developer details if available - sanitize all error details
            if (errorDetails && (errorDetails.error_details || errorDetails.traceback)) {
                const safeErrorDetails = this.escapeHtml(errorDetails.error_details || errorDetails.message || '');
                const safeTraceback = this.escapeHtml(errorDetails.traceback || '');
                const safeFixInstructions = this.escapeHtml(errorDetails.fix_instructions || '');
                
                errorHtml += `
                    <details style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px; cursor: pointer;">
                        <summary style="font-weight: bold; color: #495057; cursor: pointer;">
                            🔍 Developer Details (Click to expand)
                        </summary>
                        <div style="margin-top: 10px; padding: 10px; background: #ffffff; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 12px; color: #212529; white-space: pre-wrap; overflow-x: auto;">
                            ${safeErrorDetails}
                            ${safeTraceback ? '\n\nTraceback:\n' + safeTraceback : ''}
                            ${safeFixInstructions ? '\n\nFix Instructions:\n' + safeFixInstructions : ''}
                        </div>
                    </details>
                `;
            }
            
            responseText.innerHTML = errorHtml;
        }
        
        // Log to console for developers
        console.error('AI Error displayed:', message);
        if (errorDetails) {
            console.error('Error details:', errorDetails);
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

    // Add message to existing chat (for follow-up queries)
    async addChatMessage(query) {
        this.addUserMessage(query);
        await this.startAIResponse(query);
    }

    // Reset to search mode
    resetToSearchMode() {
        console.log('🤖→🚗 Resetting to search mode');
        
        // Reset all inline styles
        const header = document.querySelector('.fixed-header');
        const searchSection = document.querySelector('.search-section-wrapper');
        const sourceFilters = document.querySelector('.datasource-section-wrapper');
        const faqSection = document.querySelector('.content-wrapper');
        const userAvatar = document.querySelector('.original-user-avatar');
        
        if (header) header.style.cssText = '';
        if (searchSection) searchSection.style.cssText = '';
        if (sourceFilters) sourceFilters.style.cssText = '';
        if (faqSection) faqSection.style.cssText = '';
        if (userAvatar) {
            userAvatar.style.cssText = '';
            userAvatar.innerHTML = '';
            userAvatar.title = 'User Profile';
        }
        
        // Reset title styles
        const title = document.querySelector('.main-title');
        const subtitle = document.querySelector('.subtitle');
        if (title) title.style.cssText = '';
        if (subtitle) subtitle.style.cssText = '';
        
        // Reset classes
        document.body.classList.remove('chat-mode', 'transforming');
        document.body.classList.add('search-mode');
        
        // Clear chat messages
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
            chatContainer.style.display = 'none';
        }
        
        // Clear search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
        
        // Reset state
        this.isSearchMode = true;
        this.currentSessionId = null;
        
        // Remove reset button
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) resetBtn.remove();
    }
}

// Global transformer instance
const cleanTransformer = new CleanTransformer();
window.cleanTransformer = cleanTransformer;

// Main search handler
window.handleCleanTransformerSearch = async function(event) {
    if (event && event.preventDefault) event.preventDefault();
    
    const searchInput = document.getElementById('searchInput');
    const query = searchInput ? searchInput.value.trim() : '';
    
    if (!query) {
        alert('Please enter a search query');
        return;
    }

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

    console.log('🚀 Clean transformer search:', query);
    
    // Fix #3: Clear search input after submission
    if (searchInput) {
        searchInput.value = '';
    }
    await cleanTransformer.transformToChat(query);
};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Set initial search mode
    document.body.classList.add('search-mode');
    
    console.log('✅ Clean transformer initialized');
});

// Add required CSS for chat messages
const chatStyles = document.createElement('style');
chatStyles.textContent = `
    .chat-message {
        display: flex;
        gap: 15px;
        margin-bottom: 25px;
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
        padding: 0 10px;
        clear: both;
        position: relative;
    }
    
    .user-message {
        flex-direction: row-reverse;
    }
    
    .message-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .user-chat-avatar {
        background: linear-gradient(135deg, #007bff, #0056b3);
    }
    
    .ai-chat-avatar {
        background: linear-gradient(135deg, #28a745, #1e7e34);
    }
    
    .message-content {
        max-width: 75%;
        background: white;
        border-radius: 18px;
        padding: 18px 22px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid #e9ecef;
        position: relative;
        word-wrap: break-word;
        overflow-wrap: break-word;
        line-height: 1.6;
        font-size: 14px;
        color: #2c3e50;
    }
    
    .user-content {
        background: linear-gradient(135deg, #007bff, #0056b3);
        color: white;
        text-shadow: none;
    }
    
    .ai-content {
        background: white;
        border: 1px solid #e9ecef;
    }
    
    .message-time {
        font-size: 10px;
        opacity: 0.7;
        margin-top: 5px;
        text-align: right;
    }
    
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #6c757d;
        font-style: italic;
    }
    
    .typing-dots {
        display: flex;
        gap: 4px;
    }
    
    .typing-dots span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgba(0, 123, 255, 0.6);
        animation: typingBounce 1.4s ease-in-out infinite both;
    }
    
    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typingBounce {
        0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
    
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(50px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-50px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
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
`;
document.head.appendChild(chatStyles);
