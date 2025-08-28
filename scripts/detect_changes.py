#!/usr/bin/env python3
"""
HelloAI 文章变更检测脚本

检测新增或修改的日报文章，为自动发布流程提供支持。
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def get_git_changed_files() -> List[str]:
    """获取Git变更的文件列表"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        print("警告: 无法获取Git变更，可能是首次提交")
        return []


def filter_article_files(files: List[str]) -> List[str]:
    """过滤出文章文件"""
    article_files = []
    for file in files:
        if file.startswith('articles/') and file.endswith('index.md'):
            article_files.append(file)
    return article_files


def extract_article_info(article_path: str) -> Optional[Dict]:
    """提取文章信息（优化版，支持元信息读取）"""
    if not os.path.exists(article_path):
        return None
    
    try:
        # 读取文章内容
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 文章目录路径
        article_dir = os.path.dirname(article_path)
        meta_path = os.path.join(article_dir, 'meta.json')
        
        # 优先从 meta.json 读取信息
        meta_info = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_info = json.load(f)
                print(f"  📄 读取到元信息: {os.path.basename(article_dir)}")
            except Exception as e:
                print(f"  ⚠️ 元信息读取失败: {e}")
        
        # 提取标题（优先使用元信息，否则从内容提取）
        if meta_info.get('full_title'):
            title = meta_info['full_title']
        else:
            # 从内容提取标题（第一个# 标题）
            lines = content.split('\n')
            title = None
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            title = title or '未知标题'
        
        # 日期信息（优先使用元信息）
        if meta_info.get('publish_date'):
            date_str = meta_info['publish_date']
        else:
            # 从路径提取日期
            path_parts = article_path.split('/')
            if len(path_parts) >= 3:
                date_part = path_parts[2]  # 格式如 08-28
                year = path_parts[1]       # 格式如 2025
                date_str = f"{year}-{date_part}"
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 检查图片和资源
        images_dir = os.path.join(article_dir, 'images')
        has_images = os.path.exists(images_dir) and len(os.listdir(images_dir)) > 0
        images_count = len(os.listdir(images_dir)) if has_images else 0
        
        # 封面图检查
        cover_path = os.path.join(article_dir, 'cover.jpg')
        has_cover = os.path.exists(cover_path)
        
        # 缩略图路径
        thumb_path = os.path.join(article_dir, 'thumb.jpg')
        has_thumb = os.path.exists(thumb_path)
        
        # 构建完整信息
        article_info = {
            'path': article_path,
            'title': title,
            'date': date_str,
            'has_images': has_images,
            'images_count': images_count,
            'has_cover': has_cover,
            'has_thumb': has_thumb,
            'content_length': len(content),
            'detected_at': datetime.now().isoformat()
        }
        
        # 如果有元信息，添加额外字段
        if meta_info:
            article_info.update({
                'title_hook': meta_info.get('title_hook'),
                'description': meta_info.get('article_description'),
                'keywords': meta_info.get('keywords', []),
                'cover_copy_text': meta_info.get('cover_copy_text'),
                'product_count': meta_info.get('product_count', 0),
                'issue_number': meta_info.get('issue_info', {}).get('issue_number'),
                'generated_at': meta_info.get('generated_at'),
                'has_meta': True
            })
        else:
            article_info['has_meta'] = False
        
        return article_info
    
    except Exception as e:
        print(f"提取文章信息失败: {article_path}, 错误: {e}")
        return None


def save_change_summary(articles_info: List[Dict]):
    """保存变更摘要"""
    summary = {
        'detection_time': datetime.now().isoformat(),
        'total_changes': len(articles_info),
        'articles': articles_info
    }
    
    # 确保目录存在
    os.makedirs('config', exist_ok=True)
    
    # 保存到配置文件
    with open('config/latest_changes.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"变更摘要已保存: {len(articles_info)} 篇文章")


def main():
    """主函数"""
    print("🔍 HelloAI 文章变更检测开始...")
    
    # 获取变更文件
    changed_files = get_git_changed_files()
    if not changed_files:
        print("📝 未检测到任何文件变更")
        return
    
    print(f"📁 检测到 {len(changed_files)} 个文件变更")
    
    # 过滤文章文件
    article_files = filter_article_files(changed_files)
    if not article_files:
        print("📰 未检测到文章文件变更")
        return
    
    print(f"📰 检测到 {len(article_files)} 篇文章变更:")
    for file in article_files:
        print(f"  - {file}")
    
    # 提取文章信息
    articles_info = []
    for article_file in article_files:
        info = extract_article_info(article_file)
        if info:
            articles_info.append(info)
            print(f"  ✅ {info['title']} ({info['date']})")
        else:
            print(f"  ❌ 提取失败: {article_file}")
    
    # 保存变更摘要
    if articles_info:
        save_change_summary(articles_info)
        print("🎉 变更检测完成!")
    else:
        print("❌ 未发现有效的文章变更")


if __name__ == '__main__':
    main()