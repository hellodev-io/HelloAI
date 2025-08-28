#!/usr/bin/env python3
"""
HelloAI 文章摘要提取脚本

用于提取文章的元信息和摘要，支持从 meta.json 读取详细信息。
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def extract_article_summary(article_path: str) -> Optional[Dict]:
    """提取单个文章的摘要信息"""
    article_path = Path(article_path)
    
    if not article_path.exists():
        print(f"❌ 文章不存在: {article_path}")
        return None
    
    try:
        # 读取文章内容
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        article_dir = article_path.parent
        meta_path = article_dir / 'meta.json'
        
        # 读取元信息
        meta_info = {}
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_info = json.load(f)
                print(f"  📄 读取元信息: {article_dir.name}")
            except Exception as e:
                print(f"  ⚠️ 元信息读取失败: {e}")
        
        # 提取基础信息
        lines = content.split('\n')
        title = None
        summary_lines = []
        
        # 找到标题
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # 提取开场白作为摘要（从引言或第一段正文）
        in_content = False
        for line in lines:
            line = line.strip()
            
            # 跳过标题和空行
            if line.startswith('#') or not line:
                continue
            
            # 找到开场白段落
            if line.startswith('>'):
                continue
            elif line and not line.startswith('##') and not line.startswith('!['):
                summary_lines.append(line)
                if len(summary_lines) >= 3:  # 取前3行作为摘要
                    break
        
        # 组合摘要
        summary = ' '.join(summary_lines)[:200] + '...' if summary_lines else ''
        
        # 统计信息
        images_dir = article_dir / 'images'
        images_count = len(list(images_dir.glob('*'))) if images_dir.exists() else 0
        
        # 构建摘要信息
        summary_info = {
            'path': str(article_path),
            'dir_name': article_dir.name,
            'title': title or '未知标题',
            'summary': summary,
            'content_length': len(content),
            'images_count': images_count,
            'has_cover': (article_dir / 'cover.jpg').exists(),
            'has_meta': meta_path.exists(),
            'extracted_at': datetime.now().isoformat()
        }
        
        # 添加元信息字段
        if meta_info:
            summary_info.update({
                'title_hook': meta_info.get('title_hook'),
                'description': meta_info.get('article_description'),
                'keywords': meta_info.get('keywords', []),
                'cover_copy_text': meta_info.get('cover_copy_text'),
                'product_count': meta_info.get('product_count', 0),
                'issue_number': meta_info.get('issue_info', {}).get('issue_number'),
                'publish_date': meta_info.get('publish_date'),
                'generated_at': meta_info.get('generated_at')
            })
        
        return summary_info
        
    except Exception as e:
        print(f"❌ 提取摘要失败: {article_path}, 错误: {e}")
        return None


def extract_all_articles_summary(articles_dir: str = 'articles') -> List[Dict]:
    """提取所有文章的摘要信息"""
    articles_path = Path(articles_dir)
    if not articles_path.exists():
        print(f"❌ 文章目录不存在: {articles_path}")
        return []
    
    all_summaries = []
    
    # 遍历所有文章目录
    for year_dir in sorted(articles_path.iterdir()):
        if not year_dir.is_dir():
            continue
            
        for date_dir in sorted(year_dir.iterdir()):
            if not date_dir.is_dir():
                continue
                
            index_file = date_dir / 'index.md'
            if index_file.exists():
                summary = extract_article_summary(str(index_file))
                if summary:
                    all_summaries.append(summary)
                    print(f"  ✅ {summary['title'][:50]}...")
    
    return all_summaries


def save_summaries_to_file(summaries: List[Dict], output_path: str = 'config/articles_summary.json'):
    """保存摘要到文件"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    summary_data = {
        'generated_at': datetime.now().isoformat(),
        'total_articles': len(summaries),
        'articles': summaries
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"📄 摘要文件已保存: {output_path}")
    return output_path


def print_summary_stats(summaries: List[Dict]):
    """打印统计信息"""
    if not summaries:
        print("📊 没有找到文章")
        return
    
    total = len(summaries)
    with_meta = len([s for s in summaries if s.get('has_meta')])
    with_cover = len([s for s in summaries if s.get('has_cover')])
    total_images = sum(s.get('images_count', 0) for s in summaries)
    
    print(f"\n📊 统计信息:")
    print(f"  📰 总文章数: {total}")
    print(f"  📄 有元信息: {with_meta} ({with_meta/total*100:.1f}%)")
    print(f"  🎨 有封面图: {with_cover} ({with_cover/total*100:.1f}%)")
    print(f"  🖼️  总图片数: {total_images}")
    
    # 最近的文章
    recent = sorted(summaries, key=lambda x: x.get('publish_date', ''), reverse=True)[:3]
    print(f"\n📅 最近文章:")
    for article in recent:
        date = article.get('publish_date', '未知日期')
        print(f"  - {date}: {article['title'][:40]}...")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='HelloAI 文章摘要提取工具')
    parser.add_argument('--single', '-s', help='提取单个文章摘要', metavar='PATH')
    parser.add_argument('--all', '-a', action='store_true', help='提取所有文章摘要')
    parser.add_argument('--output', '-o', default='config/articles_summary.json', help='输出文件路径')
    parser.add_argument('--articles-dir', default='articles', help='文章目录路径')
    
    args = parser.parse_args()
    
    if args.single:
        print(f"🔍 提取单个文章摘要: {args.single}")
        summary = extract_article_summary(args.single)
        if summary:
            print(f"✅ 提取成功:")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        
    elif args.all:
        print(f"🔍 提取所有文章摘要...")
        summaries = extract_all_articles_summary(args.articles_dir)
        
        if summaries:
            output_file = save_summaries_to_file(summaries, args.output)
            print_summary_stats(summaries)
            print(f"\n🎉 完成! 提取了 {len(summaries)} 篇文章的摘要")
        else:
            print("❌ 没有找到任何文章")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()