from workflow import run_workflow
from config import check_required_env_vars, print_env_config


def main():
    """主函数，提供用户交互界面"""
    print("=== 微信公众号文章收集工具 ===")
    print("使用说明：")
    print("1. 输入包含公众号名称的查询请求")
    print("2. 可以添加筛选条件，如：标题关键词、文章数量、时间范围等")
    print("3. 工具会自动获取、筛选、解析文章并导出到Excel文件")
    print("\n示例输入：")
    print("- '请查询银行科技研究社的文章，筛选最近的20篇'")
    print("- '搜索科技日报公众号，标题包含人工智能的文章，最多10篇'")
    print("- '查询创业邦的文章，2024年1月1日到2024年3月31日的文章'")
    print("\n配置文件：.env")
    print("=" * 50)
    
    # 打印环境配置信息
    print_env_config()
    
    # 检查必需的环境变量
    missing_vars = check_required_env_vars()
    if missing_vars:
        print("❌ 缺少以下必需的环境变量：")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请在 .env 文件中设置这些环境变量，例如：")
        print("OPENAI_API_KEY=your-openai-api-key")
        print("OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，使用自定义API地址")
        print("\n是否继续运行？LLM功能可能无法正常工作。")
        choice = input("继续？(y/n): ").strip().lower()
        if choice != 'y':
            return
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n请输入您的查询请求（输入 'quit' 退出）：").strip()
            
            if not user_input:
                print("请输入有效的查询请求")
                continue
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("感谢使用！")
                break
            
            # 执行工作流
            print(f"\n开始处理请求: {user_input}")
            result = run_workflow(user_input)
            
            # 显示结果总结
            if result.get("error_message"):
                print(f"\n❌ 处理失败: {result['error_message']}")
            else:
                print(f"\n✅ 处理完成！")
                if result.get("excel_file_path"):
                    print(f"📁 结果已保存到: {result['excel_file_path']}")
                
                # 显示统计信息
                stats = []
                if result.get("account_info"):
                    account_name = result["account_info"].get("nick_name", "Unknown")
                    stats.append(f"公众号: {account_name}")
                
                if result.get("all_articles"):
                    stats.append(f"总文章数: {len(result['all_articles'])}")
                
                if result.get("filtered_articles"):
                    stats.append(f"筛选后: {len(result['filtered_articles'])}")
                
                if result.get("short_news_list"):
                    stats.append(f"短新闻数: {len(result['short_news_list'])}")
                
                if stats:
                    print(f"📊 统计信息: {' | '.join(stats)}")
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 程序出错: {str(e)}")


if __name__ == "__main__":
    main()