// software-agent/extension/src/chatPanel.ts
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;       
    displayText?: string;  
    code?: string;
    isStreaming?: boolean;
    designProposal?: DesignProposal;
    language?: string;
    task?: string;
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
    isTemporary?: boolean;
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
        
        // 先清理所有空的临时对话（确保启动时干净）
        this._cleanupAllTemporaryConversations();
        
        // 如果有历史对话，不自动加载，只是存储起来
        // 启动时总是创建一个新的临时对话（带欢迎消息）
        this._createTemporaryConversation();
        
        // 如果有历史对话，历史列表会保留，但当前显示的是临时对话
        this._updateConversationList();
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
                    await this._handleUserMessage(data.text, data.files, data.language || 'Python', data.task || 'full');
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
                    this._deleteConversation(data.conversationId);
                    break;
                }
            }
        });

        this._addSystemMessage('👋 欢迎使用 Software Engineering Agent！\n\n我支持以下功能：\n📐 分析+设计（类图、活动图、状态机图）\n💻 实现+测试（代码生成、单元测试）\n🔧 调试+修复（错误定位、代码修复）\n\n请告诉我你的需求。');
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

    private _createTemporaryConversation(): string {
        const id = `temp_${Date.now()}`;
        const tempConv: Conversation = {
            id: id,
            title: '新对话',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            isTemporary: true  // 标记为临时对话
        };
        
        // 临时对话不保存到 _conversations 中
        this._currentConversationId = id;
        this._messages = [];
        
        this._view?.webview.postMessage({ type: 'clearMessages' });
        this._addSystemMessage('👋 欢迎使用 Software Engineering Agent！\n\n我支持以下功能：\n📐 分析+设计（类图、活动图、状态机图）\n💻 实现+测试（代码生成、单元测试）\n🔧 调试+修复（错误定位、代码修复）\n\n请告诉我你的需求。');
        
        return id;
    }

    private _cleanupAllTemporaryConversations() {
        // 清理所有临时对话（从存储中删除）
        const beforeCount = this._conversations.length;
        this._conversations = this._conversations.filter(c => !c.isTemporary);
        if (beforeCount !== this._conversations.length) {
            this._saveConversations();
        }
    }

    private _createNewConversation(shouldSave: boolean = true): string {
        const id = Date.now().toString();
        const newConv: Conversation = {
            id: id,
            title: '新对话',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            isTemporary: false  // 明确标记为非临时
        };
        
        if (shouldSave) {
            this._conversations.unshift(newConv);
            this._saveConversations();
        }
        
        this._currentConversationId = id;
        this._messages = [];
        
        this._updateConversationList();
        this._view?.webview.postMessage({ type: 'clearMessages' });
        this._addSystemMessage('👋 欢迎使用 Software Engineering Agent！\n\n我支持以下功能：\n📐 分析+设计（类图、活动图、状态机图）\n💻 实现+测试（代码生成、单元测试）\n🔧 调试+修复（错误定位、代码修复）\n\n请告诉我你的需求。');
        
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
        // 如果要切换的对话不是当前临时对话，且当前有临时对话存在，则删除临时对话（不保存）
        const currentIsTemporary = !this._conversations.find(c => c.id === this._currentConversationId);
        
        if (currentIsTemporary && id !== this._currentConversationId) {
            // 当前是临时对话，切换到其他对话时，临时对话直接丢弃
            // 不需要保存，直接忽略
            console.log('Discarding temporary conversation');
        }
        
        const conv = this._conversations.find(c => c.id === id);
        if (conv) {
            this._currentConversationId = id;
            this._messages = conv.messages;

            this._view?.webview.postMessage({
                type: 'loadConversation',
                messages: conv.messages.map(m => ({ role: m.role, content: m.displayText || m.content }))
            });

            this._updateConversationList();
        }
        
        // 如果切换后没有对话了，创建一个新的临时对话
        if (this._conversations.length === 0) {
            this._createTemporaryConversation();
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

    private _updateConversationList() {
        const permanentConversations = this._conversations.filter(c => !c.isTemporary);
        
        this._view?.webview.postMessage({
            type: 'updateConversationList',
            conversations: permanentConversations.map(c => ({
                id: c.id,
                title: c.title,
                isCurrent: c.id === this._currentConversationId
            }))
        });
    }

    private _sendDesignToWebview(proposal: DesignProposal) {
        this._view?.webview.postMessage({
            type: 'renderDesign', // 与 chat.js 中的 case 对应
            designProposal: proposal
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
            const lastUserMsg = [...this._messages].reverse().find(m => m.role === 'user');
            // 模拟全新指令投递
            await this._handleUserMessage(text, undefined, lastUserMsg?.language || 'Python', lastUserMsg?.task || 'full');
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
            await this._streamResponse(
                lastUserMessage.content, 
                lastUserMessage.language || 'Python', 
                lastUserMessage.task || 'full'
            );
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
                    <h3>🤖 Software Engineering Agent</h3>
                    </div>
                <div class="messages-container" id="messagesContainer">
                    <div class="welcome-message">
                        <div class="assistant-message">
                            <div class="message-content">👋 欢迎使用 Software Engineering Agent！</div>
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

    private async _handleUserMessage(text: string, files?: { name: string; content: string }[], language: string = 'Python', task: string = 'full') {
        if (!text.trim() && (!files || files.length === 0)) return;

        // 1. 先确定对话是否正式（临时转正式）
        const isTemporary = !this._conversations.find(c => c.id === this._currentConversationId);
        let isFirstMessage = false;  // 标记是否是第一条消息
        
        if (isTemporary) {
            // 临时对话转正式，这是第一条消息
            isFirstMessage = true;
            const newId = Date.now().toString();
            const newConv: Conversation = {
                id: newId,
                title: '新对话',  // 临时标题，马上会更新
                messages: [],
                createdAt: new Date(),
                updatedAt: new Date(),
                isTemporary: false
            };
            this._conversations.unshift(newConv);
            this._currentConversationId = newId;
            this._messages = [];
            this._saveConversations();
            this._updateConversationList();
        } else {
            // 已有正式对话，检查是否为空对话（没有消息）
            const existingConv = this._conversations.find(c => c.id === this._currentConversationId);
            if (existingConv && existingConv.messages.length === 0) {
                isFirstMessage = true;
            }
        }

        // 2. 构建用户消息内容
        let fullRequirement = text || '';
        let displayTitle = text || '';
        let displayText = text || '';

        if (files && files.length > 0) {
            const filesText = files.map(f => `[文件: ${f.name}]\n\`\`\`\n${f.content}\n\`\`\``).join('\n\n');
            fullRequirement = `${text ? text + '\n\n' : ''}${filesText}`;
            const fileBadges = files.map(f => `📎 [已附加文件上下文: ${f.name}]`).join(' ');
            displayText = `${text ? text + '\n\n' : ''}${fileBadges}`;
            if (!displayTitle) displayTitle = `文件分析 (${files.length}个文件)`;
        }

        // 3. 创建用户消息
        const userMessage: Message = { 
            role: 'user', 
            content: fullRequirement,
            displayText: displayText,
            language: language,
            task: task
        };
        this._messages.push(userMessage);

        // 4. 更新对话对象的消息数组
        let conv = this._conversations.find(c => c.id === this._currentConversationId);
        if (conv) {
            conv.messages = this._messages;
            conv.updatedAt = new Date();
            
            // 5. 更新标题（第一条消息）
            if (isFirstMessage) {
                const rawTitle = text.trim();
                if (rawTitle.length > 0) {
                    let title = rawTitle.length > 15 ? rawTitle.substring(0, 15) + '...' : rawTitle;
                    conv.title = title;
                } else if (files && files.length > 0) {
                    conv.title = `文件分析 (${files.length}个文件)`;
                } else {
                    conv.title = '新对话';
                }
                this._saveConversations();
                this._updateConversationList();
            } else {
                this._saveConversations();
            }
        }

        // 6. 发送到前端
        this._view?.webview.postMessage({
            type: 'addMessage',
            message: { role: userMessage.role, content: displayText }
        });

        // 7. 调用后端
        await this._streamResponse(fullRequirement, language, task);
    }

    private async _streamResponse(requirement: string, language: string, task: string) {
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
                body: JSON.stringify({ requirement, history, language: language, task: task }),
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

                let isDesignMode = task === 'design';  // 标记是否为设计模式
                let designProcessed = false;           // 标记设计是否已处理

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

                                designProcessed = true; // 新增
                            } else if (parsed.type === 'code_chunk') {
                                if (!isDesignMode) {
                                    fullContent += parsed.content;
                                    this._updateStreamingMessage(messageId, fullContent, parsed.isCode, language);
                                }
                            } else if (parsed.type === 'complete') {
                                assistantMessage.content = fullContent;
                                assistantMessage.isStreaming = false;
                                if (parsed.code) {
                                    assistantMessage.code = parsed.code;
                                }
                                // 设计模式下不调用 finalize，因为已经通过 showDesignProposal 显示了
                                if (!isDesignMode) {
                                    this._finalizeStreamingMessage(messageId, fullContent, language);
                                } else {
                                    // 设计模式下只隐藏取消按钮
                                    this._showCancelButton(false);
                                }
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
        const classDiagram = proposal.architecture || '';
        const activityDiagram = proposal.components?.join('\n') || '';
        
        // 生成包含 PlantUML 渲染的 HTML（不包含确认/重新设计按钮）
        const proposalHtml = `
            <div class="design-proposal">
                <div class="proposal-title">📐 ${this._escapeHtml(proposal.title)}</div>
                <div class="proposal-description">${this._escapeHtml(proposal.description)}</div>
                
                ${classDiagram ? `
                <div class="proposal-architecture">
                    <strong>类图 (Class Diagram):</strong>
                    <div class="plantuml-container">
                        <pre class="plantuml-code"><code>${this._escapeHtml(classDiagram)}</code></pre>
                        <div class="plantuml-render"></div>
                    </div>
                </div>` : ''}
                
                ${activityDiagram ? `
                <div class="proposal-components">
                    <strong>活动图 (Activity Diagram):</strong>
                    <div class="plantuml-container">
                        <pre class="plantuml-code"><code>${this._escapeHtml(activityDiagram)}</code></pre>
                        <div class="plantuml-render"></div>
                    </div>
                </div>` : ''}
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
                const lastUserMsg = [...this._messages].reverse().find(m => m.role === 'user');
                await this._streamResponse(
                    `修改设计方案：${feedback}\n原需求：${this._messages[this._messages.length - 2]?.content}`,
                    lastUserMsg?.language || 'Python',
                    lastUserMsg?.task || 'full'
                );
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
            await this._streamResponse(
                lastUserMessage.content, 
                lastUserMessage.language || 'Python', 
                lastUserMessage.task || 'full'
            );
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

    private _updateStreamingMessage(id: string, content: string, isCode: boolean = false, language: string = 'Python') {
        this._view?.webview.postMessage({
            type: 'updateStreamingMessage',
            id,
            content,
            isCode,
            language
        });
    }

    private _finalizeStreamingMessage(id: string, content: string, language: string = 'Python') {
        const assistantMessage: Message = { role: 'assistant', content: content };
        const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
        if (currentConv) {
            currentConv.updatedAt = new Date();
            this._saveConversations();
        }

        this._view?.webview.postMessage({
            type: 'finalizeStreamingMessage',
            id,
            content,
            language
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