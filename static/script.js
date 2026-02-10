/**
 * LLM Memory Management System - Frontend JavaScript
 */

// API Base URL
const API_BASE = '/api';

// State
let currentUser = null;
let currentSession = null;
let allEntities = [];
let currentSettings = { model: 'gemini', selected_model: 'gemini-2.0-flash', api_keys: { gemini: [], openai: [], openrouter: [] } };
let availableModels = {};

// DOM Elements
const elements = {
    userList: document.getElementById('userList'),
    newUsername: document.getElementById('newUsername'),
    createUserBtn: document.getElementById('createUserBtn'),
    chatContainer: document.getElementById('chatContainer'),
    messageInput: document.getElementById('messageInput'),
    chatModelSelect: document.getElementById('chatModelSelect'),
    sendBtn: document.getElementById('sendBtn'),
    sessionInfo: document.getElementById('sessionInfo'),
    activeUser: document.getElementById('activeUser'),
    mongoStatus: document.getElementById('mongoStatus'),
    memoryList: document.getElementById('memoryList'),
    entityList: document.getElementById('entityList'),
    relationList: document.getElementById('relationList'),
    nosqlList: document.getElementById('nosqlList'),
    nosqlStatusBadge: document.getElementById('nosqlStatusBadge'),
    refreshNoSQLBtn: document.getElementById('refreshNoSQLBtn'),
    memoryTypeFilter: document.getElementById('memoryTypeFilter'),
    memorySearch: document.getElementById('memorySearch'),
    searchMemoryBtn: document.getElementById('searchMemoryBtn'),
    toast: document.getElementById('toast'),
    // Settings Modal
    settingsBtn: document.getElementById('settingsBtn'),
    settingsModal: document.getElementById('settingsModal'),
    closeSettingsBtn: document.getElementById('closeSettingsBtn'),
    cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    modelSelect: document.getElementById('modelSelect'),
    apiKeyList: document.getElementById('apiKeyList'),
    newApiKeyInput: document.getElementById('newApiKeyInput'),
    newKeyLabelInput: document.getElementById('newKeyLabelInput'),
    addKeyBtn: document.getElementById('addKeyBtn'),
    currentModelStatus: document.getElementById('currentModelStatus')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
});

async function initializeApp() {
    await checkHealth();
    await loadUsers();
    await loadSettings();
    await loadAvailableModels();
}

function setupEventListeners() {
    // User creation
    elements.createUserBtn.addEventListener('click', createUser);
    elements.newUsername.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createUser();
    });

    // Message sending
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Memory filter
    elements.memoryTypeFilter.addEventListener('change', () => {
        if (currentUser) loadMemories();
    });

    // Memory search
    elements.searchMemoryBtn.addEventListener('click', searchMemories);
    elements.memorySearch.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMemories();
    });

    // NoSQL refresh
    if (elements.refreshNoSQLBtn) {
        elements.refreshNoSQLBtn.addEventListener('click', loadNoSQLData);
    }

    // Settings modal
    elements.settingsBtn.addEventListener('click', openSettingsModal);
    elements.closeSettingsBtn.addEventListener('click', closeSettingsModal);
    elements.cancelSettingsBtn.addEventListener('click', closeSettingsModal);
    elements.saveSettingsBtn.addEventListener('click', saveSettings);

    // Add Key Button
    elements.addKeyBtn.addEventListener('click', addApiKey);

    // Model Select Change in settings modal(update key list)
    elements.modelSelect.addEventListener('change', () => {
        renderSettingsKeys();
        const prov = elements.modelSelect.value;
        const provNames = { gemini: 'Gemini', openai: 'OpenAI', openrouter: 'OpenRouter' };
        elements.newApiKeyInput.placeholder = `Paste new ${provNames[prov] || prov} API key...`;
    });

    // Inline model selector change (chat bar)
    elements.chatModelSelect.addEventListener('change', async () => {
        const modelId = elements.chatModelSelect.value;
        try {
            await apiRequest('/settings/model', 'POST', { model: modelId });
            currentSettings.selected_model = modelId;
            showToast(`Model: ${modelId}`, 'success');
        } catch (err) {
            showToast('Failed to switch model', 'error');
        }
    });

    elements.settingsModal.addEventListener('click', (e) => {
        if (e.target === elements.settingsModal) closeSettingsModal();
    });
}

// ==========================================
// API Functions
// ==========================================

async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        elements.mongoStatus.textContent = data.mongodb === 'connected' ? 'Connected' : 'Disconnected';
        elements.mongoStatus.className = 'stat-value ' +
            (data.mongodb === 'connected' ? 'status-connected' : 'status-disconnected');
    } catch (error) {
        elements.mongoStatus.textContent = 'Error';
        elements.mongoStatus.className = 'stat-value status-disconnected';
    }
}

// ==========================================
// User Functions
// ==========================================

async function loadUsers() {
    try {
        const users = await apiRequest('/users');
        renderUsers(users);
    } catch (error) {
        showToast('Failed to load users', 'error');
    }
}

function renderUsers(users) {
    if (users.length === 0) {
        elements.userList.innerHTML = `
            <li class="empty-state" style="padding: 20px; text-align: center;">
                <span style="font-size: 24px;">👤</span>
                <p style="margin-top: 8px; color: var(--text-muted); font-size: 13px;">No users yet</p>
            </li>
        `;
        return;
    }

    elements.userList.innerHTML = users.map(user => `
        <li class="user-item ${currentUser?.user_id === user.user_id ? 'active' : ''}" 
            data-user-id="${user.user_id}">
            <div class="user-content" onclick="selectUser('${user.user_id}')">
                <div class="user-avatar">${user.username.charAt(0).toUpperCase()}</div>
                <span class="user-name">${user.username}</span>
            </div>
            <button class="user-delete-btn" onclick="event.stopPropagation(); deleteUser('${user.user_id}', '${user.username}')" title="Delete user">
                ✕
            </button>
        </li>
    `).join('');
}

async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?\n\nThis will delete all their sessions, conversations, and memories.`)) {
        return;
    }

    try {
        await apiRequest(`/users/${userId}`, 'DELETE');
        showToast(`User "${username}" deleted`, 'success');

        // If we deleted the current user, clear the state
        if (currentUser?.user_id === userId) {
            currentUser = null;
            currentSession = null;
            elements.activeUser.textContent = 'None';
            elements.sessionInfo.textContent = 'No active session';
            elements.messageInput.disabled = true;
            elements.sendBtn.disabled = true;
            elements.chatContainer.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">👋</div>
                    <h3>Welcome to Memory LLM</h3>
                    <p>Select or create a user to start a conversation.</p>
                </div>
            `;
        }

        await loadUsers();
    } catch (error) {
        showToast(`Failed to delete user: ${error.message}`, 'error');
    }
}

async function createUser() {
    const username = elements.newUsername.value.trim();

    if (!username) {
        showToast('Please enter a username', 'error');
        return;
    }

    try {
        const user = await apiRequest('/users', 'POST', { username });
        elements.newUsername.value = '';
        showToast(`User "${username}" created!`, 'success');
        await loadUsers();
        selectUser(user.user_id);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function selectUser(userId) {
    try {
        const user = await apiRequest(`/users/${userId}`);
        currentUser = user;

        // Update UI
        elements.activeUser.textContent = user.username;
        elements.messageInput.disabled = false;
        elements.sendBtn.disabled = false;

        // Refresh user list to show active state
        await loadUsers();

        // Get or create session
        const session = await apiRequest(`/sessions/user/${userId}/active`);
        currentSession = session;
        elements.sessionInfo.textContent = `Session: ${session.session_id.substring(0, 8)}...`;

        // Load data
        await loadConversation();
        await loadMemories();
        await loadEntityRelations();
        await loadNoSQLData();

        showToast(`Switched to ${user.username}`, 'success');
    } catch (error) {
        showToast('Failed to select user', 'error');
    }
}

// ==========================================
// Conversation Functions
// ==========================================

async function loadConversation() {
    if (!currentSession) return;

    try {
        const messages = await apiRequest(`/conversations/session/${currentSession.session_id}`);
        renderMessages(messages);
    } catch (error) {
        console.error('Failed to load conversation:', error);
    }
}

function renderMessages(messages) {
    if (messages.length === 0) {
        elements.chatContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">💬</div>
                <h3>Start a conversation</h3>
                <p>Type a message to begin. Your memories will be automatically extracted and stored!</p>
            </div>
        `;
        return;
    }

    elements.chatContainer.innerHTML = messages.map(msg => {
        const content = msg.role === 'assistant' ? renderMarkdown(msg.message_text) : escapeHtml(msg.message_text);
        return `
        <div class="message ${msg.role}">
            <div class="message-text md-content">${content}</div>
            <div class="message-meta">${formatTime(msg.timestamp)}</div>
        </div>
    `;
    }).join('');

    // Scroll to bottom
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

async function sendMessage() {
    const text = elements.messageInput.value.trim();

    if (!text || !currentUser || !currentSession) return;

    elements.messageInput.value = '';
    elements.sendBtn.disabled = true;
    elements.messageInput.disabled = true;

    // Show loading indicator
    const loadingId = showLoadingMessage();

    // Start periodic refresh of memories while waiting for response
    const refreshInterval = setInterval(async () => {
        await loadMemories();
        await loadEntityRelations();
    }, 2000); // Refresh every 2 seconds

    try {
        // Send user message - backend will process NLP and generate LLM response
        // This might take a while due to OpenAI processing
        const userMessage = await apiRequest('/conversations', 'POST', {
            user_id: currentUser.user_id,
            session_id: currentSession.session_id,
            role: 'user',
            message_text: text
        });

        // Remove loading indicator
        removeLoadingMessage(loadingId);

        // Reload conversation to get both user message and LLM response
        await loadConversation();

        // Final refresh of memory panel
        await loadMemories();
        await loadEntityRelations();

    } catch (error) {
        removeLoadingMessage(loadingId);

        // Even if the request fails/times out, the backend might have processed it
        // So refresh the conversation and memories anyway
        try {
            await loadConversation();
            await loadMemories();
            await loadEntityRelations();
        } catch (refreshError) {
            console.error('Refresh error:', refreshError);
        }

        showToast('Message sent but response may be delayed', 'info');
        console.error('Send message error:', error);
    } finally {
        // Stop the periodic refresh
        clearInterval(refreshInterval);

        elements.sendBtn.disabled = false;
        elements.messageInput.disabled = false;
        elements.messageInput.focus();
    }
}

function showLoadingMessage() {
    const loadingId = 'loading-' + Date.now();
    const loadingEl = document.createElement('div');
    loadingEl.id = loadingId;
    loadingEl.className = 'message assistant';
    loadingEl.innerHTML = `
        <div class="message-text">
            <span class="typing-indicator">
                <span></span><span></span><span></span>
            </span>
        </div>
    `;

    elements.chatContainer.appendChild(loadingEl);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

    return loadingId;
}

function removeLoadingMessage(loadingId) {
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) loadingEl.remove();
}

function appendMessage(msg) {
    // Remove welcome message if present
    const welcome = elements.chatContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const content = msg.role === 'assistant' ? renderMarkdown(msg.message_text) : escapeHtml(msg.message_text);
    const messageEl = document.createElement('div');
    messageEl.className = `message ${msg.role}`;
    messageEl.innerHTML = `
        <div class="message-text md-content">${content}</div>
        <div class="message-meta">${formatTime(msg.timestamp)}</div>
    `;

    elements.chatContainer.appendChild(messageEl);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}


// ==========================================
// Memory Functions
// ==========================================

async function loadMemories() {
    if (!currentUser) return;

    try {
        const memoryType = elements.memoryTypeFilter.value || null;
        let endpoint = `/memory/user/${currentUser.user_id}`;
        if (memoryType) {
            endpoint += `?memory_type=${memoryType}`;
        }

        const memories = await apiRequest(endpoint);
        renderMemories(memories);
    } catch (error) {
        console.error('Failed to load memories:', error);
    }
}

function renderMemories(memories) {
    if (memories.length === 0) {
        elements.memoryList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <p>No memories found.</p>
            </div>
        `;
        return;
    }

    elements.memoryList.innerHTML = memories.map(mem => `
        <div class="memory-item" data-type="${mem.memory_type}">
            <span class="memory-type ${mem.memory_type}">${mem.memory_type}</span>
            <div class="memory-content">${escapeHtml(mem.content)}</div>
            <div class="memory-meta">
                <span>${formatDate(mem.created_at)}</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${mem.confidence_score * 100}%"></div>
                </div>
            </div>
        </div>
    `).join('');
}

async function searchMemories() {
    const query = elements.memorySearch.value.trim();

    if (!query || !currentUser) return;

    try {
        const results = await apiRequest('/memory/search', 'POST', {
            user_id: currentUser.user_id,
            query: query,
            limit: 20
        });

        renderMemories(results);
        showToast(`Found ${results.length} memories`, 'success');
    } catch (error) {
        showToast('Search failed', 'error');
    }
}

async function loadEntityRelations() {
    if (!currentUser) return;

    try {
        const relations = await apiRequest(`/memory/relations/${currentUser.user_id}`);
        console.debug('[UI] Loaded relations from API:', relations);
        renderRelations(relations);

        // Extract unique entities
        const entities = new Set();
        relations.forEach(rel => {
            entities.add(rel.entity_1);
            entities.add(rel.entity_2);
        });

        // If no relations found, fall back to requesting aggregated entities from the API
        if (entities.size === 0) {
            try {
                const apiEntities = await apiRequest(`/memory/entities/${currentUser.user_id}`);
                if (apiEntities && apiEntities.length > 0) {
                    renderEntities(apiEntities);
                    return;
                }

                // Final fallback: extract from memories client-side
                const memories = await apiRequest(`/memory/user/${currentUser.user_id}`);
                const fallbackEntities = extractEntitiesFromMemories(memories);
                renderEntities(fallbackEntities);
                return;
            } catch (memErr) {
                console.error('Failed to load fallback entities:', memErr);
            }
        }

        renderEntities(Array.from(entities));
    } catch (error) {
        console.error('Failed to load relations:', error);
    }
}

// Helper: simple heuristic to extract entity-like tokens from memory contents
function extractEntitiesFromMemories(memories) {
    const entities = new Set();
    const tokenRegex = /\b[A-Z][a-zA-Z0-9.+#-]{2,}\b/g; // capitalized tokens like "React", "Docker", "Python"

    memories.forEach(mem => {
        // Check memory content for capitalized tokens and tech-like tokens
        const text = mem.content || '';
        let match;
        while ((match = tokenRegex.exec(text)) !== null) {
            entities.add(match[0]);
        }

        // Also pick up common lowercase tech tokens (python, docker etc.)
        const lowerWords = text.toLowerCase().split(/[^a-z0-9+#+-]+/);
        const knownTechs = ['python', 'javascript', 'docker', 'kubernetes', 'react', 'django', 'flask', 'redis', 'postgresql', 'mysql', 'mongodb', 'aws', 'fastapi', 'tailwind', 'node', 'express', 'scikit', 'pandas', 'numpy', 'typescript'];
        for (const w of lowerWords) {
            if (knownTechs.includes(w)) entities.add(w[0].toUpperCase() + w.slice(1));
        }
    });

    return Array.from(entities).sort();
}

function renderEntities(entities) {
    if (entities.length === 0) {
        elements.entityList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🏷️</span>
                <p>No entities extracted yet.</p>
            </div>
        `;
        return;
    }

    elements.entityList.innerHTML = entities.map(entity => `
        <span class="entity-item">
            ${escapeHtml(entity)}
        </span>
    `).join('');
}

function formatRelationType(type) {
    if (!type) return '';
    // Show a more natural label in the UI
    const typeMap = {
        'similar_to': 'related to',
        'associated_with': 'associated with',
        'likes': 'likes',
        'knows': 'knows',
        'uses': 'uses',
        'prefers': 'prefers',
        'has': 'has',
        'lives_in': 'lives in',
        'works_with': 'works with',
        'related_to': 'related to',
        'depends_on': 'depends on',
        'overrides': 'overrides',
        'opposite_of': 'opposite of',
        'part_of': 'part of'
    };
    return typeMap[type] || type.replace(/_/g, ' ');
}

function renderRelations(relations) {
    if (relations.length === 0) {
        elements.relationList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔗</span>
                <p>No relationships found.</p>
            </div>
        `;
        return;
    }

    elements.relationList.innerHTML = relations.map(rel => `
        <div class="relation-item">
            <span class="relation-entity">${escapeHtml(rel.entity_1)}</span>
            <span class="relation-type">${formatRelationType(rel.relation_type)}</span>
            <span class="relation-entity">${escapeHtml(rel.entity_2)}</span>
        </div>
    `).join('');
}

// ==========================================
// NoSQL Functions
// ==========================================

async function loadNoSQLData() {
    if (!currentUser) return;

    try {
        // Get NoSQL status first
        const statusResponse = await apiRequest('/memory/nosql/status');

        if (elements.nosqlStatusBadge) {
            if (statusResponse.connected) {
                elements.nosqlStatusBadge.textContent = 'Connected';
                elements.nosqlStatusBadge.className = 'nosql-status status-connected';
            } else {
                elements.nosqlStatusBadge.textContent = 'Disconnected';
                elements.nosqlStatusBadge.className = 'nosql-status status-disconnected';
            }
        }

        // Get user's NoSQL data
        const data = await apiRequest(`/memory/nosql/user/${currentUser.user_id}/all`);
        renderNoSQLDocuments(data);
    } catch (error) {
        console.error('Failed to load NoSQL data:', error);
        if (elements.nosqlStatusBadge) {
            elements.nosqlStatusBadge.textContent = 'Error';
            elements.nosqlStatusBadge.className = 'nosql-status status-disconnected';
        }
    }
}

function renderNoSQLDocuments(data) {
    if (!elements.nosqlList) return;

    if (!data.connected) {
        elements.nosqlList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔌</span>
                <p>MongoDB is not connected. Start MongoDB to see NoSQL data.</p>
            </div>
        `;
        return;
    }

    if (!data.nlp_logs || data.nlp_logs.length === 0) {
        elements.nosqlList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📄</span>
                <p>No NLP processing logs yet. Send messages to generate NoSQL documents.</p>
            </div>
        `;
        return;
    }

    elements.nosqlList.innerHTML = data.nlp_logs.map(doc => `
        <div class="nosql-document">
            <div class="nosql-doc-header">
                <span class="nosql-doc-id">_id: ${doc._id.substring(0, 12)}...</span>
                <span class="nosql-doc-time">${doc.created_at ? formatTime(doc.created_at) : 'N/A'}</span>
            </div>
            <div class="nosql-doc-content">
                <pre>${escapeHtml(JSON.stringify(doc, null, 2).substring(0, 300))}${JSON.stringify(doc).length > 300 ? '...' : ''}</pre>
            </div>
        </div>
    `).join('');
}

// ==========================================
// UI Functions
// ==========================================

function switchTab(tabId) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabId}-tab`);
    });

    // Load data specific to tab
    if (tabId === 'nosql') {
        loadNoSQLData();
    }
}

function showToast(message, type = 'info') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type} show`;

    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 3000);
}

// ==========================================
// Utility Functions
// ==========================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="md-code-block"><code>$2</code></pre>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // Headers (### h3, ## h2, # h1) — must come before bold
    html = html.replace(/^#### (.+)$/gm, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 class="md-h2">$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 class="md-h1">$1</h1>');

    // Bold + Italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Horizontal rules
    html = html.replace(/^---+$/gm, '<hr class="md-hr">');

    // Unordered lists (lines starting with - or *)
    html = html.replace(/^[\s]*[-*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\s*)+)/g, '<ul class="md-list">$1</ul>');

    // Ordered lists (lines starting with 1. 2. etc.)
    html = html.replace(/^[\s]*\d+\. (.+)$/gm, '<li>$1</li>');
    // Wrap consecutive <li> not already in <ul> into <ol>
    html = html.replace(/(<li>(?:(?!<\/?[uo]l).)*<\/li>(?:\s*<li>(?:(?!<\/?[uo]l).)*<\/li>)*)/g, (match) => {
        if (!match.includes('<ul') && !match.includes('<ol')) {
            return '<ol class="md-list">' + match + '</ol>';
        }
        return match;
    });

    // Links [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>');

    // Paragraphs: convert double newlines
    html = html.replace(/\n\n/g, '</p><p>');
    // Single newlines to <br> (but not inside pre/code)
    html = html.replace(/(?<!<\/?(pre|code|li|ul|ol|h[1-4]|hr)[^>]*>)\n/g, '<br>');

    return html;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// ==========================================
// Settings Functions
// ==========================================

async function loadSettings() {
    try {
        const data = await apiRequest('/settings');
        currentSettings = data;
        updateSettingsUI();
    } catch (error) {
        console.log('Using default settings', error);
        currentSettings = { model: 'gemini', selected_model: 'gemini-2.0-flash', api_keys: { gemini: [], openai: [], openrouter: [] } };
        updateSettingsUI();
    }
}

async function loadAvailableModels() {
    try {
        const data = await apiRequest('/settings/models');
        availableModels = data.providers || {};
        const selectedModel = data.selected_model || currentSettings.selected_model || 'gemini-2.0-flash';
        populateModelDropdown(selectedModel);
    } catch (error) {
        console.log('Failed to load models', error);
    }
}

function populateModelDropdown(selectedModel) {
    const sel = elements.chatModelSelect;
    sel.innerHTML = '';

    const providerLabels = { gemini: '🟦 Gemini', openai: '🟩 OpenAI', openrouter: '🟨 OpenRouter' };

    for (const [provider, info] of Object.entries(availableModels)) {
        const group = document.createElement('optgroup');
        group.label = providerLabels[provider] || provider;
        const hasKeys = info.has_keys;

        for (const m of info.models) {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.name + (m.free ? ' ✦' : '') + (!hasKeys ? ' 🔑' : '');
            opt.disabled = !hasKeys;
            if (m.id === selectedModel) opt.selected = true;
            group.appendChild(opt);
        }
        sel.appendChild(group);
    }

    sel.disabled = false;
}

function updateSettingsUI() {
    if (elements.modelSelect.value !== currentSettings.model) {
        elements.modelSelect.value = currentSettings.model;
    }
    const provNames = { gemini: 'Gemini', openai: 'OpenAI', openrouter: 'OpenRouter' };
    elements.currentModelStatus.textContent = `${provNames[currentSettings.model] || currentSettings.model} — ${currentSettings.selected_model || ''}`;
    renderSettingsKeys();
}

function renderSettingsKeys() {
    const provider = elements.modelSelect.value;
    const keys = (currentSettings.api_keys && currentSettings.api_keys[provider]) || [];

    if (keys.length === 0) {
        elements.apiKeyList.innerHTML = `
            <div class="empty-keys-state">
                <p>No active keys for ${provider}.</p>
                <p style="font-size: 11px; margin-top: 4px;">Add a key to use this model.</p>
            </div>
        `;
    } else {
        elements.apiKeyList.innerHTML = keys.map(key => {
            const isActive = key.status === 'active';
            const maskedKey = key.masked_key || '';
            const lastUsed = key.last_used;
            return `
            <div class="key-item">
                <div class="key-info">
                    <span class="key-label" title="${key.id}">${key.label} <small style="opacity: 0.7; font-weight: normal;">(${maskedKey})</small></span>
                    <div class="key-stats">
                        <span class="key-badge ${isActive ? 'badge-active' : 'badge-exhausted'}">
                            ${isActive ? 'Active' : 'Exhausted'}
                        </span>
                        <span class="key-mask" title="Usage count">Used: ${key.usage_count || 0}</span>
                        ${lastUsed ? `<span class="key-mask" title="Last used">${new Date(lastUsed).toLocaleDateString()}</span>` : ''}
                    </div>
                </div>
                <button class="remove-key-btn" onclick="removeApiKey('${provider}', '${key.id}')" title="Remove Key">
                    🗑️
                </button>
            </div>
        `;
        }).join('');
    }

    const provNames = { gemini: 'Gemini', openai: 'OpenAI', openrouter: 'OpenRouter' };
    elements.newApiKeyInput.placeholder = `Paste new ${provNames[provider] || provider} API key...`;
}

function openSettingsModal() {
    loadSettings().then(() => {
        elements.settingsModal.style.display = 'flex';
        renderSettingsKeys();
    });
}

function closeSettingsModal() {
    elements.settingsModal.style.display = 'none';
    elements.newApiKeyInput.value = '';
    // Refresh model dropdown in case keys were added
    loadAvailableModels();
}

async function addApiKey() {
    const provider = elements.modelSelect.value;
    const key = elements.newApiKeyInput.value.trim();
    const label = elements.newKeyLabelInput.value.trim();

    if (!key) {
        showToast('Please enter an API key', 'error');
        return;
    }

    try {
        await apiRequest('/settings/keys', 'POST', {
            provider: provider,
            api_key: key,
            label: label || null
        });

        elements.newApiKeyInput.value = '';
        elements.newKeyLabelInput.value = '';
        showToast('API Key added successfully', 'success');
        await loadSettings();
        await loadAvailableModels(); // Sync model availability in dropdown
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function removeApiKey(provider, keyId) {
    if (!confirm('Are you sure you want to remove this API key?')) return;

    try {
        await apiRequest(`/settings/keys/${provider}/${keyId}`, 'DELETE');
        showToast('API Key removed', 'success');
        await loadSettings();
        await loadAvailableModels(); // Sync model availability in dropdown
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function saveSettings() {
    // saveSettings in modal is now just for closing — model is already saved inline
    closeSettingsModal();
    showToast('Settings saved!', 'success');
}

// Make functions globally available
window.selectUser = selectUser;
window.deleteUser = deleteUser;
window.removeApiKey = removeApiKey;
