from langgraph.graph import StateGraph, END
from workflow_state import WorkflowState
from llm_extraction_nodes import (  # 使用新的LLM提取节点
    llm_extract_account_keyword_node,
    llm_parse_filter_conditions_node
)
from workflow_nodes import (
    get_account_info_node,
    fetch_articles_with_smart_filtering_node
)
from llm_nodes import parse_articles_with_llm_node
from export_nodes import export_to_excel_node, should_continue, error_handler_node


def create_workflow():
    """创建LangGraph工作流"""
    
    # 创建状态图
    workflow = StateGraph(WorkflowState)
    
    # 添加节点 - 使用新的LLM提取节点
    workflow.add_node("llm_extract_keyword", llm_extract_account_keyword_node)  # LLM提取关键词
    workflow.add_node("get_account_info", get_account_info_node)
    workflow.add_node("llm_parse_conditions", llm_parse_filter_conditions_node)  # LLM解析条件
    workflow.add_node("smart_fetch_and_filter", fetch_articles_with_smart_filtering_node)
    workflow.add_node("parse_with_llm", parse_articles_with_llm_node)
    workflow.add_node("export_excel", export_to_excel_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # 设置入口点
    workflow.set_entry_point("llm_extract_keyword")
    
    # 添加边 - 使用新的节点名称
    workflow.add_edge("llm_extract_keyword", "get_account_info")
    workflow.add_edge("get_account_info", "llm_parse_conditions")
    workflow.add_edge("llm_parse_conditions", "smart_fetch_and_filter")
    workflow.add_edge("smart_fetch_and_filter", "parse_with_llm")
    workflow.add_edge("parse_with_llm", "export_excel")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "export_excel",
        should_continue,
        {
            "continue": END,
            "error": "error_handler"
        }
    )
    
    workflow.add_edge("error_handler", END)
    
    # 编译工作流
    app = workflow.compile()
    mermaid_code = app.get_graph().draw_mermaid()
    print(mermaid_code)
    
    return app


def run_workflow(user_input: str):
    """运行工作流"""
    print("=== 开始执行微信文章收集工作流 (使用LLM智能理解) ===")
    print(f"用户输入: {user_input}")
    
    # 创建工作流
    app = create_workflow()
    
    # 初始状态
    initial_state = WorkflowState(
        user_input=user_input,
        account_keyword="",
        account_info=None,
        fake_id=None,
        all_articles=[],
        filter_conditions={},
        filtered_articles=[],
        short_news_list=[],
        excel_file_path=None,
        error_message=None
    )
    
    try:
        # 执行工作流
        result = app.invoke(initial_state)
        
        # 打印结果
        print("\n=== 工作流执行完成 ===")
        if result.get("error_message"):
            print(f"执行失败: {result['error_message']}")
        else:
            print(f"✅ 成功处理公众号: {result.get('account_keyword', 'Unknown')}")
            print(f"📊 获取文章数量: {len(result.get('all_articles', []))}")
            print(f"🔍 筛选后文章数量: {len(result.get('filtered_articles', []))}")
            print(f"📰 提取短新闻数量: {len(result.get('short_news_list', []))}")
            if result.get("excel_file_path"):
                print(f"📁 Excel文件路径: {result['excel_file_path']}")
        
        return result
        
    except Exception as e:
        print(f"工作流执行异常: {str(e)}")
        return {"error_message": str(e)}


if __name__ == "__main__":
    # 示例使用 - 测试各种复杂的自然语言输入
    test_inputs = [
        "请查询银行科技研究社的文章，筛选最近的5篇文章，标题包含'一周观察'",
        "我想看科技日报关于人工智能的报道，要最新的10篇",
        "帮我收集创业邦发布的包含区块链内容的文章，数量不超过15篇",
        "搜索腾讯研究院的数字化转型相关文章"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{'='*60}")
        print(f"测试案例 {i}")
        print(f"{'='*60}")
        result = run_workflow(user_input)