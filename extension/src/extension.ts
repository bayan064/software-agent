// extension.ts
import * as vscode from 'vscode';
type GenerateResponse = {
    code: string;
    test_code: string;
    test_result?: {
        passed: number;
        failed: number;
    };
};

export function activate(context: vscode.ExtensionContext) {
    console.log('插件 "agent-ui" 已激活');

    // 注册一个命令：点击按钮时调用智能体
    const generateCommand = vscode.commands.registerCommand('agent-ui.generateCode', async () => {
        // 1. 让用户输入需求
        const requirement = await vscode.window.showInputBox({
            prompt: '请输入你的需求',
            placeHolder: '例如：写一个加法函数，输入两个数字返回它们的和',
            title: '智能体需求输入'
        });

        if (!requirement) {
            vscode.window.showWarningMessage('未输入需求');
            return;
        }

        vscode.window.showInformationMessage('正在生成代码，请稍候...');

        const config = vscode.workspace.getConfiguration('agent-ui');
        const baseUrl = config.get<string>('baseUrl') ?? 'http://127.0.0.1:8000';
        const timeoutMs = config.get<number>('timeoutMs') ?? 15000;
        const endpoint = new URL('/generate', baseUrl).toString();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            // 2. 调用你的后端API
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ requirement }),
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status} ${response.statusText}`);
            }

            const data = (await response.json()) as GenerateResponse;
            const code = data.code;
            const testCode = data.test_code;
            const testResult = data.test_result;

            // 3. 创建一个新文件显示生成的代码
            const doc = await vscode.workspace.openTextDocument({
                content: code,
                language: 'python'
            });
            await vscode.window.showTextDocument(doc);

            // 4. 显示测试结果
            if (testResult) {
                if (testResult.failed === 0) {
                    vscode.window.showInformationMessage(`✅ 测试通过！共 ${testResult.passed} 个测试用例全部通过`);
                } else {
                    vscode.window.showWarningMessage(`❌ 测试失败：${testResult.failed} 个失败`);
                }
            } else {
                vscode.window.showInformationMessage('生成完成，但未返回测试结果');
            }

        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            const cause = error instanceof Error ? (error as { cause?: unknown }).cause : undefined;
            const causeMessage = cause instanceof Error ? cause.message : cause ? String(cause) : '';
            const detail = causeMessage ? ` (${causeMessage})` : '';
            const timeoutNote = message === 'This operation was aborted' ? ` (timeout ${timeoutMs}ms)` : '';
            vscode.window.showErrorMessage(`调用智能体失败：${message}${detail}${timeoutNote}`);
            console.error('agent-ui fetch failed', { message, cause, timeoutMs, endpoint });
        } finally {
            clearTimeout(timeoutId);
        }
    });

    context.subscriptions.push(generateCommand);
}

export function deactivate() { }
