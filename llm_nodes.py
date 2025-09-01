import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import json

from workflow_state import WorkflowState, ShortNews
from config import get_env_var


def parse_articles_with_llm_node(state: WorkflowState) -> WorkflowState:
    """使用LLM解析文章内容，提取短新闻"""
    filtered_articles = state["filtered_articles"]
    if not filtered_articles:
        state["short_news_list"] = []
        return state
    
    # 初始化OpenAI模型，支持自定义base_url
    try:
        llm_config = {
            "model": get_env_var("OPENAI_MODEL", "gpt-3.5-turbo"),
            "temperature": 0,
            "api_key": get_env_var("OPENAI_API_KEY")
        }
        
        # 如果设置了自定义base_url，则使用它
        base_url = get_env_var("OPENAI_BASE_URL")
        if base_url:
            llm_config["base_url"] = base_url
            
        llm = ChatOpenAI(**llm_config)
    except Exception as e:
        state["error_message"] = f"初始化LLM时出错: {str(e)}"
        return state
    
    all_short_news = []
    
    for i, article in enumerate(filtered_articles):
        print(f"正在处理第 {i+1}/{len(filtered_articles)} 篇文章: {article['title']}")
        
        try:
            # 获取文章内容
            article_content = fetch_article_content(article["content_url"] or article["link"])
            if not article_content:
                print(f"无法获取文章内容: {article['title']}")
                continue
            
            # 使用LLM解析文章
            prompt = f"""
请分析以下微信公众号文章，将其拆分为多个独立的短新闻。每个短新闻应该包含完整的信息，可以独立阅读理解。

文章标题: {article['title']}
文章内容: {article_content[:4000]}...

请按照以下JSON格式返回结果：
{{
    "short_news": [
        {{
            "title": "短新闻标题",
            "content": "短新闻的完整内容"
        }},
        ...
    ]
}}

要求：
1. 每个短新闻都应该是独立完整的
2. 标题简洁明了
3. 内容包含关键信息
4. 如果文章本身就是一个整体，可以作为一个短新闻
"""
            
            response = llm.invoke([HumanMessage(content=prompt)])
            
            # 解析LLM返回的JSON
            try:
                result = json.loads(response.content)
                short_news_data = result.get("short_news", [])
                
                for news in short_news_data:
                    short_news = ShortNews(
                        title=news.get("title", ""),
                        content=news.get("content", ""),
                        original_link=article["link"]
                    )
                    all_short_news.append(short_news)
                    
                print(f"从文章中提取到 {len(short_news_data)} 条短新闻")
                
            except json.JSONDecodeError:
                # 如果JSON解析失败，将整篇文章作为一个短新闻
                short_news = ShortNews(
                    title=article["title"],
                    content=article_content[:1000] + "...",
                    original_link=article["link"]
                )
                all_short_news.append(short_news)
                print("JSON解析失败，将整篇文章作为一个短新闻")
                
        except Exception as e:
            print(f"处理文章时出错 {article['title']}: {str(e)}")
            continue
    
    state["short_news_list"] = all_short_news
    print(f"总共提取到 {len(all_short_news)} 条短新闻")
    return state


def fetch_article_content(url: str) -> str:
    """获取文章内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 尝试找到文章内容区域
        content_selectors = [
            '.rich_media_content',
            '#js_content', 
            '.weui-article__bd',
            'article',
            '.content'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                break
        
        if not content:
            # 如果找不到特定区域，提取body中的文本
            body = soup.find('body')
            if body:
                content = body.get_text(strip=True)
        
        return content
        
    except Exception as e:
        print(f"获取文章内容失败: {str(e)}")
        return ""