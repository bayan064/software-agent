// software-agent/extension/media/chat.js

let streamingMessageElement = null;
let conversationsListVisible = false;
let designMessageIds = new Set();

function getSelectedLanguage() {
    const select = document.getElementById('languageSelect');
    return select ? select.value : 'Python';
}

function getSelectedTask() {
    const select = document.getElementById('taskSelect');
    return select ? select.value : 'full';
}

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
    if (code.includes('@startuml') || lang.toLowerCase() === 'plantuml') {
        lang = 'plantuml';
    }
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
        contentDiv.innerHTML = renderCodeBlock(content, getSelectedLanguage());
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
function updateStreamingMessage(id, content, isCode, language = 'python') {
    const messageDiv = document.getElementById(`streaming-${id}`);
    if (!messageDiv) return;
    
    const contentDiv = messageDiv.querySelector('.message-content');
    if (isCode || content.includes('def ') || content.includes('class ')) {
        contentDiv.innerHTML = renderCodeBlock(content, language);
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    scrollToBottom();
}

// 完成流式消息
function finalizeStreamingMessage(id, content, language = 'python') {
    const messageDiv = document.getElementById(`streaming-${id}`);
    if (!messageDiv) return;

    // 如果已经是设计消息，不做任何覆盖
    if (designMessageIds.has(id) || messageDiv.dataset.isDesign === 'true') {
        messageDiv.classList.remove('streaming');
        showCancelButton(false);
        return;
    }
    
    messageDiv.classList.remove('streaming');
    messageDiv.setAttribute('data-raw-content', content);
    
    const contentDiv = messageDiv.querySelector('.message-content');
    
    // 检查是否是设计内容（包含 PlantUML）
    if (content.includes('@startuml')) {
        // 尝试解析为设计提案格式
        try {
            const designData = JSON.parse(content);
            if (designData.type === 'design_proposal') {
                contentDiv.innerHTML = generateDesignHTML(designData);
                const containers = contentDiv.querySelectorAll('.plantuml-container');
                containers.forEach(container => renderPlantUML(container));
                messageDiv.dataset.isDesign = 'true';
                designMessageIds.add(id);
                const actions = createMessageActions('assistant', content, messageDiv, contentDiv);
                messageDiv.appendChild(actions);
                scrollToBottom();
                showCancelButton(false);
                return;
            }
        } catch (e) {
            // 不是 JSON，但包含 @startuml，按 PlantUML 处理
            contentDiv.innerHTML = renderCodeBlock(content, 'plantuml');
        }
        // 渲染 PlantUML
        const containers = contentDiv.querySelectorAll('.plantuml-container');
        containers.forEach(container => renderPlantUML(container));
        const actions = createMessageActions('assistant', content, messageDiv, contentDiv);
        messageDiv.appendChild(actions);
        scrollToBottom();
        showCancelButton(false);
        return;
    }
    
    // 普通代码块处理
    if (content.includes('def ') || content.includes('class ') || content.includes('import ')) {
        contentDiv.innerHTML = renderCodeBlock(content, language);
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    // 异步完成后加载操作工具栏
    const actions = createMessageActions('assistant', content, messageDiv, contentDiv);
    messageDiv.appendChild(actions);
    
    scrollToBottom();
    showCancelButton(false);
}

// 显示设计方案
function showDesignProposal(messageId, content) {
    const messageDiv = document.getElementById(`streaming-${messageId}`);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        contentDiv.innerHTML = content;
        messageDiv.classList.remove('streaming');
        
        // 标记为设计消息，防止被覆盖
        messageDiv.dataset.isDesign = 'true';
        designMessageIds.add(messageId);
        
        // 渲染所有 PlantUML 图表
        const plantumlContainers = contentDiv.querySelectorAll('.plantuml-container');
        plantumlContainers.forEach(container => {
            renderPlantUML(container);
        });
        
        // 为设计消息添加操作按钮（复制等）
        const rawContent = contentDiv.textContent;
        const actions = createMessageActions('assistant', rawContent, messageDiv, contentDiv);
        messageDiv.appendChild(actions);
        
        scrollToBottom();
    }
}

function formatMarkdown(text) {
    if (!text) return '';
    
    // 1. 代码块（优先处理，避免被其他规则破坏）
    text = text.replace(
        /```(\w*)\n([\s\S]*?)```/g,
        (match, lang, code) => renderCodeBlock(code, lang || 'text')
    );
    
    // 2. 标题（支持 #、##、###、####）- 修复：不要求空格
    text = text.replace(/^####\s*(.*)$/gm, '<h4 style="font-size: 13px; font-weight: 600; margin: 10px 0 4px 0; color: var(--vscode-editor-foreground);">$1</h4>');
    text = text.replace(/^###\s*(.*)$/gm, '<h3 style="font-size: 14px; font-weight: 600; margin: 12px 0 6px 0; color: var(--vscode-editor-foreground);">$1</h3>');
    text = text.replace(/^##\s*(.*)$/gm, '<h2 style="font-size: 16px; font-weight: 600; margin: 14px 0 8px 0; color: var(--vscode-editor-foreground); border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 4px;">$1</h2>');
    text = text.replace(/^#\s*(.*)$/gm, '<h1 style="font-size: 18px; font-weight: 700; margin: 16px 0 10px 0; color: var(--vscode-editor-foreground);">$1</h1>');
    
    // 3. 无序列表（支持 -、*、•）
    text = text.replace(/^[\-*•]\s+(.*)$/gm, '<li style="margin-left: 20px; list-style-type: disc; padding: 2px 0;">$1</li>');
    
    // 4. 有序列表
    text = text.replace(/^\d+\.\s+(.*)$/gm, '<li style="margin-left: 20px; list-style-type: decimal; padding: 2px 0;">$1</li>');
    
    // 5. 粗体
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 6. 斜体
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // 7. 行内代码
    text = text.replace(/`([^`]+)`/g, '<code style="background: var(--vscode-textCodeBlock-background); padding: 2px 6px; border-radius: 4px; font-size: 0.9em;">$1</code>');
    
    // 8. 将连续的列表项用 <ul> 包裹
    text = text.replace(/((?:<li[^>]*>.*?<\/li>\s*)+)/g, '<ul style="margin: 4px 0; padding-left: 0; list-style: none;">$1</ul>');
    
    // 9. 处理段落
    const lines = text.split('\n');
    let result = '';
    let inList = false;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        // 检查是否是列表项
        if (line.startsWith('<li') || line.startsWith('</li>')) {
            result += line;
            inList = true;
            continue;
        }
        
        // 检查是否是标题
        if (line.startsWith('<h')) {
            if (inList) inList = false;
            result += line;
            continue;
        }
        
        // 检查是否是代码块
        if (line.startsWith('<div') || line.startsWith('<pre') || line.startsWith('<code')) {
            if (inList) inList = false;
            result += line;
            continue;
        }
        
        // 普通文本，用 <p> 包裹
        if (inList) inList = false;
        result += `<p style="margin: 4px 0; line-height: 1.6;">${line}</p>`;
    }
    
    return result || text;
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

// ================= 新增：初始化语言和任务选择器 =================
function initSelectors() {
    // 在输入框上方添加控制栏
    const inputContainer = document.querySelector('.input-container');
    const textarea = document.getElementById('userInput');
    
    // 创建控制栏
    const controlBar = document.createElement('div');
    controlBar.className = 'control-bar';
    controlBar.style.cssText = `
        display: flex;
        gap: 12px;
        margin-bottom: 10px;
        align-items: center;
        flex-wrap: wrap;
    `;
    
    // 语言选择器
    const langGroup = document.createElement('div');
    langGroup.className = 'control-group';
    langGroup.style.cssText = 'display: flex; align-items: center; gap: 6px;';
    
    const langLabel = document.createElement('label');
    langLabel.textContent = '🌐 语言:';
    langLabel.style.cssText = 'font-size: 12px; color: var(--vscode-descriptionForeground);';
    
    const langSelect = document.createElement('select');
    langSelect.id = 'languageSelect';
    langSelect.style.cssText = `
        background: var(--vscode-input-background);
        color: var(--vscode-input-foreground);
        border: 1px solid var(--vscode-input-border);
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        outline: none;
    `;
    langSelect.innerHTML = `
        <option value="Python">Python</option>
        <option value="Java">Java</option>
        <option value="JavaScript">JavaScript</option>
        <option value="TypeScript">TypeScript</option>
        <option value="C++">C++</option>
        <option value="Go">Go</option>
    `;
    langGroup.appendChild(langLabel);
    langGroup.appendChild(langSelect);
    
    // 任务模式选择器
    const taskGroup = document.createElement('div');
    taskGroup.className = 'control-group';
    taskGroup.style.cssText = 'display: flex; align-items: center; gap: 6px;';
    
    const taskLabel = document.createElement('label');
    taskLabel.textContent = '🎯 模式:';
    taskLabel.style.cssText = 'font-size: 12px; color: var(--vscode-descriptionForeground);';
    
    const taskSelect = document.createElement('select');
    taskSelect.id = 'taskSelect';
    taskSelect.style.cssText = `
        background: var(--vscode-input-background);
        color: var(--vscode-input-foreground);
        border: 1px solid var(--vscode-input-border);
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        outline: none;
    `;
    taskSelect.innerHTML = `
        <option value="full">📐 设计 + 代码</option>
        <option value="design">📋 仅设计 (UML)</option>
        <option value="code">💻 仅代码</option>
        <option value="fix">🔧 仅修复</option>
    `;
    taskGroup.appendChild(taskLabel);
    taskGroup.appendChild(taskSelect);
    
    controlBar.appendChild(langGroup);
    controlBar.appendChild(taskGroup);

    function toggleLanguageSelect() {
        if (taskSelect.value === 'design') {
            langGroup.style.display = 'none'; // 选 UML 时隐藏语言
        } else {
            langGroup.style.display = 'flex'; // 其他模式显示语言
        }
    }

    // 2. 监听模式下拉框的切换事件
    taskSelect.addEventListener('change', toggleLanguageSelect);

    // 3. 界面初始化时先执行一次，确保初始状态正确
    toggleLanguageSelect();
    
    // 插入到 textarea 之前
    inputContainer.insertBefore(controlBar, textarea);
}

function renderDesignToUI(proposal) {
    const container = document.getElementById('messagesContainer');

    const div = document.createElement('div');
    div.className = 'assistant-message';

     div.innerHTML =
        generateDesignHTML(proposal);

    container.appendChild(div);

    div.querySelectorAll('.plantuml-container')
       .forEach(renderPlantUML);

    scrollToBottom();
}

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
            updateStreamingMessage(message.id, message.content, message.isCode, message.language);
            break;
        case 'finalizeStreamingMessage':
            finalizeStreamingMessage(message.id, message.content, message.language);
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
        case 'renderDesign': 
            renderDesignToUI(message.designProposal);
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
    
    // 获取用户选择的语言和任务模式
    const language = getSelectedLanguage();
    const task = getSelectedTask();
    
    // 显示模式提示
    const taskLabels = {
        'design': '📋 设计模式 (生成 UML)',
        'code': '💻 代码生成模式',
        'full': '📐 设计 + 代码模式',
        'fix': '🔧 修复模式'
    };

    // 如果有文件，显示提示消息
    if (pendingFiles.length > 0) {
        const fileNames = pendingFiles.map(f => f.name).join(', ');
        addMessageToUI('system', `📎 正在处理 ${pendingFiles.length} 个文件: ${fileNames}`);
    }
    
    // 显示当前模式
    addMessageToUI('system', `${taskLabels[task] || '💻 代码生成模式'} | 语言: ${language}`);

    const messageText = text || (pendingFiles.length > 0 ? `请分析以下 ${pendingFiles.length} 个文件的内容` : '');
    
    userInput.value = '';
    userInput.style.height = 'auto';
    
    vscode.postMessage({ 
        type: 'sendMessage', 
        text: messageText,
        files: pendingFiles.length > 0 ? pendingFiles : [],
        language: language,    // 新增
        task: task             // 新增
    });
    
    showCancelButton(true);
    clearSelectedFile();
}

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

function encodePlantUML(text) {
    // 直接 URL 编码，最简单可靠
    return encodeURIComponent(text);
}

function renderPlantUML(container) {
    const codeElement = container.querySelector('.plantuml-code code');
    if (!codeElement) return;
    
    const plantumlCode = codeElement.textContent.trim();
    if (!plantumlCode || !plantumlCode.includes('@startuml')) {
        return;
    }
    
    const renderDiv = container.querySelector('.plantuml-render');
    if (!renderDiv) return;
    
    // 只显示原始代码，不进行渲染
    renderDiv.innerHTML = `
        <div style="padding: 12px; background: var(--vscode-editor-background); border-radius: 4px; text-align: left; font-family: var(--vscode-editor-font-family); font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; border: 1px solid var(--vscode-panel-border);">
            <div style="color: var(--vscode-descriptionForeground); margin-bottom: 8px; font-size: 12px;">📄 PlantUML 源码:</div>
            ${escapeHtml(plantumlCode)}
        </div>
    `;
    
    // 隐藏原始代码块
    const codeDiv = container.querySelector('.plantuml-code');
    if (codeDiv) {
        codeDiv.style.display = 'none';
    }
}

function showDesignProposal(messageId, content) {
    const messageDiv = document.getElementById(`streaming-${messageId}`);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        
        // 直接设置内容，不包含任何操作按钮（由 createMessageActions 统一管理）
        contentDiv.innerHTML = content;
        messageDiv.classList.remove('streaming');
        
        // 标记为设计消息，防止被覆盖
        messageDiv.dataset.isDesign = 'true';
        designMessageIds.add(messageId);
        
        // 渲染所有 PlantUML 图表
        const plantumlContainers = contentDiv.querySelectorAll('.plantuml-container');
        plantumlContainers.forEach(container => {
            renderPlantUML(container);
        });
        
        // 为设计消息添加操作按钮（复制、重新生成）
        const rawContent = contentDiv.textContent;
        const actions = createMessageActions('assistant', rawContent, messageDiv, contentDiv);
        messageDiv.appendChild(actions);
        
        scrollToBottom();
        showCancelButton(false);
    }
}

// 在 finalizeStreamingMessage 中也添加渲染支持
// 修改原有的 finalizeStreamingMessage 函数
function finalizeStreamingMessage(id, content, language = 'python') {
    const messageDiv = document.getElementById(`streaming-${id}`);
    if (!messageDiv) return;
    
    messageDiv.classList.remove('streaming');
    messageDiv.setAttribute('data-raw-content', content);
    
    const contentDiv = messageDiv.querySelector('.message-content');
    
    // 检查是否是设计内容（包含 PlantUML）
    if (content.includes('@startuml') || content.includes('class_diagram') || content.includes('activity_diagram')) {
        // 尝试解析为设计提案格式
        try {
            // 如果内容是 JSON 格式的设计数据
            const designData = JSON.parse(content);
            if (designData.type === 'design_proposal') {
                // 使用设计提案渲染
                contentDiv.innerHTML = generateDesignHTML(designData);
                // 渲染 PlantUML
                const containers = contentDiv.querySelectorAll('.plantuml-container');
                containers.forEach(container => renderPlantUML(container));
                return;
            }
        } catch (e) {
            // 不是 JSON，作为普通内容处理
        }
    }
    
    // 普通代码块处理
    if (content.includes('def ') || content.includes('class ') || content.includes('import ')) {
        contentDiv.innerHTML = renderCodeBlock(content, language);
    } else {
        contentDiv.innerHTML = formatMarkdown(content);
    }
    
    // 异步完成后加载操作工具栏
    const actions = createMessageActions('assistant', content, messageDiv, contentDiv);
    messageDiv.appendChild(actions);
    
    scrollToBottom();
}

// 生成设计提案 HTML
function generateDesignHTML(designData) {
    const classDiagram = designData.architecture || '';
    const activityDiagram = designData.components ? designData.components.join('\n') : '';
    
    // 修复1：调换escape与formatMarkdown顺序，先markdown渲染，不提前转义破坏语法
    const rawDesc = designData.description?.trim() || '暂无设计描述';
    const descriptionHtml = formatMarkdown(rawDesc);
    
    return `
        <div class="design-proposal">
            <div class="proposal-title">📐 ${escapeHtml(designData.title || '系统设计模型')}</div>
            <!-- 修复2：追加message-content类，复用已有markdown排版样式 -->
            <div class="proposal-description message-content">${descriptionHtml}</div>
            
            ${classDiagram ? `
            <div class="proposal-architecture">
                <strong>类图 (Class Diagram):</strong>
                <div class="plantuml-container">
                    <pre class="plantuml-code"><code>${escapeHtml(classDiagram)}</code></pre>
                    <div class="plantuml-render"></div>
                </div>
            </div>` : ''}
            
            ${activityDiagram ? `
            <div class="proposal-components">
                <strong>活动图 (Activity Diagram):</strong>
                <div class="plantuml-container">
                    <pre class="plantuml-code"><code>${escapeHtml(activityDiagram)}</code></pre>
                    <div class="plantuml-render"></div>
                </div>
            </div>` : ''}
        </div>
    `;
}

window.addEventListener('DOMContentLoaded', () => {
    initSelectors();      
    addFileUploadUI();
    initConversationSidebar();
    vscode.postMessage({ type: 'webviewReady' });
});