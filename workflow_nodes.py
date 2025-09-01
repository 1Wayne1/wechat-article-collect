import re
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
from bs4 import BeautifulSoup

from workflow_state import WorkflowState, ArticleInfo, FilterConditions
from api_request import get_account_info, get_articles


def extract_account_keyword_node(state: WorkflowState) -> WorkflowState:
    """从用户输入中提取公众号关键词"""
    user_input = state["user_input"]
    print(f"[DEBUG] 输入: {user_input}")
    
    # 简单提取逻辑，可以根据需要改进
    # 假设用户输入格式类似："请查询银行科技研究社的文章"
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
            print(f"[DEBUG] 通过模式 '{pattern}' 提取到关键词: {account_keyword}")
            break
    
    if not account_keyword:
        # 如果没有匹配到特定模式，尝试提取第一个中文词组
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', user_input)
        if chinese_words:
            account_keyword = chinese_words[0]
            print(f"[DEBUG] 通过中文词组提取到关键词: {account_keyword}")
    
    state["account_keyword"] = account_keyword
    print(f"[DEBUG] 最终关键词: {account_keyword}")
    return state


def get_account_info_node(state: WorkflowState) -> WorkflowState:
    """获取公众号信息"""
    keyword = state["account_keyword"]
    print(f"[DEBUG] 搜索关键词: {keyword}")
    if not keyword:
        state["error_message"] = "未能提取到公众号关键词"
        return state
    
    try:
        account_info = get_account_info(keyword)
        print(f"[DEBUG] API返回结果: {account_info}")
        
        # 根据实际API返回结构解析
        if (account_info and 
            account_info.get("base_resp", {}).get("ret") == 0 and  # 检查返回状态
            account_info.get("list") and 
            len(account_info["list"]) > 0):
            
            # 取第一个匹配的公众号
            first_account = account_info["list"][0]
            state["account_info"] = first_account
            state["fake_id"] = first_account.get("fakeid")  # 注意是 fakeid 不是 fake_id
            
            nickname = first_account.get("nickname", "Unknown")
            fakeid = first_account.get("fakeid", "")
            signature = first_account.get("signature", "")
            
            print(f"[DEBUG] 找到公众号: {nickname}")
            print(f"[DEBUG] fakeid: {fakeid}")
            print(f"[DEBUG] 简介: {signature}")
            
        else:
            error_msg = "未找到匹配的公众号"
            if account_info:
                # 检查是否有错误信息
                base_resp = account_info.get("base_resp", {})
                if base_resp.get("ret") != 0:
                    error_msg = f"API错误: {base_resp.get('err_msg', '未知错误')}"
                elif account_info.get("total", 0) == 0:
                    error_msg = f"未找到关键词为 '{keyword}' 的公众号"
            
            state["error_message"] = error_msg
            
    except Exception as e:
        state["error_message"] = f"获取公众号信息时出错: {str(e)}"
    
    return state


def fetch_articles_with_smart_filtering_node(state: WorkflowState) -> WorkflowState:
    """智能获取文章：根据筛选条件动态获取足够数量的文章，支持时间范围优化"""
    fake_id = state["fake_id"]
    conditions = state.get("filter_conditions", {})
    print(f"[DEBUG] 开始智能获取文章，fake_id: {fake_id}")
    print(f"[DEBUG] 筛选条件: {conditions}")
    
    if not fake_id:
        state["error_message"] = "缺少公众号fake_id"
        return state
    
    # 检查是否有时间范围条件，启用优化策略
    start_date = conditions.get("start_date")
    end_date = conditions.get("end_date")
    has_time_range = start_date or end_date
    
    if has_time_range:
        print(f"[TIME-OPT] 检测到时间范围条件，启用时间优化策略")
        print(f"[TIME-OPT] 时间范围: {start_date} 到 {end_date}")
    
    all_articles = []
    filtered_articles = []
    begin = 0
    size = 20
    max_pages = 50
    target_count = conditions.get("max_articles", 20)
    
    # 时间优化相关变量
    found_in_range = False  # 是否找到过在时间范围内的文章
    api_calls = 0
    
    try:
        for page in range(max_pages):
            api_calls += 1
            # 获取当前页文章
            articles_response = get_articles(fake_id, begin, size)
            print(f"[DEBUG] 第{page + 1}页API返回")
            
            # 检查API返回状态和数据
            if not articles_response:
                print(f"[DEBUG] 第{page + 1}页API返回为空，停止获取")
                break
                
            # 检查API状态
            base_resp = articles_response.get("base_resp", {})
            if base_resp.get("ret") != 0:
                error_msg = f"API错误: {base_resp.get('err_msg', '未知错误')}"
                print(f"[DEBUG] {error_msg}")
                state["error_message"] = error_msg
                return state
            
            # 获取文章列表
            articles_data = articles_response.get("articles", [])
            if not articles_data or len(articles_data) == 0:
                print(f"[DEBUG] 第{page + 1}页文章列表为空，停止获取")
                break
            
            # 转换为标准格式并添加到总列表
            current_page_articles = []
            page_in_range_count = 0
            early_termination = False
            
            for article in articles_data:
                article_info = ArticleInfo(
                    title=article.get("title", ""),
                    publish_time=str(article.get("update_time", article.get("create_time", ""))),
                    link=article.get("link", ""),
                    content_url=article.get("link", ""),
                    fake_id=fake_id
                )
                all_articles.append(article_info)
                current_page_articles.append(article_info)
                
                # 如果有时间范围条件，进行时间优化判断
                if has_time_range:
                    article_time = parse_article_time(article_info["publish_time"])
                    if article_time:
                        # 检查是否在时间范围内
                        in_range = True
                        if start_date and article_time < start_date:
                            # 文章时间早于开始时间
                            if found_in_range:
                                # 如果之前已经找到过在范围内的文章，现在可以提前终止
                                print(f"[TIME-OPT] 🚀 提前终止：文章时间 {article_time.strftime('%Y-%m-%d')} 早于开始时间 {start_date.strftime('%Y-%m-%d')}")
                                early_termination = True
                                break
                            in_range = False
                        elif end_date and article_time > end_date:
                            # 文章时间晚于结束时间，跳过但继续获取
                            print(f"[TIME-OPT] 跳过文章：{article_info['title'][:30]}... (时间晚于结束时间)")
                            in_range = False
                        
                        if in_range:
                            found_in_range = True
                            page_in_range_count += 1
            
            # 如果需要提前终止，跳出循环
            if early_termination:
                print(f"[TIME-OPT] 提前终止获取，节省了 {max_pages - page - 1} 页的API调用")
                break
            
            # 对当前累积的所有文章进行筛选
            filtered_articles = apply_filters(all_articles, conditions)
            
            if has_time_range:
                print(f"[DEBUG] 第{page + 1}页获取 {len(current_page_articles)} 篇，时间范围内 {page_in_range_count} 篇，累计筛选后 {len(filtered_articles)} 篇")
            else:
                print(f"[DEBUG] 第{page + 1}页获取 {len(current_page_articles)} 篇文章，累计 {len(all_articles)} 篇，筛选后 {len(filtered_articles)} 篇")
            
            # 检查是否满足条件
            if is_filtering_complete(filtered_articles, conditions):
                print(f"[DEBUG] 已满足筛选条件，停止获取")
                break
            
            # 如果返回的文章数量少于size，说明已经是最后一页
            if len(articles_data) < size:
                print(f"[DEBUG] 已到最后一页，停止获取")
                break
            
            begin += size
    
    except Exception as e:
        state["error_message"] = f"获取文章列表时出错: {str(e)}"
        return state
    
    # 最终筛选（确保数量限制）
    if conditions.get("max_articles") and len(filtered_articles) > conditions["max_articles"]:
        filtered_articles = filtered_articles[:conditions["max_articles"]]
    
    state["all_articles"] = all_articles
    state["filtered_articles"] = filtered_articles
    
    if has_time_range:
        print(f"[TIME-OPT] 时间优化效果：API调用 {api_calls} 次，最终结果：总文章 {len(all_articles)} 篇，筛选后 {len(filtered_articles)} 篇")
    else:
        print(f"[DEBUG] 最终结果：总文章 {len(all_articles)} 篇，筛选后 {len(filtered_articles)} 篇")
    
    return state


def parse_article_time(time_str: str) -> Optional[datetime]:
    """解析文章时间戳"""
    if not time_str or not time_str.strip():
        return None
    
    try:
        if time_str.isdigit():
            return datetime.fromtimestamp(int(time_str))
        else:
            # 尝试其他日期格式
            from dateutil import parser as date_parser
            return date_parser.parse(time_str)
    except:
        return None


def apply_filters(articles: List[ArticleInfo], conditions: FilterConditions) -> List[ArticleInfo]:
    """应用筛选条件到文章列表"""
    filtered = articles.copy()
    
    # 按标题关键词筛选
    if conditions.get("title_keywords"):
        keywords = conditions["title_keywords"]
        filtered = [
            article for article in filtered
            if any(keyword in article["title"] for keyword in keywords)
        ]
        print(f"[DEBUG] 按关键词 {keywords} 筛选后剩余 {len(filtered)} 篇文章")
    
    # 按时间筛选
    if conditions.get("start_date") or conditions.get("end_date"):
        date_filtered = []
        for article in filtered:
            try:
                publish_time = article["publish_time"]
                if isinstance(publish_time, str):
                    # 尝试解析时间戳或日期字符串
                    if publish_time.isdigit():
                        article_date = datetime.fromtimestamp(int(publish_time))
                    else:
                        article_date = date_parser.parse(publish_time)
                else:
                    continue
                
                if conditions.get("start_date") and article_date < conditions["start_date"]:
                    continue
                if conditions.get("end_date") and article_date > conditions["end_date"]:
                    continue
                
                date_filtered.append(article)
            except:
                # 如果日期解析失败，保留文章
                date_filtered.append(article)
        
        filtered = date_filtered
        print(f"[DEBUG] 按时间筛选后剩余 {len(filtered)} 篇文章")
    
    return filtered


def is_filtering_complete(filtered_articles: List[ArticleInfo], conditions: FilterConditions) -> bool:
    """检查筛选是否已完成（满足用户需求）"""
    target_count = conditions.get("max_articles")
    
    # 如果用户指定了数量要求，检查是否已达到
    if target_count:
        if len(filtered_articles) >= target_count:
            return True
    
    # 如果没有指定数量但有其他条件，继续获取更多文章以确保充分筛选
    # 这里可以设置一个默认的"足够"数量，比如50篇
    if not target_count and len(filtered_articles) >= 50:
        return True
    
    return False


def parse_filter_conditions_node(state: WorkflowState) -> WorkflowState:
    """解析用户输入的筛选条件"""
    user_input = state["user_input"]
    
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
            keywords = [kw.strip() for kw in match.group(1).split(",") if kw.strip()]
            conditions["title_keywords"] = keywords
            break
    
    # 提取文章数量限制
    count_match = re.search(r"(\d+)篇|最多(\d+)|前(\d+)", user_input)
    if count_match:
        count = int(count_match.group(1) or count_match.group(2) or count_match.group(3))
        conditions["max_articles"] = count
    
    # 提取时间范围
    date_patterns = [
        r"(\d{4}-\d{1,2}-\d{1,2})",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"最近(\d+)天",
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, user_input)
        for match in matches:
            try:
                if "年" in match and "月" in match and "日" in match:
                    # 处理中文日期格式
                    date_str = match.replace("年", "-").replace("月", "-").replace("日", "")
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    parsed_date = date_parser.parse(match)
                
                if not conditions["start_date"]:
                    conditions["start_date"] = parsed_date
                else:
                    conditions["end_date"] = parsed_date
            except:
                continue
    
    state["filter_conditions"] = conditions
    return state


def filter_articles_node(state: WorkflowState) -> WorkflowState:
    """根据条件筛选文章"""
    all_articles = state["all_articles"]
    conditions = state["filter_conditions"]
    
    print(f"[DEBUG] 开始筛选，原始文章数: {len(all_articles)}")
    print(f"[DEBUG] 筛选条件: {conditions}")
    
    filtered_articles = all_articles.copy()
    
    # 按标题关键词筛选
    if conditions["title_keywords"]:
        keywords = conditions["title_keywords"]
        filtered_articles = [
            article for article in filtered_articles
            if any(keyword in article["title"] for keyword in keywords)
        ]
        print(f"[DEBUG] 按关键词筛选后剩余 {len(filtered_articles)} 篇文章")
    
    # 按时间筛选
    if conditions["start_date"] or conditions["end_date"]:
        date_filtered = []
        for article in filtered_articles:
            try:
                publish_time = article["publish_time"]
                if isinstance(publish_time, str):
                    # 尝试解析时间戳或日期字符串
                    if publish_time.isdigit():
                        article_date = datetime.fromtimestamp(int(publish_time))
                    else:
                        article_date = date_parser.parse(publish_time)
                else:
                    continue
                
                if conditions["start_date"] and article_date < conditions["start_date"]:
                    continue
                if conditions["end_date"] and article_date > conditions["end_date"]:
                    continue
                
                date_filtered.append(article)
            except:
                # 如果日期解析失败，保留文章
                date_filtered.append(article)
        
        filtered_articles = date_filtered
        print(f"[DEBUG] 按时间筛选后剩余 {len(filtered_articles)} 篇文章")
    
    # 按数量限制
    if conditions["max_articles"] and len(filtered_articles) > conditions["max_articles"]:
        filtered_articles = filtered_articles[:conditions["max_articles"]]
        print(f"[DEBUG] 按数量限制后剩余 {len(filtered_articles)} 篇文章")
    
    state["filtered_articles"] = filtered_articles
    print(f"[DEBUG] 最终筛选结果: {len(filtered_articles)} 篇文章")
    return state