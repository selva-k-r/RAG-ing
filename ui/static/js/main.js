/**
 * Main JavaScript functionality for the RAG system UI
 */

class RAGInterface {
    constructor() {
        this.initializeEventListeners();
        this.searchResults = null;
    }

    initializeEventListeners() {
        // Search form submission
        const searchForm = document.getElementById('searchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => this.handleSearch(e));
        }

        // Enter key in search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleSearch(e);
                }
            });
        }

        // Audience toggle
        const audienceToggle = document.getElementById('audienceToggle');
        if (audienceToggle) {
            audienceToggle.addEventListener('change', () => this.updateAudienceDisplay());
        }
    }

    async handleSearch(event) {
        event.preventDefault();
        
        const searchInput = document.getElementById('searchInput');
        const audienceToggle = document.getElementById('audienceToggle');
        const resultsContainer = document.getElementById('results');
        const loadingIndicator = document.getElementById('loading');
        
        const query = searchInput.value.trim();
        if (!query) {
            this.showError('Please enter a search query');
            return;
        }

        // Show loading state
        if (loadingIndicator) loadingIndicator.style.display = 'flex';
        if (resultsContainer) resultsContainer.innerHTML = '';

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    audience: audienceToggle ? audienceToggle.value : 'technical',
                    sources: ['confluence', 'jira', 'internal', 'salesforce']
                })
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const data = await response.json();
            this.displayResults(data);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError(`Search failed: ${error.message}`);
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        }
    }

    displayResults(data) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        this.searchResults = data;

        const confidenceScore = data.metadata?.safety_score || 0.5;
        const confidenceLevel = this.getConfidenceLevel(confidenceScore);
        
        const resultsHTML = `
            <div class="card">
                <div class="results-header">
                    <div class="confidence-badge badge ${confidenceLevel.class}">
                        ${confidenceLevel.icon} ${confidenceLevel.text} Confidence (${Math.round(confidenceScore * 100)}%)
                    </div>
                    <a href="/result/${data.query_hash}" target="_blank" class="btn btn-primary">
                        View Detailed Results →
                    </a>
                </div>
                
                <div class="response-content">
                    ${this.formatResponse(data.response)}
                </div>
                
                <div class="sources-section">
                    <h3>Sources (${data.sources.length})</h3>
                    <div class="sources-grid">
                        ${data.sources.map((source, index) => this.formatSource(source, index + 1)).join('')}
                    </div>
                </div>
                
                <div class="metadata">
                    <small>
                        Model: ${data.metadata?.model_used || 'Unknown'} | 
                        Processing Time: ${data.metadata?.total_processing_time?.toFixed(2) || 'N/A'}s |
                        Query Hash: ${data.query_hash}
                    </small>
                </div>
            </div>
        `;

        resultsContainer.innerHTML = resultsHTML;
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    formatResponse(response) {
        // Convert line breaks to HTML
        return response.replace(/\n/g, '<br>');
    }

    formatSource(source, index) {
        const title = source.title || 'Unknown Document';
        const url = source.url || '#';
        const content = source.content || 'No preview available';
        const author = source.author || 'Unknown';
        const date = source.date || 'Unknown';

        return `
            <div class="source-item">
                <div class="source-header">
                    <span class="source-number">${index}</span>
                    <a href="${url}" target="_blank" class="source-title">${title}</a>
                </div>
                <div class="source-meta">
                    <span>By: ${author}</span>
                    <span>Date: ${date}</span>
                </div>
                <div class="source-preview">${content}</div>
            </div>
        `;
    }

    getConfidenceLevel(score) {
        if (score >= 0.8) {
            return { text: 'High', class: 'badge-success', icon: '✅' };
        } else if (score >= 0.6) {
            return { text: 'Medium', class: 'badge-warning', icon: '⚠️' };
        } else {
            return { text: 'Low', class: 'badge-error', icon: '❌' };
        }
    }

    updateAudienceDisplay() {
        const audienceToggle = document.getElementById('audienceToggle');
        const audienceDisplay = document.getElementById('audienceDisplay');
        
        if (audienceToggle && audienceDisplay) {
            audienceDisplay.textContent = audienceToggle.value === 'clinical' ? 'Clinical' : 'Technical';
        }
    }

    showError(message) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;

        resultsContainer.innerHTML = `
            <div class="card">
                <div class="error-message" style="color: var(--error-color); text-align: center; padding: 2rem;">
                    <strong>Error:</strong> ${message}
                </div>
            </div>
        `;
    }
}

// Initialize the interface when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RAGInterface();
});

// Add some utility functions
window.RAGUtils = {
    // Copy text to clipboard
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            console.log('Copied to clipboard');
        } catch (err) {
            console.error('Failed to copy to clipboard:', err);
        }
    },

    // Format timestamp
    formatTimestamp: (timestamp) => {
        return new Date(timestamp).toLocaleString();
    },

    // Download search results as JSON
    downloadResults: (data, filename = 'search_results.json') => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};