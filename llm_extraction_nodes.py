import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

from workflow_state import WorkflowState, FilterConditions
from config import get_env_var
from datetime import datetime
from dateutil import parser as date_parser


def create_llm():
    """创建LLM实例"""
    try:
        llm_config = {
            "model": get_env_var("OPENAI_MODEL", "gpt-3.5-turbo"),
            "temperature": 0,
            "api_key": get_env_var("OPENAI_API_KEY")
        }
        
        base_url = get_env_var("OPENAI_BASE_URL")
        if base_url:
            llm_config["base_url"] = base_url
            
        return ChatOpenAI(**llm_config)
    except Exception as e:
        print(f"[ERROR] 创建LLM失败: {str(e)}")
        return None


def llm_extract_account_keyword_node(state: WorkflowState) -> WorkflowState:
    """使用LLM提取公众号关键词"""
    user_input = state["user_input"]
    print(f"[DEBUG] 使用LLM提取关键词，输入: {user_input}")
    
    llm = create_llm()
    if not llm:
        # 回退到正则表达式方法
        return regex_extract_account_keyword(state)
    
    prompt = f"""
请分析以下用户输入，提取其中的微信公众号名称或关键词。

用户输入："{user_input}"

请按照以下JSON格式返回结果：
{{
    "account_keyword": "提取到的公众号名称或关键词",
    "confidence": "high/medium/low",
    "reasoning": "提取的理由说明"
}}

提取规则：
1. 优先提取明确的公众号名称（如"银行科技研究社"、"科技日报"等）
2. 如果没有明确名称，提取相关的关键词
3. 如果完全无法提取，返回空字符串
4. 保持原始的中文名称，不要翻译

示例：
- "请查询银行科技研究社的文章" → "银行科技研究社"
- "搜索科技相关的公众号文章" → "科技"
- "查找AI相关内容" → "AI"
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = json.loads(response.content)
        
        account_keyword = result.get("account_keyword", "").strip()
        confidence = result.get("confidence", "medium")
        reasoning = result.get("reasoning", "")
        
        print(f"[DEBUG] LLM提取结果: 关键词='{account_keyword}', 置信度={confidence}")
        print(f"[DEBUG] 提取理由: {reasoning}")
        
        if not account_keyword:
            print("[WARNING] LLM未能提取到关键词，尝试回退到正则方法")
            return regex_extract_account_keyword(state)
        
        state["account_keyword"] = account_keyword
        return state
        
    except Exception as e:
        print(f"[ERROR] LLM提取关键词失败: {str(e)}")
        print("[INFO] 回退到正则表达式方法")
        return regex_extract_account_keyword(state)


def llm_parse_filter_conditions_node(state: WorkflowState) -> WorkflowState:
    """使用LLM解析筛选条件"""
    user_input = state["user_input"]
    print(f"[DEBUG] 使用LLM解析筛选条件，输入: {user_input}")
    
    llm = create_llm()
    if not llm:
        # 回退到正则表达式方法
        return regex_parse_filter_conditions(state)
    
    # 获取当前日期用于相对时间计算
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
请分析以下用户输入，提取其中的文章筛选条件。

用户输入："{user_input}"
当前日期：{current_date}

请按照以下JSON格式返回结果：
{{
    "title_keywords": ["关键词1", "关键词2"],  // 标题中需要包含的关键词，如果没有则为null
    "max_articles": 数字,  // 需要的文章数量，如果没有指定则为null
    "start_date": "YYYY-MM-DD",  // 开始日期，如果没有则为null
    "end_date": "YYYY-MM-DD",  // 结束日期，如果没有则为null
    "time_description": "时间描述",  // 用户的原始时间描述
    "reasoning": "解析理由"
}}

解析规则：
1. 标题关键词：提取"标题包含"、"关键词"、"包含...的文章"等表述
2. 文章数量：提取"20篇"、"最多10个"、"前5篇"等数量表述
3. 时间范围：
   - "最近的" → 从当前日期往前推算
   - "2024年1月" → 转换为具体日期范围
   - "最近30天" → 计算具体日期
   - "一周内" → 计算具体日期
4. 如果用户只说"最近的X篇"，不设置具体时间范围，让系统按发布顺序获取

示例：
输入："请查询银行科技研究社的文章，筛选最近的20篇，标题包含'AI'或'人工智能'"
输出：{{
    "title_keywords": ["AI", "人工智能"],
    "max_articles": 20,
    "start_date": null,
    "end_date": null,
    "time_description": "最近的",
    "reasoning": "用户需要20篇文章，标题包含AI或人工智能，最近发布的文章"
}}
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = json.loads(response.content)
        
        # 转换为FilterConditions格式
        conditions = FilterConditions(
            title_keywords=result.get("title_keywords"),
            max_articles=result.get("max_articles"),
            start_date=None,
            end_date=None
        )
        
        # 处理日期
        start_date_str = result.get("start_date")
        end_date_str = result.get("end_date")
        
        if start_date_str:
            try:
                conditions["start_date"] = datetime.strptime(start_date_str, "%Y-%m-%d")
            except:
                print(f"[WARNING] 无法解析开始日期: {start_date_str}")
        
        if end_date_str:
            try:
                conditions["end_date"] = datetime.strptime(end_date_str, "%Y-%m-%d")
            except:
                print(f"[WARNING] 无法解析结束日期: {end_date_str}")
        
        print(f"[DEBUG] LLM解析条件结果:")
        print(f"  - 标题关键词: {conditions['title_keywords']}")
        print(f"  - 文章数量: {conditions['max_articles']}")
        print(f"  - 开始日期: {conditions['start_date']}")
        print(f"  - 结束日期: {conditions['end_date']}")
        print(f"  - 时间描述: {result.get('time_description', '')}")
        print(f"  - 解析理由: {result.get('reasoning', '')}")
        
        state["filter_conditions"] = conditions
        return state
        
    except Exception as e:
        print(f"[ERROR] LLM解析筛选条件失败: {str(e)}")
        print("[INFO] 回退到正则表达式方法")
        return regex_parse_filter_conditions(state)


def regex_extract_account_keyword(state: WorkflowState) -> WorkflowState:
    """正则表达式回退方法：提取公众号关键词"""
    import re
    
    user_input = state["user_input"]
    print(f"[DEBUG] 使用正则方法提取关键词: {user_input}")
    
    keyword_patterns = [
        r"查询(.+?)的文章",
        r"搜索(.+?)公众号",
        r"公众号：(.+)",
        r"关键词：(.+)",
    ]
    
    account_keyword = ""
    for pattern in keyword_patterns:
        match = re.search(pattern, user_input)
        if match:
            account_keyword = match.group(1).strip()
            print(f"[DEBUG] 正则提取到关键词: {account_keyword}")
            break
    
    if not account_keyword:
        # 尝试提取第一个中文词组
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', user_input)
        if chinese_words:
            account_keyword = chinese_words[0]
            print(f"[DEBUG] 正则提取中文词组: {account_keyword}")
    
    state["account_keyword"] = account_keyword
    return state


def regex_parse_filter_conditions(state: WorkflowState) -> WorkflowState:
    """正则表达式回退方法：解析筛选条件"""
    import re
    
    user_input = state["user_input"]
    print(f"[DEBUG] 使用正则方法解析条件: {user_input}")
    
    conditions = FilterConditions(
        title_keywords=None,
        max_articles=None,
        start_date=None,
        end_date=None
    )
    
    # 提取标题关键词
    keyword_patterns = [
        r"标题包含[：:]?(.+)",
        r"关键词[：:]?(.+)",
        r"包含[：:]?(.+?)的文章",
    ]
    
    for pattern in keyword_patterns:
        match = re.search(pattern, user_input)
        if match:
            keywords = [kw.strip().strip("'\"") for kw in re.split(r'[,，或和]', match.group(1)) if kw.strip()]
            conditions["title_keywords"] = keywords
            break
    
    # 提取文章数量
    count_match = re.search(r"(\d+)篇|最多(\d+)|前(\d+)", user_input)
    if count_match:
        count = int(count_match.group(1) or count_match.group(2) or count_match.group(3))
        conditions["max_articles"] = count
    
    print(f"[DEBUG] 正则解析结果: {conditions}")
    state["filter_conditions"] = conditions
    return state