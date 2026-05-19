# check_java_env.py
import subprocess
import sys
import re

def check_java():
    """检查 Java 环境"""
    print("检查 Java 环境...")
    
    # 检查 javac
    try:
        result = subprocess.run(['javac', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            # 提取版本号
            version_output = result.stderr.strip()
            print(f"✅ javac: {version_output}")
        else:
            print("❌ javac 未找到，请安装 JDK")
            return False
    except FileNotFoundError:
        print("❌ javac 未找到，请安装 JDK")
        return False
    
    # 检查 java
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            # 提取版本号（避免 f-string 中的反斜杠问题）
            version_output = result.stderr.split()[2].strip('"')
            print(f"✅ java: {version_output}")
        else:
            print("❌ java 未找到")
            return False
    except FileNotFoundError:
        print("❌ java 未找到")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("环境检查")
    print("=" * 50)
    
    if check_java():
        print("\n✅ Java 环境正常，可以运行 Java 测试")
    else:
        print("\n❌ Java 环境配置有问题")
        print("请安装 JDK 11 或更高版本")
        print("下载地址: https://adoptium.net/")
        sys.exit(1)
    
    # 检查 Python 环境
    print(f"\n✅ Python: {sys.version}")
    
    print("\n所有环境检查完成！")