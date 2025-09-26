/**
 * NYC Subway ETA Frontend Application
 * Main JavaScript file for handling user interactions and API calls
 */

class NYCSubwayApp {
    constructor() {
        // Configuration
        this.config = {
            apiBaseUrl: 'http://localhost:3000/api',
            searchDebounceMs: 300,
            refreshIntervalMs: 30000,
            maxSuggestions: 8
        };

        // State
        this.state = {
            currentTab: 'plan',
            selectedFromStation: null,
            selectedToStation: null,
            selectedArrivalsStation: null,
            currentRoute: null,
            currentArrivals: null,
            refreshInterval: null,
            searchTimeouts: new Map()
        };

        // Initialize the application
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.bindEvents();
        this.checkApiStatus();
        this.setupAccessibility();
        console.log('NYC Subway ETA app initialized');
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Tab navigation
        document.getElementById('planTab').addEventListener('click', () => this.switchTab('plan'));
        document.getElementById('arrivalsTab').addEventListener('click', () => this.switchTab('arrivals'));

        // Trip planning form
        document.getElementById('tripForm').addEventListener('submit', (e) => this.handleTripFormSubmit(e));
        document.getElementById('fromStation').addEventListener('input', (e) => this.handleStationSearch(e, 'from'));
        document.getElementById('toStation').addEventListener('input', (e) => this.handleStationSearch(e, 'to'));

        // Arrivals form
        document.getElementById('arrivalsForm').addEventListener('submit', (e) => this.handleArrivalsFormSubmit(e));
        document.getElementById('stationSelect').addEventListener('input', (e) => this.handleStationSearch(e, 'arrivals'));

        // Keyboard navigation for suggestions
        document.addEventListener('keydown', (e) => this.handleKeyboardNavigation(e));
        document.addEventListener('click', (e) => this.handleDocumentClick(e));

        // Window events
        window.addEventListener('resize', () => this.handleResize());
        window.addEventListener('beforeunload', () => this.cleanup());
    }

    /**
     * Set up accessibility features
     */
    setupAccessibility() {
        // Announce route changes to screen readers
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.style.cssText = 'position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden;';
        document.body.appendChild(announcer);
        this.announcer = announcer;
    }

    /**
     * Switch between tabs
     */
    switchTab(tabName) {
        // Update state
        this.state.currentTab = tabName;

        // Update UI
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

        document.getElementById(`${tabName}Tab`).classList.add('active');
        document.getElementById(`${tabName}Panel`).classList.add('active');

        // Update tab attributes for accessibility
        document.querySelectorAll('.tab-button').forEach(btn => btn.setAttribute('aria-selected', 'false'));
        document.getElementById(`${tabName}Tab`).setAttribute('aria-selected', 'true');

        // Focus management
        document.getElementById(`${tabName}Panel`).setAttribute('tabindex', '-1');
        document.getElementById(`${tabName}Panel`).focus();
        document.getElementById(`${tabName}Panel`).removeAttribute('tabindex');

        // Clear refresh interval when switching away from arrivals
        if (tabName !== 'arrivals' && this.state.refreshInterval) {
            clearInterval(this.state.refreshInterval);
            this.state.refreshInterval = null;
        }
    }

    /**
     * Handle station search with debouncing
     */
    async handleStationSearch(event, type) {
        const input = event.target;
        const query = input.value.trim();

        // Clear previous timeout
        if (this.state.searchTimeouts.has(type)) {
            clearTimeout(this.state.searchTimeouts.get(type));
        }

        const suggestionId = type === 'from' ? 'fromSuggestions' :
                           type === 'to' ? 'toSuggestions' : 'stationSuggestions';
        const suggestionsEl = document.getElementById(suggestionId);

        if (query.length < 2) {
            this.hideSuggestions(suggestionId);
            return;
        }

        // Set up debounced search
        const timeoutId = setTimeout(async () => {
            try {
                await this.searchStations(query, suggestionId, type);
            } catch (error) {
                console.error('Station search error:', error);
                this.showToast('Failed to search stations', 'error');
            }
        }, this.config.searchDebounceMs);

        this.state.searchTimeouts.set(type, timeoutId);
    }

    /**
     * Search for stations via API
     */
    async searchStations(query, suggestionId, type) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/stops?q=${encodeURIComponent(query)}`);

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status}`);
            }

            const data = await response.json();
            this.displaySuggestions(data.stops, suggestionId, type);
        } catch (error) {
            console.error('API Error:', error);
            this.hideSuggestions(suggestionId);
        }
    }

    /**
     * Display station suggestions
     */
    displaySuggestions(stations, suggestionId, type) {
        const suggestionsEl = document.getElementById(suggestionId);

        if (!stations || stations.length === 0) {
            this.hideSuggestions(suggestionId);
            return;
        }

        const limitedStations = stations.slice(0, this.config.maxSuggestions);

        suggestionsEl.innerHTML = limitedStations.map((station, index) => `
            <div class="suggestion-item"
                 data-station-id="${station.id}"
                 data-station-name="${station.name}"
                 data-type="${type}"
                 data-index="${index}"
                 role="option"
                 aria-selected="false">
                <div class="suggestion-name">${this.escapeHtml(station.name)}</div>
                <div class="suggestion-lines">
                    ${station.lines.map(line =>
                        `<span class="line-badge line-${line.toLowerCase()}">${line}</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');

        // Add click handlers
        suggestionsEl.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', (e) => this.selectStation(e));
        });

        this.showSuggestions(suggestionId);
    }

    /**
     * Select a station from suggestions
     */
    selectStation(event) {
        const item = event.currentTarget;
        const stationId = item.dataset.stationId;
        const stationName = item.dataset.stationName;
        const type = item.dataset.type;

        // Update input value
        const inputId = type === 'from' ? 'fromStation' :
                       type === 'to' ? 'toStation' : 'stationSelect';
        const input = document.getElementById(inputId);
        input.value = stationName;

        // Store selection in state
        const stationData = { id: stationId, name: stationName };
        if (type === 'from') {
            this.state.selectedFromStation = stationData;
        } else if (type === 'to') {
            this.state.selectedToStation = stationData;
        } else {
            this.state.selectedArrivalsStation = stationData;
        }

        // Hide suggestions
        const suggestionId = type === 'from' ? 'fromSuggestions' :
                           type === 'to' ? 'toSuggestions' : 'stationSuggestions';
        this.hideSuggestions(suggestionId);

        // Focus next input or button
        if (type === 'from') {
            document.getElementById('toStation').focus();
        }

        this.announceToScreenReader(`Selected ${stationName}`);
    }

    /**
     * Show suggestions dropdown
     */
    showSuggestions(suggestionId) {
        const suggestionsEl = document.getElementById(suggestionId);
        suggestionsEl.classList.add('show');
        suggestionsEl.setAttribute('aria-expanded', 'true');
    }

    /**
     * Hide suggestions dropdown
     */
    hideSuggestions(suggestionId) {
        const suggestionsEl = document.getElementById(suggestionId);
        suggestionsEl.classList.remove('show');
        suggestionsEl.setAttribute('aria-expanded', 'false');
    }

    /**
     * Handle trip form submission
     */
    async handleTripFormSubmit(event) {
        event.preventDefault();

        if (!this.state.selectedFromStation || !this.state.selectedToStation) {
            this.showToast('Please select both origin and destination stations', 'warning');
            return;
        }

        if (this.state.selectedFromStation.id === this.state.selectedToStation.id) {
            this.showToast('Origin and destination cannot be the same', 'warning');
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch(
                `${this.config.apiBaseUrl}/route?from=${this.state.selectedFromStation.id}&to=${this.state.selectedToStation.id}`
            );

            if (!response.ok) {
                throw new Error(`Failed to plan route: ${response.status}`);
            }

            const routeData = await response.json();
            this.displayRoute(routeData);
            this.announceToScreenReader(`Route found with ${routeData.legs.length} legs and ${routeData.transfers} transfers`);
        } catch (error) {
            console.error('Route planning error:', error);
            this.showToast('Failed to plan route. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Handle arrivals form submission
     */
    async handleArrivalsFormSubmit(event) {
        event.preventDefault();

        if (!this.state.selectedArrivalsStation) {
            this.showToast('Please select a station', 'warning');
            return;
        }

        await this.fetchArrivals();
    }

    /**
     * Fetch arrivals data
     */
    async fetchArrivals(isRefresh = false) {
        if (!isRefresh) {
            this.showLoading(true);
        }

        try {
            const direction = document.getElementById('directionSelect').value;
            let url = `${this.config.apiBaseUrl}/arrivals?stop_id=${this.state.selectedArrivalsStation.id}`;

            if (direction) {
                url += `&direction=${direction}`;
            }

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Failed to fetch arrivals: ${response.status}`);
            }

            const arrivalsData = await response.json();
            this.displayArrivals(arrivalsData);

            if (!isRefresh) {
                this.setupArrivalsRefresh();
            }

            if (!isRefresh) {
                this.announceToScreenReader(`Found ${arrivalsData.arrivals.length} upcoming arrivals`);
            }
        } catch (error) {
            console.error('Arrivals fetch error:', error);
            this.showToast('Failed to fetch arrivals. Please try again.', 'error');
        } finally {
            if (!isRefresh) {
                this.showLoading(false);
            }
        }
    }

    /**
     * Display route results
     */
    displayRoute(routeData) {
        this.state.currentRoute = routeData;
        const resultsEl = document.getElementById('routeResults');
        const containerEl = document.getElementById('routeContainer');

        if (!routeData.legs || routeData.legs.length === 0) {
            containerEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🚫</div>
                    <div class="empty-state-text">No route found</div>
                    <div class="empty-state-subtext">Try different stations or check service alerts</div>
                </div>
            `;
            resultsEl.style.display = 'block';
            return;
        }

        const legsHtml = routeData.legs.map((leg, index) => {
            const isTransfer = leg.transfer && index > 0;
            const routeColor = this.getRouteColor(leg.route_id);
            const totalTime = leg.board_in_s + leg.run_s;
            const totalMinutes = Math.ceil(totalTime / 60);

            return `
                <div class="route-leg ${isTransfer ? 'transfer' : ''}">
                    <div class="leg-icon" style="background-color: ${routeColor}">
                        ${leg.route_id}
                    </div>
                    <div class="leg-details">
                        <div class="leg-route">
                            ${leg.route_id} ${isTransfer ? '(Transfer)' : 'Train'}
                        </div>
                        <div class="leg-stations">
                            ${this.getStationName(leg.from_stop_id)} → ${this.getStationName(leg.to_stop_id)}
                        </div>
                        <div class="leg-timing">
                            Wait: ${Math.ceil(leg.board_in_s / 60)}min • Travel: ${Math.ceil(leg.run_s / 60)}min • Total: ${totalMinutes}min
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        const summaryHtml = `
            <div class="route-summary">
                <div class="summary-item">
                    <div class="summary-value">${Math.ceil(routeData.total_eta_s / 60)}</div>
                    <div class="summary-label">Total Minutes</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${routeData.transfers}</div>
                    <div class="summary-label">Transfers</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${routeData.legs.length}</div>
                    <div class="summary-label">Legs</div>
                </div>
            </div>
        `;

        containerEl.innerHTML = legsHtml + summaryHtml;
        resultsEl.style.display = 'block';

        // Scroll to results
        resultsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /**
     * Display arrivals results
     */
    displayArrivals(arrivalsData) {
        this.state.currentArrivals = arrivalsData;
        const resultsEl = document.getElementById('arrivalsResults');
        const containerEl = document.getElementById('arrivalsContainer');
        const lastUpdatedEl = document.getElementById('lastUpdated');

        if (!arrivalsData.arrivals || arrivalsData.arrivals.length === 0) {
            containerEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⏰</div>
                    <div class="empty-state-text">No arrivals found</div>
                    <div class="empty-state-subtext">Check back in a few minutes or try a different direction</div>
                </div>
            `;
            resultsEl.style.display = 'block';
            return;
        }

        // Sort arrivals by ETA
        const sortedArrivals = [...arrivalsData.arrivals].sort((a, b) => a.eta_s - b.eta_s);

        const arrivalsHtml = sortedArrivals.map(arrival => {
            const routeColor = this.getRouteColor(arrival.route_id);
            const minutes = Math.ceil(arrival.eta_s / 60);
            const etaClass = minutes <= 1 ? 'now' : minutes <= 3 ? 'soon' : '';
            const timeText = minutes <= 1 ? 'Now' : `${minutes}min`;

            return `
                <div class="arrival-item">
                    <div class="arrival-route" style="background-color: ${routeColor}">
                        ${arrival.route_id}
                    </div>
                    <div class="arrival-info">
                        <div class="arrival-headsign">${this.escapeHtml(arrival.headsign)}</div>
                        <div class="arrival-direction">Arriving in</div>
                    </div>
                    <div class="arrival-time">
                        <div class="arrival-eta ${etaClass}">${timeText}</div>
                    </div>
                </div>
            `;
        }).join('');

        containerEl.innerHTML = arrivalsHtml;

        // Update timestamp
        const lastUpdate = new Date(arrivalsData.as_of_ts * 1000);
        lastUpdatedEl.textContent = `Last updated: ${lastUpdate.toLocaleTimeString()}`;

        resultsEl.style.display = 'block';

        // Scroll to results on first load
        if (!this.state.refreshInterval) {
            resultsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * Set up automatic refresh for arrivals
     */
    setupArrivalsRefresh() {
        // Clear existing interval
        if (this.state.refreshInterval) {
            clearInterval(this.state.refreshInterval);
        }

        // Set up new interval
        this.state.refreshInterval = setInterval(() => {
            if (this.state.currentTab === 'arrivals' && this.state.selectedArrivalsStation) {
                this.fetchArrivals(true);
            }
        }, this.config.refreshIntervalMs);
    }

    /**
     * Refresh arrivals manually
     */
    async refreshArrivals() {
        if (!this.state.selectedArrivalsStation) {
            return;
        }

        const refreshBtn = document.getElementById('refreshArrivals');
        const originalText = refreshBtn.innerHTML;

        refreshBtn.innerHTML = '<span class="refresh-icon">🔄</span> Refreshing...';
        refreshBtn.disabled = true;

        try {
            await this.fetchArrivals(true);
            this.showToast('Arrivals updated', 'success');
        } catch (error) {
            this.showToast('Failed to refresh arrivals', 'error');
        } finally {
            refreshBtn.innerHTML = originalText;
            refreshBtn.disabled = false;
        }
    }

    /**
     * Swap origin and destination stations
     */
    swapStations() {
        const fromInput = document.getElementById('fromStation');
        const toInput = document.getElementById('toStation');

        // Swap input values
        const tempValue = fromInput.value;
        fromInput.value = toInput.value;
        toInput.value = tempValue;

        // Swap state
        const tempStation = this.state.selectedFromStation;
        this.state.selectedFromStation = this.state.selectedToStation;
        this.state.selectedToStation = tempStation;

        // Announce to screen reader
        this.announceToScreenReader('Origin and destination stations swapped');

        // Focus the from input
        fromInput.focus();
    }

    /**
     * Clear route results
     */
    clearRoute() {
        document.getElementById('routeResults').style.display = 'none';
        document.getElementById('fromStation').value = '';
        document.getElementById('toStation').value = '';
        this.state.selectedFromStation = null;
        this.state.selectedToStation = null;
        this.state.currentRoute = null;

        // Focus the from input
        document.getElementById('fromStation').focus();
        this.announceToScreenReader('Route cleared');
    }

    /**
     * Handle keyboard navigation for suggestions
     */
    handleKeyboardNavigation(event) {
        const activeDropdown = document.querySelector('.suggestions-dropdown.show');
        if (!activeDropdown) return;

        const items = activeDropdown.querySelectorAll('.suggestion-item');
        const currentSelected = activeDropdown.querySelector('.suggestion-item.selected');
        let selectedIndex = currentSelected ? parseInt(currentSelected.dataset.index) : -1;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.updateSelectedSuggestion(activeDropdown, selectedIndex);
                break;

            case 'ArrowUp':
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                this.updateSelectedSuggestion(activeDropdown, selectedIndex);
                break;

            case 'Enter':
                if (currentSelected) {
                    event.preventDefault();
                    currentSelected.click();
                }
                break;

            case 'Escape':
                this.hideSuggestions(activeDropdown.id);
                break;
        }
    }

    /**
     * Update selected suggestion for keyboard navigation
     */
    updateSelectedSuggestion(dropdown, selectedIndex) {
        const items = dropdown.querySelectorAll('.suggestion-item');

        // Remove previous selection
        items.forEach(item => {
            item.classList.remove('selected');
            item.setAttribute('aria-selected', 'false');
        });

        // Add new selection
        if (selectedIndex >= 0 && selectedIndex < items.length) {
            const selectedItem = items[selectedIndex];
            selectedItem.classList.add('selected');
            selectedItem.setAttribute('aria-selected', 'true');
            selectedItem.scrollIntoView({ block: 'nearest' });
        }
    }

    /**
     * Handle document clicks to close dropdowns
     */
    handleDocumentClick(event) {
        if (!event.target.closest('.station-input-wrapper')) {
            document.querySelectorAll('.suggestions-dropdown.show').forEach(dropdown => {
                this.hideSuggestions(dropdown.id);
            });
        }
    }

    /**
     * Check API status and update status indicator
     */
    async checkApiStatus() {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        try {
            const response = await fetch(`${this.config.apiBaseUrl}/health`);
            const healthData = await response.json();

            if (response.ok && healthData.status === 'healthy') {
                statusDot.className = 'status-dot';
                statusText.textContent = 'Online';

                if (healthData.feed_age_seconds > 300) { // 5 minutes
                    statusDot.classList.add('warning');
                    statusText.textContent = 'Delayed Data';
                }
            } else {
                throw new Error('API unhealthy');
            }
        } catch (error) {
            statusDot.className = 'status-dot error';
            statusText.textContent = 'Offline';
            console.error('API health check failed:', error);
        }

        // Schedule next check
        setTimeout(() => this.checkApiStatus(), 30000);
    }

    /**
     * Show/hide loading overlay
     */
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        overlay.style.display = show ? 'flex' : 'none';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    /**
     * Get route color for display
     */
    getRouteColor(routeId) {
        const colors = {
            '4': '#00933C', '5': '#00933C', '6': '#00933C',
            '7': '#B933AD',
            'A': '#0039A6', 'C': '#0039A6', 'E': '#0039A6',
            'B': '#FF6319', 'D': '#FF6319', 'F': '#FF6319', 'M': '#FF6319',
            'G': '#6CBE45',
            'J': '#996633', 'Z': '#996633',
            'L': '#A7A9AC',
            'N': '#FCCC0A', 'Q': '#FCCC0A', 'R': '#FCCC0A', 'W': '#FCCC0A',
            'S': '#808183'
        };
        return colors[routeId] || '#6C757D';
    }

    /**
     * Get station name from ID (fallback if not stored)
     */
    getStationName(stationId) {
        // Try to get from stored selections
        if (this.state.selectedFromStation && this.state.selectedFromStation.id === stationId) {
            return this.state.selectedFromStation.name;
        }
        if (this.state.selectedToStation && this.state.selectedToStation.id === stationId) {
            return this.state.selectedToStation.name;
        }
        return `Station ${stationId}`;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Announce messages to screen readers
     */
    announceToScreenReader(message) {
        if (this.announcer) {
            this.announcer.textContent = message;
        }
    }

    /**
     * Handle window resize
     */
    handleResize() {
        // Close any open dropdowns on resize
        document.querySelectorAll('.suggestions-dropdown.show').forEach(dropdown => {
            this.hideSuggestions(dropdown.id);
        });
    }

    /**
     * Show about modal
     */
    showAbout() {
        document.getElementById('aboutModal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    /**
     * Hide about modal
     */
    hideAbout() {
        document.getElementById('aboutModal').style.display = 'none';
        document.body.style.overflow = '';
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.state.refreshInterval) {
            clearInterval(this.state.refreshInterval);
        }

        this.state.searchTimeouts.forEach(timeout => {
            clearTimeout(timeout);
        });
    }
}

// Global functions for HTML event handlers
function switchTab(tabName) {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.switchTab(tabName);
    }
}

function swapStations() {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.swapStations();
    }
}

function clearRoute() {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.clearRoute();
    }
}

function refreshArrivals() {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.refreshArrivals();
    }
}

function showAbout() {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.showAbout();
    }
}

function hideAbout() {
    if (window.nycSubwayApp) {
        window.nycSubwayApp.hideAbout();
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.nycSubwayApp = new NYCSubwayApp();
});