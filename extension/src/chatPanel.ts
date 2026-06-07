// software-agent/extension/src/chatPanel.ts
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
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
        // 加载保存的对话
        this._loadConversations();
        // 如果没有对话，创建一个新的
        if (this._conversations.length === 0) {
            this._createNewConversation();
        } else {
            this._currentConversationId = this._conversations[0].id;
            this._messages = this._conversations[0].messages;
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

        // 处理来自 Webview 的消息
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    // 支持多个文件和文本一起发送
                    await this._handleUserMessage(data.text, data.files);
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
                case 'cancelGeneration':
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

        // 显示欢迎消息
        this._addSystemMessage('👋 欢迎使用 Agent UI！\n\n我可以帮助你生成代码、设计方案。请告诉我你的需求，例如：\n\n• "写一个计算器应用"\n• "实现用户登录功能"\n• "创建一个 RESTful API 服务"');
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

    private _createNewConversation(): string {
        const id = Date.now().toString();
        const newConv: Conversation = {
            id: id,
            title: '新对话',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date()
        };
        this._conversations.unshift(newConv);
        this._currentConversationId = id;
        this._messages = newConv.messages;
        this._saveConversations();
        
        // 更新侧边栏显示
        this._updateConversationList();
        return id;
    }

    private _switchConversation(id: string) {
        const conv = this._conversations.find(c => c.id === id);
        if (conv) {
            this._currentConversationId = id;
            this._messages = conv.messages; // 确保引用一致

            // 【核心修改点】：切换对话时，立刻把该对话的历史消息发送给前端 Webview
            this._view?.webview.postMessage({
                type: 'loadConversation',
                messages: conv.messages
            });

            // 同时也更新一下侧边栏列表的高亮状态
            this._updateConversationList();
        }
    }

    private _deleteConversation(conversationId: string) {
        const index = this._conversations.findIndex(c => c.id === conversationId);
        if (index === -1) return;
        
        this._conversations.splice(index, 1);
        
        if (this._conversations.length === 0) {
            this._createNewConversation();
            // 【修改点】：补充清空内存状态与前端视图的动作
            this._messages = [];
            this._view?.webview.postMessage({ type: 'clearMessages' });
        } else if (this._currentConversationId === conversationId) {
            this._switchConversation(this._conversations[0].id);
        }
        
        this._saveConversations();
        this._updateConversationList();
    }

    private _updateConversationTitle(conversationId: string, firstMessage: string) {
        const conv = this._conversations.find(c => c.id === conversationId);
        if (conv && conv.title === '新对话') {
            // 截取前20个字符作为标题
            conv.title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? '...' : '');
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

    private _getHtmlForWebview(webview: vscode.Webview): string {
        // 读取 CSS 和 JS 文件
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
            <style>${cssContent}</style>
            <title>Agent UI Chat</title>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <h3>🤖 Agent UI Assistant</h3>
                    <button id="clearHistoryBtn" class="icon-btn" title="清空历史">🗑️</button>
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
                        <button id="cancelBtn" class="secondary-btn" style="display:none;">取消</button>
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

        // 【修改点】：拼接支持多个文件的内容，并将完整内容直接存入历史
        if (files && files.length > 0) {
            const filesText = files.map(f => `[文件: ${f.name}]\n\`\`\`\n${f.content}\n\`\`\``).join('\n\n');
            fullRequirement = `${text ? text + '\n\n' : ''}${filesText}`;
            if (!displayTitle) displayTitle = `上传了 ${files.length} 个文件`;
        }

        // 把包含文件的 fullRequirement 直接作为 content 存下来，这样历史记录就包含文件了
        const userMessage: Message = { role: 'user', content: fullRequirement };
        this._messages.push(userMessage);

        const currentConv = this._conversations.find(c => c.id === this._currentConversationId);
        
        // 更新对话标题
        if (currentConv && currentConv.messages.length === 1) {
            this._updateConversationTitle(this._currentConversationId, displayTitle || text);
        }

        // 保存消息到对话
        if (currentConv) {
            currentConv.updatedAt = new Date();
            this._saveConversations();
        }

        // 发送给 UI 显示
        this._view?.webview.postMessage({
            type: 'addMessage',
            message: { role: userMessage.role, content: userMessage.content }
        });

        // 开始流式响应
        await this._streamResponse(fullRequirement);
    }

    private async _streamResponse(requirement: string) {
        const config = vscode.workspace.getConfiguration('agent-ui');
        const baseUrl = config.get<string>('baseUrl') ?? 'http://127.0.0.1:8000';
        const endpoint = new URL('/stream', baseUrl).toString();

        this._abortController = new AbortController();
        
        // 创建流式消息占位符
        const assistantMessage: Message = {
            role: 'assistant',
            content: '',
            isStreaming: true
        };
        this._messages.push(assistantMessage);
        const messageId = this._addStreamingMessageToView();

        // 构建历史消息（只发送 user 和 assistant 的消息，不含 system）
        const history = this._messages
            .filter(m => m.role === 'user' || m.role === 'assistant')
            .slice(0, -1) // 不包括刚添加的这条 assistant 消息
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
                            
                            // 处理不同类型的响应
                            if (parsed.type === 'design_proposal') {
                                // 收到设计方案，请求用户确认
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
                                // 流式输出代码
                                fullContent += parsed.content;
                                this._updateStreamingMessage(messageId, fullContent, parsed.isCode);
                            } else if (parsed.type === 'complete') {
                                // 完成
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
                this._updateStreamingMessage(messageId, '\n\n❌ 生成已取消', false);
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
            // 用户确认，继续生成代码
            await this._continueWithDesign(this._pendingDesignProposal);
        } else {
            // 用户拒绝，让用户提供修改意见
            const feedback = await vscode.window.showInputBox({
                prompt: '请说明需要如何修改设计方案',
                placeHolder: '例如：应该使用 MVC 架构，而不是...'
            });
            if (feedback) {
                await this._streamResponse(`修改设计方案：${feedback}\n原需求：${this._messages[this._messages.length - 2]?.content}`);
            }
        }
        this._pendingDesignProposal = undefined;
    }

    private async _continueWithDesign(proposal: DesignProposal) {
        this._addSystemMessage('✅ 设计方案已确认，正在生成代码...');
        
        // 继续流式生成代码
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
            // 如果没有活动编辑器，创建新文件
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
        // 保存 assistant 消息
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