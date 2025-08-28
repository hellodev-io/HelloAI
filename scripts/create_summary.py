#!/usr/bin/env python3
"""
HelloAI 发布摘要生成脚本

为发布的AI行业日报生成简洁的摘要信息，用于社交媒体分发。
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def read_article_content(article_path: str) -> Optional[str]:
    """读取文章内容"""
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文章失败: {article_path}, 错误: {e}")
        return None


def extract_article_summary(content: str) -> Dict:
    """提取文章关键信息（兼容AI产品头条格式）"""
    lines = content.split('\n')
    
    # 提取标题
    title = None
    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
            break
    
    # 检测文章类型
    is_product_digest = '产品头条' in (title or '') or 'Product Hunt' in content
    
    if is_product_digest:
        # AI产品头条格式
        product_count = 0
        products = []
        
        # 统计产品数量（查找产品标题格式）
        for line in lines:
            # 匹配产品标题格式，如 "### ProductName: Description" 或 "### 1. ProductName"
            if line.startswith('### ') and not line.startswith('### 🎯') and not line.startswith('### 📊'):
                product_count += 1
                # 提取产品名称
                product_line = line[4:].strip()  # 去掉 "### "
                
                # 如果有冒号，取冒号前的部分
                if ':' in product_line:
                    product_name = product_line.split(':', 1)[0].strip()
                elif ' - ' in product_line:
                    product_name = product_line.split(' - ', 1)[0].strip()
                else:
                    product_name = product_line
                
                # 去除数字前缀（如 "1. "）
                product_name = re.sub(r'^\d+\.\s*', '', product_name)
                # 去除链接格式
                product_name = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', product_name)
                products.append(product_name)
        
        # 提取开场白作为摘要
        intro_text = ""
        found_intro = False
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                continue
            elif line and not line.startswith('##') and not found_intro and len(line) > 20:
                intro_text = line[:100] + "..." if len(line) > 100 else line
                found_intro = True
                break
        
        return {
            'title': title or '未知标题',
            'type': 'product_digest',
            'product_count': product_count,
            'products': products[:5],  # 只显示前5个产品
            'intro_text': intro_text,
            'total_items': product_count,
            'category_count': 1,
            'stats': {'AI产品推荐': product_count}
        }
    
    else:
        # 传统格式
        # 提取统计信息（寻找📊 今日统计部分）
        stats = {}
        in_stats = False
        for line in lines:
            if '📊' in line and '今日统计' in line:
                in_stats = True
                continue
            elif in_stats and line.startswith('---'):
                break
            elif in_stats and line.strip().startswith('-'):
                # 解析统计行，如 "- 🚀 技术分享：X条"
                match = re.search(r'- ([^：]+)：(\d+)条', line)
                if match:
                    category = match.group(1).strip()
                    count = int(match.group(2))
                    stats[category] = count
        
        # 提取分类内容（统计各分类的项目）
        categories = {}
        current_category = None
        current_items = []
        
        for line in lines:
            # 检测分类标题
            if line.startswith('## ') and any(emoji in line for emoji in ['🚀', '🛠️', '📰', '💡', '📸']):
                if current_category and current_items:
                    categories[current_category] = current_items
                current_category = line[3:].strip()
                current_items = []
            
            # 检测项目标题
            elif line.startswith('### ') and current_category:
                # 提取项目名称（去掉链接格式）
                project_title = line[4:].strip()
                # 去掉markdown链接格式 [title](url)
                project_title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', project_title)
                current_items.append(project_title)
        
        # 添加最后一个分类
        if current_category and current_items:
            categories[current_category] = current_items
        
        # 统计总数
        total_items = sum(len(items) for items in categories.values())
        
        return {
            'title': title or '未知标题',
            'type': 'traditional',
            'stats': stats,
            'categories': categories,
            'total_items': total_items,
            'category_count': len(categories)
        }


def generate_social_summary(summary: Dict, article_date: str) -> Dict:
    """生成社交媒体摘要（支持AI产品头条和传统格式）"""
    
    if summary.get('type') == 'product_digest':
        # AI产品头条格式
        product_count = summary.get('product_count', 0)
        products = summary.get('products', [])
        intro_text = summary.get('intro_text', '')
        
        # 微信公众号摘要（较详细）
        wechat_summary = f"""🚀 HelloAI AI产品头条 - {article_date}

今日为大家精选了 {product_count} 个最新AI产品！

{intro_text}

🎯 今日精选产品包括：
"""
        
        for i, product in enumerate(products[:5], 1):
            wechat_summary += f"• {product}\n"
        
        if product_count > 5:
            wechat_summary += f"• ...及其他 {product_count - 5} 个优质产品\n"
        
        wechat_summary += f"""
每个产品都经过精心筛选，从创新性、实用性、技术深度等多个维度进行评估。

👉 点击阅读完整内容，发现最新AI神器！

#AI产品 #ProductHunt #HelloAI #人工智能"""

        # 掘金摘要（中等长度）  
        juejin_summary = f"""HelloAI AI产品头条 {article_date} | 今日精选 {product_count} 个AI产品

🔥 Product Hunt 今日最热AI产品抢先看：

"""
        
        for i, product in enumerate(products[:3], 1):
            juejin_summary += f"{i}. {product}\n"
        
        if product_count > 3:
            juejin_summary += f"...及其他 {product_count - 3} 个产品\n"
            
        juejin_summary += "\n更多精彩产品，点击查看完整推荐 👆"

        # 知乎摘要（简洁版）
        zhihu_summary = f"""HelloAI AI产品头条 {article_date}

今日从 Product Hunt 精选了 {product_count} 个最新AI产品，涵盖开发工具、创作辅助、数据分析等多个领域。

重点推荐："""
        
        if products:
            zhihu_summary += f"\n• {products[0]}"
        
        zhihu_summary += f"\n\n完整产品列表和详细介绍请查看原文。"
        
        short_summary = f"HelloAI AI产品头条 {article_date} - 精选 {product_count} 个最新AI产品"

    else:
        # 传统格式
        total_items = summary.get('total_items', 0)
        categories = summary.get('categories', {})
        
        # 微信公众号摘要（较详细）
        wechat_summary = f"""🔥 HelloAI AI日报 - {article_date}

今日为大家精选了 {total_items} 条优质技术内容：

"""
        
        for category, items in categories.items():
            if items:
                wechat_summary += f"{category} {len(items)}条\n"
        
        wechat_summary += f"""
涵盖了开源项目、开发工具、技术动态等多个方面。每一条都经过精心筛选，确保对开发者有实际价值。

👉 点击阅读完整内容，发现今日技术亮点！

#AI日报 #人工智能 #HelloAI"""

        # 掘金摘要（中等长度）
        juejin_summary = f"""HelloAI 日报 {article_date} | 今日 {total_items} 条AI精选

"""
        
        top_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        for category, items in top_categories:
            if items:
                juejin_summary += f"• {category}: {items[0]}\n"
        
        juejin_summary += "\n更多精彩内容，点击查看完整日报 👆"

        # 知乎摘要（简洁版）
        zhihu_summary = f"""HelloAI AI行业日报 {article_date}

今日精选 {total_items} 条AI技术资讯，包含AI研究、开源工具、行业动态等。

重点推荐："""
        
        if categories:
            first_category = list(categories.values())[0]
            if first_category:
                zhihu_summary += f"\n• {first_category[0]}"
        
        zhihu_summary += "\n\n详细内容请查看完整日报。"
        
        short_summary = f"HelloAI 日报 {article_date} - {total_items} 条精选AI资讯"

    return {
        'wechat': wechat_summary,
        'juejin': juejin_summary,
        'zhihu': zhihu_summary,
        'short': short_summary
    }


def save_summary_files(article_info: Dict, summary: Dict, social_summaries: Dict):
    """保存摘要文件"""
    
    # 创建输出目录
    output_dir = Path('config/summaries')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 完整摘要数据
    full_summary = {
        'article_info': article_info,
        'content_summary': summary,
        'social_summaries': social_summaries,
        'generated_at': datetime.now().isoformat()
    }
    
    # 保存完整摘要
    date_str = article_info.get('date', datetime.now().strftime('%Y-%m-%d'))
    summary_file = output_dir / f"summary_{date_str.replace('-', '')}.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(full_summary, f, ensure_ascii=False, indent=2)
    
    # 保存最新摘要（供脚本使用）
    with open('config/latest_summary.json', 'w', encoding='utf-8') as f:
        json.dump(full_summary, f, ensure_ascii=False, indent=2)
    
    print(f"📄 摘要已保存: {summary_file}")


def create_article_info_from_path(article_path: str) -> Optional[Dict]:
    """从文章路径创建文章信息"""
    if not os.path.exists(article_path):
        print(f"❌ 文章文件不存在: {article_path}")
        return None
    
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title = None
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # 从路径提取日期
        path_parts = article_path.split('/')
        if len(path_parts) >= 3:
            date_part = path_parts[2]  # 格式如 07-31
            year = path_parts[1]       # 格式如 2025
            date_str = f"{year}-{date_part}"
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 检查图片和缩略图
        article_dir = os.path.dirname(article_path)
        has_images = os.path.exists(os.path.join(article_dir, 'images'))
        has_thumb = os.path.exists(os.path.join(article_dir, 'thumb.jpg'))
        
        return {
            'path': article_path,
            'title': title or '未知标题',
            'date': date_str,
            'has_images': has_images,
            'has_thumb': has_thumb,
            'content_length': len(content),
            'detected_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"❌ 解析文章信息失败: {article_path}, 错误: {e}")
        return None


def main():
    """主函数"""
    import sys
    
    print("📝 HelloAI 发布摘要生成开始...")
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 直接处理命令行指定的文章
        # 支持多种输入格式：多行分隔或空格分隔
        raw_input = sys.argv[1].strip()
        
        # 如果包含换行符，按行分割；否则按空格分割
        if '\n' in raw_input:
            article_paths = [line.strip() for line in raw_input.split('\n') if line.strip()]
        else:
            article_paths = [path.strip() for path in raw_input.split() if path.strip()]
        
        print(f"📝 接收到 {len(article_paths)} 个文章路径:")
        for path in article_paths:
            print(f"  - {path}")
        
        articles_info = []
        
        for article_path in article_paths:
            if article_path:
                info = create_article_info_from_path(article_path)
                if info:
                    articles_info.append(info)
                    print(f"  ✅ 解析成功: {info['title']}")
                else:
                    print(f"  ❌ 解析失败: {article_path}")
        
        if not articles_info:
            print("❌ 未能解析任何有效的文章")
            return
            
    else:
        # 从配置文件读取变更信息（原有逻辑）
        changes_file = 'config/latest_changes.json'
        if not os.path.exists(changes_file):
            print("❌ 未找到变更信息文件，请先运行 detect_changes.py 或提供文章路径参数")
            return
        
        with open(changes_file, 'r', encoding='utf-8') as f:
            changes_data = json.load(f)
        
        if not changes_data.get('articles'):
            print("📰 未发现需要处理的文章")
            return
            
        articles_info = changes_data['articles']
    
    # 处理每篇文章
    for article_info in articles_info:
        article_path = article_info['path']
        print(f"📄 处理文章: {article_info['title']}")
        
        # 读取文章内容
        content = read_article_content(article_path)
        if not content:
            continue
        
        # 提取摘要
        summary = extract_article_summary(content)
        print(f"  📊 发现 {summary['total_items']} 条内容，{summary['category_count']} 个分类")
        
        # 生成社交媒体摘要
        social_summaries = generate_social_summary(summary, article_info['date'])
        
        # 保存摘要文件
        save_summary_files(article_info, summary, social_summaries)
        
        print(f"  ✅ {article_info['title']} 摘要生成完成")
    
    print("🎉 摘要生成完成!")


if __name__ == '__main__':
    main()