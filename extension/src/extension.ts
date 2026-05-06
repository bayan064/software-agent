// extension.ts
import * as vscode from 'vscode';
import * as axios from 'axios';

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

        try {
            // 2. 调用你的后端API
            const response = await axios.default.post('http://127.0.0.1:8000/generate', {
                requirement: requirement
            });

            const code = response.data.code;
            const testCode = response.data.test_code;
            const testResult = response.data.test_result;

            // 3. 创建一个新文件显示生成的代码
            const doc = await vscode.workspace.openTextDocument({
                content: code,
                language: 'python'
            });
            await vscode.window.showTextDocument(doc);

            // 4. 显示测试结果
            if (testResult.failed === 0) {
                vscode.window.showInformationMessage(`✅ 测试通过！共 ${testResult.passed} 个测试用例全部通过`);
            } else {
                vscode.window.showWarningMessage(`❌ 测试失败：${testResult.failed} 个失败`);
            }

        } catch (error) {
            vscode.window.showErrorMessage(`调用智能体失败：${error}`);
            console.error(error);
        }
    });

    context.subscriptions.push(generateCommand);
}

export function deactivate() {}
