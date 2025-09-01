import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

def get_env_var(var_name: str, default_value: str = None) -> str:
    """获取环境变量，优先从 .env 文件中读取"""
    return os.getenv(var_name, default_value)

def check_required_env_vars():
    """检查必需的环境变量是否已设置"""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API密钥"
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not get_env_var(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    return missing_vars

def print_env_config():
    """打印当前环境配置信息"""
    print("=== 环境配置信息 ===")
    print(f"OPENAI_API_KEY: {'已设置' if get_env_var('OPENAI_API_KEY') else '未设置'}")
    print(f"OPENAI_BASE_URL: {get_env_var('OPENAI_BASE_URL', '使用默认值')}")
    print("=" * 20)