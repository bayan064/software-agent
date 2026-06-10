// software-agent/extension/media/chat.js

let streamingMessageElement = null;
let conversationsListVisible = false;

// 全局复制生成代码块函数
window.copyCodeBlock = function(btn) {
    const wrapper = btn.closest('.code-block-wrapper');
    const codeEl = wrapper.querySelector('code');
    if (codeEl) {
        navigator.clipboard.writeText(codeEl.textContent);
        btn.textContent = '✅ 已复制';
        setTimeout(() => { btn.textContent = '📋 复制'; }, 2000);
    }
};

// 封装统一的代码块渲染模板
function renderCodeBlock(code, lang = 'python') {
    return `
    <div class="code-block-wrapper">
        <div class="code-block-header">
            <span>${lang}</span>
            <span class="copy-code-btn" onclick="window.copyCodeBlock(this)">📋 复制</span>
        </div>
        <pre style="margin: 0; border: none; border-radius: 0;"><code class="language-${lang}">${escapeHtml(code)}</code></pre>
    </div>`;
}

// 进入消息编辑模式
function enterEditMode(messageDiv, contentDiv, originalContent) {
    if (messageDiv.classList.contains('editing')) return;
    messageDiv.classList.add('editing');
    
    const oldHTML = contentDiv.innerHTML;
    contentDiv.innerHTML = '';
    
    const textarea = document.createElement('textarea');
    textarea.className = 'edit-textarea';
    textarea.value = originalContent;
    
    const saveBtn = document.createElement('button');
    saveBtn.className = 'primary-btn save-edit-btn';
    saveBtn.textContent = '重新发送';
    
    const cancelEditBtn = document.createElement('button');
    cancelEditBtn.className = 'secondary-btn cancel-edit-btn';
    cancelEditBtn.textContent = '取消';
    
    const btnContainer = document.createElement('div');
    btnContainer.className = 'edit-btn-container';
    btnContainer.appendChild(saveBtn);
    btnContainer.appendChild(cancelEditBtn);
    
    contentDiv.appendChild(textarea);
    contentDiv.appendChild(btnContainer);
    
    saveBtn.addEventListener('click', () => {
        const newText = textarea.value.trim();
        if (newText && newText !== originalContent) {
            messageDiv.classList.remove('editing');
            vscode.postMessage({ type: 'editMessage', text: newText });
        } else {
            messageDiv.classList.remove('editing');
            contentDiv.innerHTML = oldHTML;
        }
    });
    
    cancelEditBtn.addEventListener('click', () => {
        messageDiv.classList.remove('editing');
        contentDiv.innerHTML = oldHTML;
    });
}

function createMessageActions(role, rawContent, messageDiv, contentDiv) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    
    // 复制按钮 - 图标形式
    const copyBtn = document.createElement('button');
    copyBtn.className = 'action-btn copy-msg-btn';
    copyBtn.innerHTML = '📋';
    copyBtn.title = '复制内容';
    copyBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(rawContent);
            copyBtn.innerHTML = '✅';
            copyBtn.style.opacity = '1';
            setTimeout(() => {
                copyBtn.innerHTML = '📋';
            }, 1500);
        } catch (err) {
            copyBtn.innerHTML = '❌';
            setTimeout(() => {
                copyBtn.innerHTML = '📋';
            }, 1500);
        }
    });
    actionsDiv.appendChild(copyBtn);
    
    // 用户消息：编辑按钮
    if (role === 'user') {
        const editBtn = document.createElement('button');
        editBtn.className = 'action-btn edit-msg-btn';
        editBtn.innerHTML = '✏️';
        editBtn.title = '编辑消息';
        editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            enterEditMode(messageDiv, contentDiv, rawContent);
        });
        actionsDiv.appendChild(editBtn);
    }
    
    // 助手消息：重新生成按钮
    if (role === 'assistant') {
        const regenBtn = document.createElement('button');
        regenBtn.className = 'action-btn regen-msg-btn';
        regenBtn.innerHTML = '🔄';
        regenBtn.title = '重新生成';
        regenBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            vscode.postMessage({ type: 'regenerate' });
        });
        actionsDiv.appendChild(regenBtn);
    }
    
    return actionsDiv;
}

// 修改原有的 addMessageToUI 函数，确保正确添加 actions
function addMessageToUI(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 存储原始内容用于编辑/复制
    messageDiv.setAttribute('data-raw-content', content);
    
    if (role === 'assistant' && (content.includes('def ') || content.includes('class ') || content.includes('import ') || content.includes('    '))) {
        contentDiv.innerHTML = renderCodeBlock(content, 'python');
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    messageDiv.appendChild(contentDiv);
    
    // 注入底部工具栏（图标形式）
    if (role === 'user' || role === 'assistant') {
        const actions = createMessageActions(role, content, messageDiv, contentDiv);
        messageDiv.appendChild(actions);
    }
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 添加消息到UI
function addMessageToUI(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'assistant' && (content.includes('def ') || content.includes('class ') || content.includes('import ') || content.includes('    '))) {
        contentDiv.innerHTML = renderCodeBlock(content, 'python');
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    messageDiv.appendChild(contentDiv);
    
    // 注入底层交互工具栏
    if (role === 'user' || role === 'assistant') {
        const actions = createMessageActions(role, content, messageDiv, contentDiv);
        messageDiv.appendChild(actions);
    }
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 创建流式消息容器
function createStreamingMessage(id) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'assistant-message streaming';
    messageDiv.id = `streaming-${id}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<span class="typing-indicator">思考中<span>.</span><span>.</span><span>.</span></span>';
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv;
}

// 更新流式消息
function updateStreamingMessage(id, content, isCode) {
    const messageDiv = document.getElementById(`streaming-${id}`);
    if (!messageDiv) return;
    
    const contentDiv = messageDiv.querySelector('.message-content');
    if (isCode || content.includes('def ') || content.includes('class ')) {
        contentDiv.innerHTML = renderCodeBlock(content, 'python');
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    scrollToBottom();
}

// 完成流式消息
function finalizeStreamingMessage(id, content) {
    const messageDiv = document.getElementById(`streaming-${id}`);
    if (!messageDiv) return;
    
    messageDiv.classList.remove('streaming');
    messageDiv.setAttribute('data-raw-content', content);
    
    const contentDiv = messageDiv.querySelector('.message-content');
    
    if (content.includes('def ') || content.includes('class ') || content.includes('import ')) {
        contentDiv.innerHTML = renderCodeBlock(content, 'python');
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    // 异步完成后加载操作工具栏（图标形式）
    const actions = createMessageActions('assistant', content, messageDiv, contentDiv);
    messageDiv.appendChild(actions);
    
    scrollToBottom();
}

// 显示设计方案
function showDesignProposal(messageId, content) {
    const messageDiv = document.getElementById(`streaming-${messageId}`);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        contentDiv.innerHTML = content;
        messageDiv.classList.remove('streaming');
    }
}

// 简单的 Markdown 格式化升级（适配独占代码块复制）
function formatMarkdown(text) {
    // 3. 代码块单独复制核心匹配逻辑
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `
        <div class="code-block-wrapper">
            <div class="code-block-header">
                <span>${lang || 'code'}</span>
                <span class="copy-code-btn" onclick="window.copyCodeBlock(this)">📋 复制</span>
            </div>
            <pre style="margin: 0; border: none; border-radius: 0;"><code class="language-${lang || 'text'}">${escapeHtml(code)}</code></pre>
        </div>`;
    });
    
    // 行内代码
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // 粗体
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // 换行
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showCancelButton(show) {
    sendBtn.style.display = show ? 'none' : 'inline-block';
    cancelBtn.style.display = show ? 'inline-block' : 'none';
}

function clearMessages() {
    messagesContainer.innerHTML = '';
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
        <div class="assistant-message">
            <div class="message-content">👋 欢迎使用 Software Engineering Agent！</div>
        </div>
    `;
    messagesContainer.appendChild(welcomeDiv);
}

// 自动调整文本框高度
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// 发送消息
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);
// 5. 停止生成绑定
cancelBtn.addEventListener('click', () => vscode.postMessage({ type: 'cancelGeneration' }));

// 【修改点 6】：移除了旧页面上方没用的 clearHistoryBtn 垃圾桶绑定事件

// 监听来自扩展的消息
window.addEventListener('message', event => {
    const message = event.data;
    switch (message.type) {
        case 'addMessage':
            addMessageToUI(message.message.role, message.message.content);
            showCancelButton(false);
            break;
        case 'addStreamingMessage':
            createStreamingMessage(message.id);
            break;
        case 'updateStreamingMessage':
            updateStreamingMessage(message.id, message.content, message.isCode);
            break;
        case 'finalizeStreamingMessage':
            finalizeStreamingMessage(message.id, message.content);
            showCancelButton(false);
            break;
        case 'showDesignProposal':
            showDesignProposal(message.messageId, message.content);
            break;
        case 'clearMessages':
            clearMessages();
            break;
        case 'showCancelButton':
            showCancelButton(message.show);
            break;
        case 'loadConversation':
            if (message.messages) {
                loadConversation(message.messages);
            }
            break;
        case 'updateConversationList':
            updateConversationList(message.conversations);
            break;
    }
});

let pendingFiles = [];

function addFileUploadUI() {
    const inputContainer = document.querySelector('.input-container');
    const textarea = document.getElementById('userInput');
    
    // 创建一个更紧凑的文件指示器
    const fileIndicator = document.createElement('div');
    fileIndicator.className = 'file-indicator';
    fileIndicator.style.display = 'none';
    fileIndicator.innerHTML = `
        <span class="file-badge">📎 <span id="fileCount">0</span> 个文件待发送</span>
        <button id="clearFileBtn" class="clear-file-icon" title="清除文件">✖</button>
    `;
    
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'fileInput';
    fileInput.style.display = 'none';
    fileInput.multiple = true;
    fileInput.accept = '.txt,.py,.java,.js,.ts,.json,.md,.csv';
    
    // 添加一个文件按钮在输入框旁边
    const attachBtn = document.createElement('button');
    attachBtn.className = 'attach-file-btn';
    attachBtn.innerHTML = '📎';
    attachBtn.title = '附加文件';
    attachBtn.addEventListener('click', () => { fileInput.click(); });
    
    // 将按钮放在输入框附近
    const inputWrapper = document.createElement('div');
    inputWrapper.className = 'input-wrapper';
    textarea.parentNode.insertBefore(inputWrapper, textarea);
    inputWrapper.appendChild(textarea);
    inputWrapper.appendChild(attachBtn);
    
    inputContainer.insertBefore(fileIndicator, inputWrapper);
    inputContainer.appendChild(fileInput);
    
    document.getElementById('clearFileBtn')?.addEventListener('click', () => { clearSelectedFile(); });
    fileInput.addEventListener('change', handleFileSelect);
}

async function handleFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.size > 1024 * 1024) {
            vscode.postMessage({ type: 'showWarning', message: `文件 ${file.name} 超过 1MB` });
            continue;
        }
        
        await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                pendingFiles.push({
                    name: file.name,
                    content: e.target.result,
                    size: file.size
                });
                resolve();
            };
            reader.readAsText(file, 'UTF-8');
        });
    }
    
    updateFileIndicator();
}



function updateFileIndicator() {
    const indicator = document.querySelector('.file-indicator');
    const fileCountSpan = document.getElementById('fileCount');
    
    if (pendingFiles.length > 0) {
        indicator.style.display = 'flex';
        if (fileCountSpan) {
            fileCountSpan.textContent = pendingFiles.length;
        }
    } else {
        indicator.style.display = 'none';
    }
}

function clearSelectedFile() {
    pendingFiles = [];
    updateFileIndicator();
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
}

function sendMessage() {
    const text = userInput.value.trim();
    if (!text && pendingFiles.length === 0) return;
    
    // 如果有文件，显示提示消息
    if (pendingFiles.length > 0) {
        const fileNames = pendingFiles.map(f => f.name).join(', ');
        addMessageToUI('system', `📎 正在处理 ${pendingFiles.length} 个文件: ${fileNames}`);
    }
    
    const messageText = text || (pendingFiles.length > 0 ? `请分析以下 ${pendingFiles.length} 个文件的内容` : '');
    
    userInput.value = '';
    userInput.style.height = 'auto';
    
    vscode.postMessage({ 
        type: 'sendMessage', 
        text: messageText,
        files: pendingFiles.length > 0 ? pendingFiles : []
    });
    
    showCancelButton(true);
    clearSelectedFile();
}

initConversationSidebar();
window.addEventListener('DOMContentLoaded', () => {
    addFileUploadUI();
});

function initConversationSidebar() {
    const header = document.querySelector('.chat-header');
    const newChatBtn = document.createElement('button');
    newChatBtn.className = 'icon-btn';
    newChatBtn.innerHTML = '➕';
    newChatBtn.title = '新对话';
    newChatBtn.onclick = () => vscode.postMessage({ type: 'newConversation' });
    header.appendChild(newChatBtn);
    
    const sidebar = document.createElement('div');
    sidebar.id = 'conversationSidebar';
    sidebar.className = 'conversation-sidebar';
    sidebar.innerHTML = `
        <div class="sidebar-header">
            <span>对话历史</span>
            <button id="closeSidebarBtn" class="icon-btn">✖</button>
        </div>
        <div id="conversationList" class="conversation-list"></div>
    `;
    
    document.body.insertBefore(sidebar, document.querySelector('.chat-container'));
    
    const toggleSidebarBtn = document.createElement('button');
    toggleSidebarBtn.className = 'icon-btn';
    toggleSidebarBtn.innerHTML = '☰';
    toggleSidebarBtn.title = '对话历史';
    toggleSidebarBtn.onclick = () => toggleConversationSidebar();
    header.insertBefore(toggleSidebarBtn, header.firstChild);
    
    document.getElementById('closeSidebarBtn')?.addEventListener('click', () => {
        toggleConversationSidebar(false);
    });
}

function toggleConversationSidebar(show) {
    const sidebar = document.getElementById('conversationSidebar');
    if (sidebar) {
        conversationsListVisible = show !== undefined ? show : !conversationsListVisible;
        sidebar.classList.toggle('visible', conversationsListVisible);
    }
}

function updateConversationList(conversations) {
    const container = document.getElementById('conversationList');
    if (!container) return;
    
    container.innerHTML = conversations.map(conv => `
        <div class="conversation-item ${conv.isCurrent ? 'current' : ''}" 
             data-id="${conv.id}">
            <span class="conversation-title">${escapeHtml(conv.title)}</span>
            <button class="delete-conv-btn" data-id="${conv.id}" title="删除">🗑️</button>
        </div>
    `).join('');
    
    container.querySelectorAll('.conversation-item').forEach(item => {
        const id = item.dataset.id;
        item.addEventListener('click', (e) => {
            if (!e.target.classList.contains('delete-conv-btn')) {
                vscode.postMessage({ type: 'switchConversation', conversationId: id });
                toggleConversationSidebar(false);
            }
        });
        
        const deleteBtn = item.querySelector('.delete-conv-btn');
        deleteBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            vscode.postMessage({ type: 'deleteConversation', conversationId: id });
        });
    });
}

function loadConversation(messages) {
    messagesContainer.innerHTML = '';
    messages.forEach(msg => {
        addMessageToUI(msg.role, msg.content);
    });
    scrollToBottom();
}

vscode.postMessage({ type: 'webviewReady' });