import pandas as pd
from datetime import datetime
import os

from workflow_state import WorkflowState


def export_to_excel_node(state: WorkflowState) -> WorkflowState:
    """将短新闻列表导出到Excel文件"""
    short_news_list = state["short_news_list"]
    print(f"[DEBUG] 准备导出，短新闻数量: {len(short_news_list)}")
    
    if not short_news_list:
        # 如果没有短新闻数据，尝试直接导出文章列表
        filtered_articles = state.get("filtered_articles", [])
        print(f"[DEBUG] 没有短新闻，尝试导出原文章，文章数量: {len(filtered_articles)}")
        
        if not filtered_articles:
            state["error_message"] = "没有找到符合条件的文章可以导出"
            return state
        
        # 将文章转换为简单格式导出
        excel_data = []
        for i, article in enumerate(filtered_articles, 1):
            excel_data.append({
                "序号": i,
                "文章标题": article["title"],
                "发布时间": article["publish_time"],
                "文章链接": article["link"],
                "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(excel_data)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            account_keyword = state.get("account_keyword", "unknown")
            filename = f"wechat_articles_{account_keyword}_{timestamp}.xlsx"
            
            # 确保输出目录存在
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            excel_path = os.path.join(output_dir, filename)
            
            # 导出Excel文件
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="文章列表", index=False)
                
                # 设置列宽
                worksheet = writer.sheets["文章列表"]
                column_widths = {
                    'A': 10,  # 序号
                    'B': 50,  # 文章标题
                    'C': 20,  # 发布时间
                    'D': 50,  # 文章链接
                    'E': 20   # 创建时间
                }
                
                for column, width in column_widths.items():
                    worksheet.column_dimensions[column].width = width
            
            state["excel_file_path"] = excel_path
            print(f"Excel文件已保存到: {excel_path}")
            print(f"共导出 {len(filtered_articles)} 篇文章（注：由于LLM解析失败，直接导出了原文章列表）")
            
        except Exception as e:
            state["error_message"] = f"导出Excel文件时出错: {str(e)}"
        
        return state
    
    try:
        # 准备Excel数据
        excel_data = []
        for i, news in enumerate(short_news_list, 1):
            excel_data.append({
                "序号": i,
                "短新闻标题": news["title"],
                "完整内容": news["content"],
                "原始文章链接": news["original_link"],
                "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 创建DataFrame
        df = pd.DataFrame(excel_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        account_keyword = state.get("account_keyword", "unknown")
        filename = f"wechat_articles_{account_keyword}_{timestamp}.xlsx"
        
        # 确保输出目录存在
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        excel_path = os.path.join(output_dir, filename)
        
        # 导出Excel文件
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="短新闻列表", index=False)
            
            # 设置列宽
            worksheet = writer.sheets["短新闻列表"]
            column_widths = {
                'A': 10,  # 序号
                'B': 40,  # 短新闻标题
                'C': 80,  # 完整内容
                'D': 50,  # 原始文章链接
                'E': 20   # 创建时间
            }
            
            for column, width in column_widths.items():
                worksheet.column_dimensions[column].width = width
        
        state["excel_file_path"] = excel_path
        print(f"Excel文件已保存到: {excel_path}")
        print(f"共导出 {len(short_news_list)} 条短新闻")
        
    except Exception as e:
        state["error_message"] = f"导出Excel文件时出错: {str(e)}"
    
    return state


def should_continue(state: WorkflowState) -> str:
    """决定工作流是否继续"""
    print(f"[DEBUG] 检查工作流状态...")
    print(f"[DEBUG] error_message: {state.get('error_message')}")
    print(f"[DEBUG] fake_id: {state.get('fake_id')}")
    print(f"[DEBUG] all_articles count: {len(state.get('all_articles', []))}")
    print(f"[DEBUG] filtered_articles count: {len(state.get('filtered_articles', []))}")
    print(f"[DEBUG] short_news_list count: {len(state.get('short_news_list', []))}")
    
    if state.get("error_message"):
        return "error"
    
    # 如果没有筛选出任何文章，也应该继续到导出节点，让导出节点处理空数据
    return "continue"


def error_handler_node(state: WorkflowState) -> WorkflowState:
    """错误处理节点"""
    error_msg = state.get("error_message", "未知错误")
    print(f"工作流执行出错: {error_msg}")
    return state