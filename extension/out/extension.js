"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
// extension.ts
const vscode = __importStar(require("vscode"));
function activate(context) {
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
            const response = await fetch('http://10.39.80.54:8000/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ requirement })
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status} ${response.statusText}`);
            }
            const data = (await response.json());
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
                }
                else {
                    vscode.window.showWarningMessage(`❌ 测试失败：${testResult.failed} 个失败`);
                }
            }
            else {
                vscode.window.showInformationMessage('生成完成，但未返回测试结果');
            }
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`调用智能体失败：${message}`);
            console.error(error);
        }
    });
    context.subscriptions.push(generateCommand);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map