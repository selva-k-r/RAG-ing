/**
 * UI Personalization - Local Storage for User Preferences
 * 
 * Features:
 * - Theme selection (light/dark/auto)
 * - Recent searches tracking
 * - Preferred data sources
 * - Search history
 */

class UIPersonalization {
    constructor() {
        this.storageKey = 'rag_ui_prefs';
        this.historyKey = 'rag_search_history';
        this.maxHistory = 20;
        
        // Load preferences
        this.prefs = this.loadPreferences();
        
        // Apply theme on init
        this.applyTheme();
    }
    
    // Preference Management
    loadPreferences() {
        const stored = localStorage.getItem(this.storageKey);
        return stored ? JSON.parse(stored) : {
            theme: 'light',
            preferredSources: [],
            compactMode: false,
            resultsPerPage: 10
        };
    }
    
    savePreferences() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.prefs));
    }
    
    updatePreference(key, value) {
        this.prefs[key] = value;
        this.savePreferences();
    }
    
    // Theme Management
    setTheme(theme) {
        this.prefs.theme = theme;
        this.savePreferences();
        this.applyTheme();
    }
    
    applyTheme() {
        const theme = this.prefs.theme;
        document.documentElement.setAttribute('data-theme', theme);
        
        if (theme === 'dark') {
            document.body.style.background = '#1a1a1a';
            document.body.style.color = '#e0e0e0';
        } else {
            document.body.style.background = '#ffffff';
            document.body.style.color = '#333';
        }
    }
    
    toggleTheme() {
        const newTheme = this.prefs.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
        return newTheme;
    }
    
    // Search History Management
    loadSearchHistory() {
        const stored = localStorage.getItem(this.historyKey);
        return stored ? JSON.parse(stored) : [];
    }
    
    addToHistory(query, source = null) {
        const history = this.loadSearchHistory();
        
        // Create history entry
        const entry = {
            query: query,
            source: source,
            timestamp: new Date().toISOString()
        };
        
        // Remove duplicates
        const filtered = history.filter(item => item.query !== query);
        
        // Add to beginning
        filtered.unshift(entry);
        
        // Keep only last N entries
        const trimmed = filtered.slice(0, this.maxHistory);
        
        // Save
        localStorage.setItem(this.historyKey, JSON.stringify(trimmed));
    }
    
    clearHistory() {
        localStorage.removeItem(this.historyKey);
    }
    
    getRecentSearches(limit = 5) {
        const history = this.loadSearchHistory();
        return history.slice(0, limit);
    }
    
    // Data Source Preferences
    setPreferredSources(sources) {
        this.prefs.preferredSources = sources;
        this.savePreferences();
    }
    
    addPreferredSource(source) {
        if (!this.prefs.preferredSources.includes(source)) {
            this.prefs.preferredSources.push(source);
            this.savePreferences();
        }
    }
    
    removePreferredSource(source) {
        this.prefs.preferredSources = this.prefs.preferredSources.filter(s => s !== source);
        this.savePreferences();
    }
    
    // UI Utilities
    
    /**
     * Sanitize HTML to prevent XSS attacks
     * Escapes special characters that could be used for HTML injection
     * Note: Ampersand must be escaped first to prevent double-escaping
     * @param {string} str - The string to sanitize
     * @returns {string} - Sanitized string safe for HTML content rendering
     */
    sanitizeHTML(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    renderRecentSearches(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const searches = this.getRecentSearches();
        
        if (searches.length === 0) {
            container.innerHTML = '<div class="no-history">No recent searches</div>';
            return;
        }
        
        let html = '<div class="recent-searches">';
        html += '<div class="recent-header">Recent Searches</div>';
        html += '<ul class="search-list">';
        
        searches.forEach((entry, index) => {
            const date = new Date(entry.timestamp).toLocaleDateString();
            const sanitizedQuery = this.sanitizeHTML(entry.query);
            html += `
                <li class="search-item" data-query-index="${index}">
                    <span class="search-query">${sanitizedQuery}</span>
                    <span class="search-date">${date}</span>
                </li>
            `;
        });
        
        html += '</ul>';
        html += '<button class="clear-history-btn">Clear History</button>';
        html += '</div>';
        
        container.innerHTML = html;
        
        // Add event listeners using event delegation (safer than inline onclick)
        const searchList = container.querySelector('.search-list');
        if (searchList) {
            searchList.addEventListener('click', (e) => {
                const listItem = e.target.closest('.search-item');
                if (listItem) {
                    const queryIndex = parseInt(listItem.dataset.queryIndex, 10);
                    // Re-fetch searches to avoid stale closure data
                    const currentSearches = this.getRecentSearches();
                    // Validate queryIndex is a valid array index
                    if (!isNaN(queryIndex) && queryIndex >= 0 && queryIndex < currentSearches.length) {
                        const queryInput = document.querySelector('input[name=query]');
                        if (queryInput) {
                            // Use the unsanitized original query for the input field
                            queryInput.value = currentSearches[queryIndex].query;
                        }
                    }
                }
            });
        }
        
        const clearBtn = container.querySelector('.clear-history-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearHistory();
                this.renderRecentSearches(containerId);
            });
        }
    }
    
    renderThemeSelector(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const currentTheme = this.prefs.theme;
        
        const html = `
            <div class="theme-selector">
                <button class="theme-btn ${currentTheme === 'light' ? 'active' : ''}" 
                        data-theme="light">
                    ☀️ Light
                </button>
                <button class="theme-btn ${currentTheme === 'dark' ? 'active' : ''}" 
                        data-theme="dark">
                    🌙 Dark
                </button>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Add event listeners using event delegation (safer than inline onclick)
        const themeButtons = container.querySelectorAll('.theme-btn');
        themeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const theme = button.dataset.theme;
                if (theme === 'light' || theme === 'dark') {
                    this.setTheme(theme);
                }
            });
        });
    }
}

// Initialize on page load
let uiPersonalization;
document.addEventListener('DOMContentLoaded', function() {
    uiPersonalization = new UIPersonalization();
    console.log('UI Personalization initialized');
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIPersonalization;
}



