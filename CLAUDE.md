# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for collecting WeChat articles using the wxdown.online API service and LangGraph workflows. The project automatically searches for WeChat public accounts, fetches articles, filters them based on user conditions, uses LLM to parse articles into short news, and exports results to Excel.

## Dependencies and Environment

- Python >=3.12 required
- Dependencies managed via uv (see pyproject.toml)
- Main dependencies: `requests`, `langgraph`, `langchain`, `langchain-openai`, `openpyxl`, `pandas`, `beautifulsoup4`, `python-dotenv`
- Requires environment variables configured in `.env` file:
  - `OPENAI_API_KEY`: Required for LLM functionality
  - `OPENAI_BASE_URL`: Optional custom API base URL

## Commands

Since this project uses uv for dependency management:

```bash
# Install dependencies
uv sync

# Run the main interactive application
uv run python main.py

# Run workflow directly
uv run python workflow.py
```

## Code Architecture

### Core Workflow (`workflow.py`)
- Uses LangGraph to orchestrate the entire process
- StateGraph manages workflow state transitions
- Main flow: extract keyword → get account → fetch articles → parse conditions → filter → LLM parse → export Excel

### State Management (`workflow_state.py`)
- `WorkflowState`: Main state container with all workflow data
- `ArticleInfo`: Article metadata structure
- `ShortNews`: Parsed short news structure  
- `FilterConditions`: User filtering criteria

### Workflow Nodes
- `workflow_nodes.py`: Basic processing nodes (account search, article fetching, filtering)
- `llm_nodes.py`: LLM-powered article parsing using OpenAI
- `export_nodes.py`: Excel export and error handling

### API Integration (`api_request.py`)
- `get_account_info(keyword)`: Search WeChat accounts by keyword
- `get_articles(fake_id, begin, size)`: Fetch articles with pagination
- Uses Authorization header with API token

### API Response Formats
**Account Info API Response:**
```json
{
  "base_resp": {"ret": 0, "err_msg": "ok"},
  "total": 2,
  "list": [
    {
      "fakeid": "MzA3NzAyMzMyMA==",
      "nickname": "铁路12306",
      "alias": "CRTT12306",
      "signature": "公众号简介",
      "verify_status": 2
    }
  ]
}
```

**Article List API Response:**
```json
{
  "base_resp": {"ret": 0, "err_msg": "ok"},
  "articles": [
    {
      "aid": "2247503214_1",
      "title": "我用ChatGPT AI Agent做了一个堆栈模拟器！",
      "link": "https://mp.weixin.qq.com/s/wZxawrdSdSUAAZc89XuhWg",
      "update_time": 1753666492,
      "create_time": 1753666493,
      "author_name": "轩辕之风"
    }
  ]
}
```

**Field Mapping Notes:**
- Account API: `list` contains accounts, each with `fakeid` and `nickname`
- Articles API: `articles` contains articles, use `update_time` as primary time field
- No separate `content_url` field in articles API, use `link` for both link and content_url

The workflow processes natural language requests like "查询银行科技研究社的文章，筛选最近20篇，标题包含人工智能" and automatically executes the full pipeline from search to Excel export.