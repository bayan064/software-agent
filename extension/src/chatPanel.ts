// software-agent/extension/src/chatPanel.ts
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;       // 依然完整保留送给后端智能体的总上下文内容
    displayText?: string;  // 【修改点 7】：专门供给前端渲染和编辑的安全文本（纯文字+微标，绝不漏出代码全文）
    code?: string;
    isStreaming?: boolean;
    designProposal?: DesignProposal;
}

interface DesignProposal {
    title: string;
    description: string;
    architecture: string;
    components: string[];
    pending: boolean;
}

interface Conversation {
    id: string;
    title: string;
    messages: Message[];
    createdAt: Date;
    updatedAt: Date;
}

export class ChatPanelProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'agent-ui.chatView';
    private _view?: vscode.WebviewView;
    private _messages: Message[] = [];
    private _conversations: Conversation[] = [];
    private _currentConversationId: string = '';
    private _abortController?: AbortController;
    private _pendingDesignProposal?: DesignProposal;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _context: vscode.ExtensionContext
    ) {
        this._loadConversations();
        // 清理所有空的新对话
        this._cleanupEmptyNewConversation();
        
        // 如果有历史对话，切换到最新的那个，否则创建新对话
        if (this._conversations.length > 0) {
            this._currentConversationId = this._conversations[0].id;
            this._messages = this._conversations[0].messages;
        } else {
            // 创建新对话但不立即保存到 conversations 中（标记为临时）
            this._createNewConversation(false);
        }
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage((data) => {
            if (data.type === 'webviewReady') {
                this._updateConversationList();
                
                this._cleanupEmptyNewConversation();

                const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
                if (currentConv && currentConv.messages.length > 0) {
                    // 重载历史时同样映射干净的渲染文字
                    this._view?.webview.postMessage({
                        type: 'loadConversation',
                        messages: currentConv.messages.map(m => ({ role: m.role, content: m.displayText || m.content }))
                    });
                }
            } else if (this._conversations.length === 0) {
                // 如果没有对话，创建一个新的
                this._createNewConversation(true);
            }
        });

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    await this._handleUserMessage(data.text, data.files);
                    break;
                case 'editMessage': // 【修改点 1】：捕获前端发起的编辑重发指令
                    await this._handleEditMessage(data.text);
                    break;
                case 'regenerate':  // 【修改点 4】：捕获前端触发的全新生成响应指令
                    await this._handleRegenerate();
                    break;
                case 'showWarning':
                    vscode.window.showWarningMessage(data.message);
                    break;
                case 'applyCode':
                    this._applyCodeToEditor(data.code);
                    break;
                case 'approveDesign':
                    await this._handleDesignApproval(true);
                    break;
                case 'rejectDesign':
                    await this._handleDesignApproval(false);
                    break;
                case 'cancelGeneration': // 【修改点 5】：中断当前正在流式响应的底层 Abort 钩子
                    this._cancelGeneration();
                    break;
                case 'retry':
                    await this._retryLastMessage();
                    break;
                case 'clearHistory':
                    this._clearHistory();
                    break;
                case 'newConversation':
                    this._createNewConversation();
                    break;
                case 'switchConversation':
                    this._switchConversation(data.conversationId);
                    break;
                case 'deleteConversation': {
                    const selection = await vscode.window.showWarningMessage(
                        '确定要删除这个对话吗？',
                        { modal: true },
                        '确定'
                    );
                    if (selection === '确定') {
                        this._deleteConversation(data.conversationId);
                    }
                    break;
                }
            }
        });

        this._addSystemMessage('👋 欢迎使用 Agent UI！\n\n我可以帮助你生成代码、设计方案。请告诉我你的需求。');
    }

    private _loadConversations() {
        const saved = this._context.globalState.get<Conversation[]>('conversations');
        if (saved) {
            this._conversations = saved.map(conv => ({
                ...conv,
                createdAt: new Date(conv.createdAt),
                updatedAt: new Date(conv.updatedAt)
            }));
        }
    }

    private _saveConversations() {
        this._context.globalState.update('conversations', this._conversations);
    }

    private _createNewConversation(shouldSave: boolean = true): string {
        const id = Date.now().toString();
        const newConv: Conversation = {
            id: id,
            title: '新对话',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date()
        };
        
        if (shouldSave) {
            this._conversations.unshift(newConv);
            this._saveConversations();
        }
        
        this._currentConversationId = id;
        this._messages = [];
        
        this._updateConversationList();
        this._view?.webview.postMessage({ type: 'clearMessages' });
        this._addSystemMessage('👋 欢迎使用 Agent UI！\n\n我可以帮助你生成代码、设计方案。请告诉我你的需求。');
        
        return id;
    }

    private _cleanupEmptyNewConversation() {
        // 找到所有标题为"新对话"且没有消息的对话
        const emptyNewConvs = this._conversations.filter(
            conv => conv.title === '新对话' && conv.messages.length === 0
        );
        
        for (const emptyConv of emptyNewConvs) {
            const index = this._conversations.findIndex(c => c.id === emptyConv.id);
            if (index !== -1) {
                this._conversations.splice(index, 1);
            }
        }
        
        if (emptyNewConvs.length > 0) {
            this._saveConversations();
            this._updateConversationList();
        }
    }

    private _switchConversation(id: string) {
        // 在切换前，先清理当前的空对话（如果不是同一个）
        const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
        if (currentConv && currentConv.title === '新对话' && currentConv.messages.length === 0 && currentConv.id !== id) {
            this._deleteConversation(this._currentConversationId, false); // 静默删除，不弹窗
        }
        
        const conv = this._conversations.find(c => c.id === id);
        if (conv) {
            this._currentConversationId = id;
            this._messages = conv.messages;

            // 切换对话过滤显示渲染文案
            this._view?.webview.postMessage({
                type: 'loadConversation',
                messages: conv.messages.map(m => ({ role: m.role, content: m.displayText || m.content }))
            });

            this._updateConversationList();
        }
        
        // 如果切换后没有对话了，创建一个新的临时对话
        if (this._conversations.length === 0) {
            this._createNewConversation(false);
        }
    }

    private _deleteConversation(conversationId: string, showConfirm: boolean = true) {
        const deleteAction = () => {
            const index = this._conversations.findIndex(c => c.id === conversationId);
            if (index === -1) return;
            
            this._conversations.splice(index, 1);
            
            if (this._conversations.length === 0) {
                this._createNewConversation(false);
            } else if (this._currentConversationId === conversationId) {
                this._switchConversation(this._conversations[0].id);
            }
            
            this._saveConversations();
            this._updateConversationList();
        };

        if (showConfirm) {
            vscode.window.showWarningMessage(
                '确定要删除这个对话吗？',
                { modal: true },
                '确定'
            ).then(selection => {
                if (selection === '确定') {
                    deleteAction();
                }
            });
        } else {
            deleteAction();
        }
    }

    private _updateConversationTitle(conversationId: string, firstMessage: string) {
    const conv = this._conversations.find(c => c.id === conversationId);
    if (conv && conv.title === '新对话') {
        // 使用时间戳让标题更有区分度
        const now = new Date();
        const timeStr = `${now.getMonth()+1}/${now.getDate()} ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
        let title = firstMessage.slice(0, 15) + (firstMessage.length > 15 ? '...' : '');
        // 如果没有有效文本内容（比如只有文件），使用时间作为标题
        if (!title || title.length === 0) {
            title = `对话 ${timeStr}`;
        } else {
            title = `${title} (${timeStr})`;
        }
        conv.title = title;
        this._saveConversations();
        this._updateConversationList();
    }
}

    private _updateConversationList() {
        this._view?.webview.postMessage({
            type: 'updateConversationList',
            conversations: this._conversations.map(c => ({
                id: c.id,
                title: c.title,
                isCurrent: c.id === this._currentConversationId
            }))
        });
    }

    // 【修改点 1】：回滚历史记录并替换为最新编辑的文字内容
    private async _handleEditMessage(text: string) {
        const index = this._messages.map(m => m.role).lastIndexOf('user');
        if (index !== -1) {
            this._messages = this._messages.slice(0, index);
            const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
            if (currentConv) {
                currentConv.messages = this._messages;
            }
            // 刷新前端界面视轨
            this._view?.webview.postMessage({
                type: 'loadConversation',
                messages: this._messages.map(m => ({ role: m.role, content: m.displayText || m.content }))
            });
            // 模拟全新指令投递
            await this._handleUserMessage(text);
        }
    }

    // 【修改点 4】：清洗最后一次助手应答并引导后台流式重新响应
    private async _handleRegenerate() {
        if (this._messages.length > 0 && this._messages[this._messages.length - 1].role === 'assistant') {
            this._messages.pop();
        }
        const lastUserMessage = [...this._messages].reverse().find(m => m.role === 'user');
        if (lastUserMessage) {
            const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
            if (currentConv) {
                currentConv.messages = this._messages;
            }
            this._view?.webview.postMessage({
                type: 'loadConversation',
                messages: this._messages.map(m => ({ role: m.role, content: m.displayText || m.content }))
            });
            await this._streamResponse(lastUserMessage.content);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const cssPath = path.join(this._extensionUri.fsPath, 'media', 'chat.css');
        const jsPath = path.join(this._extensionUri.fsPath, 'media', 'chat.js');
        
        let cssContent = '';
        let jsContent = '';
        
        try {
            cssContent = fs.readFileSync(cssPath, 'utf8');
            jsContent = fs.readFileSync(jsPath, 'utf8');
        } catch (error) {
            console.error('Failed to read media files:', error);
        }

        return `<!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'unsafe-inline';">
            <style>
                ${cssContent}
                /* 补充微调微型交互动作栏样式 */
                .message-actions {
                    display: flex;
                    gap: 4px;
                    margin-top: 6px;
                    justify-content: flex-end;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }

                .user-message:hover .message-actions,
                .assistant-message:hover .message-actions {
                    opacity: 1;
                }

                .action-btn {
                    background: var(--vscode-button-secondaryBackground);
                    border: none;
                    cursor: pointer;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: var(--vscode-button-secondaryForeground);
                    transition: all 0.2s ease;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 28px;
                }

                .action-btn:hover {
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    transform: scale(1.05);
                }
                .edit-textarea {
                    width: 100%;
                    background: var(--vscode-input-background);
                    color: var(--vscode-input-foreground);
                    border: 1px solid var(--vscode-input-border);
                    border-radius: 6px;
                    padding: 8px;
                    font-family: inherit;
                    font-size: 13px;
                    resize: vertical;
                    margin-bottom: 6px;
                }

                .edit-btn-container {
                    display: flex;
                    justify-content: flex-end;
                    gap: 6px;
                }
                .code-block-wrapper {
                    margin: 10px 0;
                    border-radius: 6px;
                    overflow: hidden;
                    border: 1px solid var(--vscode-panel-border);
                }
                .code-block-header {
                    display: flex;
                    justify-content: space-between;
                    background: var(--vscode-sideBar-background);
                    padding: 4px 10px;
                    font-size: 11px;
                    border-bottom: 1px solid var(--vscode-panel-border);
                    color: var(--vscode-descriptionForeground);
                }
            </style>
            <title>Agent UI Chat</title>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <h3>🤖 Agent UI Assistant</h3>
                    </div>
                <div class="messages-container" id="messagesContainer">
                    <div class="welcome-message">
                        <div class="assistant-message">
                            <div class="message-content">👋 欢迎使用 Agent UI！</div>
                        </div>
                    </div>
                </div>
                <div class="input-container">
                    <textarea id="userInput" placeholder="输入你的需求..." rows="3"></textarea>
                    <div class="input-actions">
                        <button id="sendBtn" class="primary-btn">发送</button>
                        <button id="cancelBtn" class="secondary-btn" style="display:none;">停止生成</button>
                    </div>
                </div>
            </div>
            <script>
                const vscode = acquireVsCodeApi();
                ${jsContent}
            </script>
        </body>
        </html>`;
    }

    private async _handleUserMessage(text: string, files?: { name: string; content: string }[]) {
        if (!text.trim() && (!files || files.length === 0)) return;

        let fullRequirement = text || '';
        let displayTitle = text || '';
        let displayText = text || '';

        // 检查当前对话是否为空的新对话（临时对话）
        const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
        const isEmptyNewConv = currentConv === undefined && this._currentConversationId !== '';
        
        // 如果是临时空对话，需要先保存它
        if (isEmptyNewConv) {
            const newConv: Conversation = {
                id: this._currentConversationId,
                title: '新对话',
                messages: [],
                createdAt: new Date(),
                updatedAt: new Date()
            };
            this._conversations.unshift(newConv);
            this._saveConversations();
            this._updateConversationList();
        }

        // 【修改点 7】：建立安全的显示文案，阻断源文件内容泄露到 DOM 结构中
        if (files && files.length > 0) {
            const filesText = files.map(f => `[文件: ${f.name}]\n\`\`\`\n${f.content}\n\`\`\``).join('\n\n');
            fullRequirement = `${text ? text + '\n\n' : ''}${filesText}`;
            
            const fileBadges = files.map(f => `📎 [已附加文件上下文: ${f.name}]`).join(' ');
            displayText = `${text ? text + '\n\n' : ''}${fileBadges}`;
            
            if (!displayTitle) displayTitle = `提交了 ${files.length} 个本地上下文`;
        } else {
            displayText = text;
        }

        const userMessage: Message = { 
            role: 'user', 
            content: fullRequirement,
            displayText: displayText
        };
        this._messages.push(userMessage);

        // 找到或创建当前的对话对象
        let conv = this._conversations.find(c => c.id === this._currentConversationId);
        if (!conv) {
            conv = {
                id: this._currentConversationId,
                title: '新对话',
                messages: [],
                createdAt: new Date(),
                updatedAt: new Date()
            };
            this._conversations.unshift(conv);
        }
        
        // 更新对话标题（第一条消息）
        if (conv.messages.length === 1) {
            this._updateConversationTitle(this._currentConversationId, displayTitle || text);
        }

        conv.messages = this._messages;
        conv.updatedAt = new Date();
        this._saveConversations();

        // 发送给前端 UI 时只派发经过净化过滤的 displayText 
        this._view?.webview.postMessage({
            type: 'addMessage',
            message: { role: userMessage.role, content: displayText }
        });

        await this._streamResponse(fullRequirement);
    }

    private async _streamResponse(requirement: string) {
        const config = vscode.workspace.getConfiguration('agent-ui');
        const baseUrl = config.get<string>('baseUrl') ?? 'http://127.0.0.1:8000';
        const endpoint = new URL('/stream', baseUrl).toString();

        this._abortController = new AbortController();
        
        const assistantMessage: Message = {
            role: 'assistant',
            content: '',
            isStreaming: true
        };
        this._messages.push(assistantMessage);
        const messageId = this._addStreamingMessageToView();

        const history = this._messages
            .filter(m => m.role === 'user' || m.role === 'assistant')
            .slice(0, -1)
            .map(m => ({ role: m.role, content: m.content }));
            
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ requirement, history }),
                signal: this._abortController.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            if (!reader) throw new Error('No response body');

            let buffer = '';
            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.type === 'design_proposal') {
                                const proposal: DesignProposal = {
                                    title: parsed.title,
                                    description: parsed.description,
                                    architecture: parsed.architecture,
                                    components: parsed.components,
                                    pending: true
                                };
                                this._pendingDesignProposal = proposal;
                                this._showDesignProposal(proposal, messageId);
                            } else if (parsed.type === 'code_chunk') {
                                fullContent += parsed.content;
                                this._updateStreamingMessage(messageId, fullContent, parsed.isCode);
                            } else if (parsed.type === 'complete') {
                                assistantMessage.content = fullContent;
                                assistantMessage.isStreaming = false;
                                if (parsed.code) {
                                    assistantMessage.code = parsed.code;
                                }
                                this._finalizeStreamingMessage(messageId, fullContent);
                            }
                        } catch (e) {
                            console.error('Parse error:', e);
                        }
                    }
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                this._updateStreamingMessage(messageId, '\n\n❌ 生成已由用户停止。', false);
            } else {
                const errorMsg = `❌ 错误: ${error instanceof Error ? error.message : String(error)}`;
                this._updateStreamingMessage(messageId, errorMsg, false);
            }
            assistantMessage.isStreaming = false;
        } finally {
            this._abortController = undefined;
            this._showCancelButton(false);
        }
    }

    private _showDesignProposal(proposal: DesignProposal, messageId: string) {
        const proposalHtml = `
            <div class="design-proposal">
                <div class="proposal-title">📐 ${this._escapeHtml(proposal.title)}</div>
                <div class="proposal-description">${this._escapeHtml(proposal.description)}</div>
                <div class="proposal-architecture">
                    <strong>架构设计：</strong>
                    <pre>${this._escapeHtml(proposal.architecture)}</pre>
                </div>
                <div class="proposal-components">
                    <strong>组件：</strong>
                    <ul>${proposal.components.map(c => `<li>${this._escapeHtml(c)}</li>`).join('')}</ul>
                </div>
                <div class="proposal-actions">
                    <button class="approve-btn" onclick="vscode.postMessage({type:'approveDesign'})">✅ 确认采用</button>
                    <button class="reject-btn" onclick="vscode.postMessage({type:'rejectDesign'})">❌ 重新设计</button>
                </div>
            </div>
        `;
        
        this._view?.webview.postMessage({
            type: 'showDesignProposal',
            messageId,
            content: proposalHtml
        });
    }

    private async _handleDesignApproval(approved: boolean) {
        if (!this._pendingDesignProposal) return;

        if (approved) {
            await this._continueWithDesign(this._pendingDesignProposal);
        } else {
            const feedback = await vscode.window.showInputBox({
                prompt: '请说明需要如何修改设计方案',
                placeHolder: '例如：应该使用 MVC 架构...'
            });
            if (feedback) {
                await this._streamResponse(`修改设计方案：${feedback}\n原需求：${this._messages[this._messages.length - 2]?.content}`);
            }
        }
        this._pendingDesignProposal = undefined;
    }

    private async _continueWithDesign(proposal: DesignProposal) {
        this._addSystemMessage('✅ 设计方案已确认，正在生成代码...');
        const config = vscode.workspace.getConfiguration('agent-ui');
        const baseUrl = config.get<string>('baseUrl') ?? 'http://127.0.0.1:8000';
        const endpoint = new URL('/generate-code', baseUrl).toString();

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ design: proposal })
            });

            const data = await response.json();
            if (data.code) {
                this._showCodeWithApplyButton(data.code);
            }
        } catch (error) {
            vscode.window.showErrorMessage(`生成代码失败: ${error}`);
        }
    }

    private _showCodeWithApplyButton(code: string) {
        const assistantMessage: Message = {
            role: 'assistant',
            content: '代码已生成：',
            code: code
        };
        this._messages.push(assistantMessage);
        
        const codeHtml = `
            <div class="code-block">
                <pre><code>${this._escapeHtml(code)}</code></pre>
                <button class="apply-code-btn" onclick="vscode.postMessage({type:'applyCode', code: ${JSON.stringify(code)}})">📋 应用到编辑器</button>
            </div>
        `;
        
        this._view?.webview.postMessage({
            type: 'addMessage',
            message: { role: 'assistant', content: codeHtml }
        });
    }

    private _applyCodeToEditor(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            editor.edit(editBuilder => {
                const selection = editor.selection;
                editBuilder.replace(selection, code);
            });
            vscode.window.showInformationMessage('代码已应用到编辑器');
        } else {
            vscode.workspace.openTextDocument({ content: code, language: 'python' }).then(doc => {
                vscode.window.showTextDocument(doc);
            });
        }
    }

    private _cancelGeneration() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = undefined;
        }
    }

    private async _retryLastMessage() {
        const lastUserMessage = [...this._messages].reverse().find(m => m.role === 'user');
        if (lastUserMessage) {
            await this._streamResponse(lastUserMessage.content);
        }
    }

    private _clearHistory() {
        this._messages = [];
        this._view?.webview.postMessage({ type: 'clearMessages' });
        this._addSystemMessage('历史记录已清空');
    }

    private _addMessageToView(message: Message) {
        this._view?.webview.postMessage({
            type: 'addMessage',
            message: { role: message.role, content: message.content }
        });
    }

    private _addSystemMessage(content: string) {
        const systemMessage: Message = { role: 'system', content };
        this._messages.push(systemMessage);
        this._addMessageToView(systemMessage);
    }

    private _addStreamingMessageToView(): string {
        const id = Date.now().toString();
        this._view?.webview.postMessage({
            type: 'addStreamingMessage',
            id
        });
        return id;
    }

    private _updateStreamingMessage(id: string, content: string, isCode: boolean = false) {
        this._view?.webview.postMessage({
            type: 'updateStreamingMessage',
            id,
            content,
            isCode
        });
    }

    private _finalizeStreamingMessage(id: string, content: string) {
        const assistantMessage: Message = { role: 'assistant', content: content };
        const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
        if (currentConv) {
            currentConv.updatedAt = new Date();
            this._saveConversations();
        }

        this._view?.webview.postMessage({
            type: 'finalizeStreamingMessage',
            id,
            content
        });
        this._showCancelButton(false);
    }

    private _showCancelButton(show: boolean) {
        this._view?.webview.postMessage({
            type: 'showCancelButton',
            show
        });
    }

    private _escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}