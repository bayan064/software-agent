// software-agent/extension/media/chat.js

let streamingMessageElement = null;

// 发送消息
function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // 只添加一次用户消息到界面
    addMessageToUI('user', text);
    
    // 清空输入框
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // 发送到扩展（后端不会再返回用户消息）
    vscode.postMessage({ type: 'sendMessage', text });
    showCancelButton(true);
}

// 添加消息到UI
function addMessageToUI(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
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
    if (isCode) {
        contentDiv.innerHTML = `<pre><code>${escapeHtml(content)}</code></pre>`;
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
    contentDiv.innerHTML = formatMarkdown(content);
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
    }
});