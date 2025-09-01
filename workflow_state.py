from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class ArticleInfo(TypedDict):
    title: str
    publish_time: str
    link: str
    content_url: str
    fake_id: str


class ShortNews(TypedDict):
    title: str
    content: str
    original_link: str


class FilterConditions(TypedDict):
    title_keywords: Optional[List[str]]
    max_articles: Optional[int]
    start_date: Optional[datetime]
    end_date: Optional[datetime]


class WorkflowState(TypedDict):
    user_input: str
    account_keyword: str
    account_info: Optional[Dict[str, Any]]
    fake_id: Optional[str]
    all_articles: List[ArticleInfo]
    filter_conditions: FilterConditions
    filtered_articles: List[ArticleInfo]
    short_news_list: List[ShortNews]
    excel_file_path: Optional[str]
    error_message: Optional[str]