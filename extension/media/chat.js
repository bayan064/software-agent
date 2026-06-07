// software-agent/extension/media/chat.js

let streamingMessageElement = null;
let conversationsListVisible = false;

// 添加消息到UI
function addMessageToUI(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    // 检测是否是代码（包含 def/class/import 或缩进特征）
    if (role === 'assistant' && (content.includes('def ') || content.includes('class ') || content.includes('import ') || content.includes('    '))) {
        contentDiv.innerHTML = `<pre><code class="language-python">${escapeHtml(content)}</code></pre>`;
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(contentDiv);
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
        contentDiv.innerHTML = `<pre><code class="language-python">${escapeHtml(content)}</code></pre>`;
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
    const contentDiv = messageDiv.querySelector('.message-content');
    // 最终确定时也检测代码
    if (content.includes('def ') || content.includes('class ') || content.includes('import ')) {
        contentDiv.innerHTML = `<pre><code class="language-python">${escapeHtml(content)}</code></pre>`;
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
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

// 简单的 Markdown 格式化
function formatMarkdown(text) {
    // 代码块
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code>${escapeHtml(code)}</code></pre>`;
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
    // 重新添加欢迎消息
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
        <div class="assistant-message">
            <div class="message-content">👋 欢迎使用 Agent UI！</div>
        </div>
    `;
    messagesContainer.appendChild(welcomeDiv);
}

// 自动调整文本框高度
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// 发送消息（Enter发送，Shift+Enter换行）
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);
cancelBtn.addEventListener('click', () => vscode.postMessage({ type: 'cancelGeneration' }));
clearHistoryBtn.addEventListener('click', () => {
    if (confirm('确定要清空所有对话历史吗？')) {
        vscode.postMessage({ type: 'clearHistory' });
    }
});

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
            updateConversationList(message.conversations, message.currentId);
            break;
    }
});

let pendingFiles = [];

function addFileUploadUI() {
    const inputContainer = document.querySelector('.input-container');
    const textarea = document.getElementById('userInput');
    
    const fileBar = document.createElement('div');
    fileBar.className = 'file-upload-bar';
    fileBar.innerHTML = `
        <button id="uploadFileBtn" class="file-btn" title="上传文件">📎</button>
        <span id="fileNameDisplay" class="file-name-display"></span>
        <button id="clearFileBtn" class="clear-file-btn" style="display:none;" title="移除文件">✖</button>
    `;
    
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'fileInput';
    fileInput.style.display = 'none';
    fileInput.multiple = true; // 【修改点】：允许选择多个文件
    fileInput.accept = '.txt,.py,.java,.js,.ts,.json,.md,.csv';
    
    inputContainer.insertBefore(fileBar, textarea);
    inputContainer.appendChild(fileInput);
    
    document.getElementById('uploadFileBtn').addEventListener('click', () => { fileInput.click(); });
    document.getElementById('clearFileBtn').addEventListener('click', () => { clearSelectedFile(); });
    fileInput.addEventListener('change', handleFileSelect);
}

// 【修改点】：循环处理多个文件
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
                addMessageToUI('system', `📎 已添加文件: ${file.name} (${(file.size/1024).toFixed(1)} KB)`);
                resolve();
            };
            reader.readAsText(file, 'UTF-8');
        });
    }
    
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const clearBtn = document.getElementById('clearFileBtn');
    fileNameDisplay.textContent = `📎 已选择 ${pendingFiles.length} 个文件`;
    clearBtn.style.display = 'inline-block';
}

function clearSelectedFile() {
    pendingFiles = []; // 【修改点】：清空数组
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const clearBtn = document.getElementById('clearFileBtn');
    const fileInput = document.getElementById('fileInput');
    
    fileNameDisplay.textContent = '';
    clearBtn.style.display = 'none';
    if (fileInput) fileInput.value = '';
}

function sendMessage() {
    const text = userInput.value.trim();
    
    if (!text && pendingFiles.length === 0) return;
    
    // 【修改点】：删除了这里主动调用的 addMessageToUI('user', ...)，全权交由后端确认后再返回渲染指令
    
    userInput.value = '';
    userInput.style.height = 'auto';
    
    vscode.postMessage({ 
        type: 'sendMessage', 
        text: text || '',
        files: pendingFiles.length > 0 ? pendingFiles : [] // 【修改点】：传出数组
    });
    
    showCancelButton(true);
    clearSelectedFile();
}

// 初始化时添加上传UI
window.addEventListener('DOMContentLoaded', () => {
    addFileUploadUI();
});

function initConversationSidebar() {
    // 创建侧边栏按钮
    const header = document.querySelector('.chat-header');
    const newChatBtn = document.createElement('button');
    newChatBtn.className = 'icon-btn';
    newChatBtn.innerHTML = '➕';
    newChatBtn.title = '新对话';
    newChatBtn.onclick = () => vscode.postMessage({ type: 'newConversation' });
    header.appendChild(newChatBtn);
    
    // 创建对话列表侧边栏
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
    
    // 添加侧边栏切换按钮
    const toggleSidebarBtn = document.createElement('button');
    toggleSidebarBtn.className = 'icon-btn';
    toggleSidebarBtn.innerHTML = '☰';
    toggleSidebarBtn.title = '对话历史';
    toggleSidebarBtn.onclick = () => toggleConversationSidebar();
    header.insertBefore(toggleSidebarBtn, header.firstChild);
    
    // 关闭按钮事件
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
    
    // 绑定点击事件
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
            // 直接向后端发送删除指令
            vscode.postMessage({ type: 'deleteConversation', conversationId: id });
        });
    });
}

function loadConversation(messages) {
    // 清空消息容器
    messagesContainer.innerHTML = '';
    
    // 重新加载所有消息
    messages.forEach(msg => {
        addMessageToUI(msg.role, msg.content);
    });
    
    scrollToBottom();
}

// 修改消息监听
window.addEventListener('message', event => {
    const message = event.data;
    switch (message.type) {
        // ... 现有 case
        case 'updateConversationList':
            updateConversationList(message.conversations);
            break;
        case 'loadConversation':
            loadConversation(message.messages);
            break;
        case 'clearMessages':
            messagesContainer.innerHTML = '';
            break;
    }
});

// 初始化
initConversationSidebar();