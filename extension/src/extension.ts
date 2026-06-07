// software-agent/extension/src/extension.ts
import * as vscode from 'vscode';
import { ChatPanelProvider } from './chatPanel';

export function activate(context: vscode.ExtensionContext) {
    console.log('插件 "agent-ui" 已激活');

    // 注册 WebView 侧边栏提供者
    const chatPanelProvider = new ChatPanelProvider(context.extensionUri, context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            ChatPanelProvider.viewType,
            chatPanelProvider
        )
    );

    // 注册传统命令（保留向后兼容）
    const generateCommand = vscode.commands.registerCommand('agent-ui.generateCode', async () => {
        // 打开侧边栏
        await vscode.commands.executeCommand('agent-ui.chatView.focus');
        
        // 可选：显示输入框让用户快速输入
        const requirement = await vscode.window.showInputBox({
            prompt: '请输入你的需求',
            placeHolder: '例如：写一个加法函数',
            title: '智能体需求输入'
        });
        
        if (requirement) {
            // 这里需要将消息发送到 ChatPanel
            // 可以通过 context 传递，或者使用全局事件
            vscode.commands.executeCommand('agent-ui.sendToChat', requirement);
        }
    });

    // 注册发送到聊天的命令
    const sendToChatCommand = vscode.commands.registerCommand('agent-ui.sendToChat', (message: string) => {
        // 通过全局状态或事件发送消息
        // 这里可以扩展实现
        vscode.window.showInformationMessage(`发送消息: ${message}`);
    });

    context.subscriptions.push(generateCommand, sendToChatCommand);
}

export function deactivate() {}