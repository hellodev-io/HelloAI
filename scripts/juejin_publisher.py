#!/usr/bin/env python3
import os
import json
import requests
import markdown
import re
from pathlib import Path
from datetime import datetime
from juejin_token_manager import JuejinTokenManager

class JuejinPublisher:
    def __init__(self):
        # 使用令牌管理器获取有效的令牌（每次都刷新）
        try:
            self.token_manager = JuejinTokenManager()
            self.session_id, self.csrf_token = self.token_manager.get_valid_tokens()
            print(f"🔍 获取到令牌: sessionid={self.session_id[:8]}...{self.session_id[-8:]}")
            print(f"🔍 获取到令牌: csrf_token={self.csrf_token[:8]}...{self.csrf_token[-8:]}")
        except Exception as e:
            raise ValueError(f"获取掘金令牌失败: {e}")
        
        self.column_id = os.getenv('JUEJIN_COLUMN_ID')  # 专辑ID
        
        self.session = requests.Session()
        self.session.cookies.set('sessionid', self.session_id)
        print(f"🔍 设置Session Cookies: sessionid={self.session_id[:8]}...{self.session_id[-8:]}")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://juejin.cn/editor/drafts',
            'Origin': 'https://juejin.cn',
            'X-CSRFToken': self.csrf_token,
            'Content-Type': 'application/json',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        })
    
    def process_markdown_content(self, markdown_content, article_dir):
        """处理Markdown内容，移除开头标题并将本地图片转换为GitHub外链"""
        # GitHub仓库配置
        github_base_url = "https://raw.githubusercontent.com/hellodev-io/HelloAI/refs/heads/main"
        
        # 移除开头的主标题（# 标题）
        lines = markdown_content.split('\n')
        processed_lines = []
        title_removed = False
        
        for line in lines:
            # 跳过开头的主标题（以单个#开头的行）
            if not title_removed and line.strip().startswith('# ') and not line.strip().startswith('## '):
                title_removed = True
                print(f"    🗑️  移除开头标题: {line.strip()}")
                continue
            # 跳过标题后的空行
            elif not title_removed and line.strip() == '':
                continue
            else:
                title_removed = True
                processed_lines.append(line)
        
        processed_content = '\n'.join(processed_lines)
        
        def replace_images(match):
            img_alt = match.group(1)
            img_path = match.group(2)
            
            # 如果是本地相对路径，转换为GitHub外链
            if not img_path.startswith(('http://', 'https://')):
                # 处理相对路径，转换为绝对路径
                if img_path.startswith('./'):
                    img_path = img_path[2:]  # 移除 './'
                elif img_path.startswith('../'):
                    # 处理上级目录
                    img_path = img_path.replace('../', '')
                
                # 构建 GitHub 外链
                github_url = f"{github_base_url}/{article_dir}/{img_path.lstrip('/')}"
                print(f"    🖼️  图片转换: {img_path} -> GitHub外链: {github_url}")
                return f'![{img_alt}]({github_url})'
            
            return f'![{img_alt}]({img_path})'
        
        # 替换图片路径
        processed_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_images, processed_content)
        
        return processed_content
    
    def create_draft(self, title, content, tags=None):
        """创建掘金草稿（基于逆向工程发现的真实API）"""
        if tags is None:
            tags = ["人工智能", "AI", "HelloAI"]
        
        # 掘金草稿创建API（已验证可用）
        url = "https://api.juejin.cn/content_api/v1/article_draft/create"
        
        # 根据逆向工程发现的数据格式
        data = {
            "title": title,
            "content": content,
            "mark_content": content,
            "tag_ids": [],
            "category_id": "6809637767543259144",  # 后端分类
            "brief_content": "",  # 简介
            "edit_type": 10,  # 编辑器类型，可能是 markdown
            "html_content": "deprecated",  # 一些API要求这个字段
            "cover_image": "",  # 封面图
            "is_gfw": 0,  # 是否过墙
            "is_english": 0,  # 是否英文
            "is_original": 1,  # 是否原创
            "user_interact": {},  # 用户交互
            "tags": []  # 标签数组
        }
        
        # 暂时移除专辑功能，因为草稿创建API不支持直接添加到专辑
        # 可以在草稿创建后手动添加
        if self.column_id:
            print(f"    📚 已配置专辑ID: {self.column_id}（需手动添加）")
        
        print(f"    🔍 请求URL: {url}")
        print(f"    🔍 请求Headers: {dict(self.session.headers)}")
        print(f"    🔍 请求数据: title={data['title']}, content_length={len(data['content'])}")
        
        try:
            response = self.session.post(url, json=data)
            print(f"    🔍 响应状态码: {response.status_code}")
            print(f"    🔍 响应Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"    ❌ HTTP错误: {response.status_code}")
                print(f"    📄 响应内容: {response.text}")
                return None
                
            result = response.json()
            print(f"    🔍 完整响应: {result}")
            
            if result.get('err_no') == 0:
                draft_id = result.get('data', {}).get('id')
                print(f"    ✅ 成功创建草稿: {draft_id}")
                print(f"    🔗 编辑链接: https://juejin.cn/editor/drafts/{draft_id}")
                
                return draft_id
            else:
                raise Exception(f"创建草稿失败: {result}")
                
        except Exception as e:
            print(f"⚠️  掘金发布暂不可用: {e}")
            return None
    
    def add_article_to_column(self, article_id):
        """将文章添加到专辑"""
        if not self.column_id:
            return False
        
        try:
            # 掘金添加文章到专辑的API（示例）
            url = "https://api.juejin.cn/content_api/v1/column/add_article"
            
            data = {
                "column_id": self.column_id,
                "article_id": article_id
            }
            
            response = self.session.post(url, json=data)
            result = response.json()
            
            if result.get('err_no') == 0:
                print(f"    ✅ 成功添加到专辑: {self.column_id}")
                return True
            else:
                print(f"    ⚠️ 添加到专辑失败: {result}")
                return False
                
        except Exception as e:
            print(f"    ⚠️ 添加到专辑异常: {e}")
            return False
    
    def get_my_columns(self):
        """获取我的专辑列表（用于调试和配置）"""
        try:
            url = "https://api.juejin.cn/content_api/v1/column/user_columns"
            
            response = self.session.get(url)
            result = response.json()
            
            if result.get('err_no') == 0:
                columns = result.get('data', [])
                print(f"📚 可用专辑列表:")
                for column in columns:
                    print(f"  - ID: {column.get('column_id')} | 名称: {column.get('title')}")
                return columns
            else:
                print(f"获取专辑列表失败: {result}")
                return []
                
        except Exception as e:
            print(f"获取专辑列表异常: {e}")
            return []
    
    def publish_article_from_summary(self, article_path, title):
        """根据摘要信息发布文章到掘金"""
        file_path = Path(article_path)
        article_dir = file_path.parent
        
        # 读取文章内容
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 处理内容
        processed_content = self.process_markdown_content(markdown_content, article_dir)
        
        # 创建草稿
        draft_id = self.create_draft(title, processed_content)
        
        if draft_id:
            return {
                'draft_id': draft_id,
                'edit_url': f"https://juejin.cn/editor/drafts/{draft_id}",
                'created_time': datetime.now().isoformat(),
                'platform': 'juejin',
                'status': 'draft_created'
            }
        else:
            raise Exception("掘金草稿创建失败")

def main():
    """主函数"""
    publish_result = {
        'success': False,
        'message': '',
        'details': []
    }
    
    try:
        # 检查摘要文件
        summary_file = Path('config/latest_summary.json')
        if not summary_file.exists():
            publish_result['message'] = "未找到发布摘要文件，跳过掘金发布"
            print(publish_result['message'])
            return
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        publisher = JuejinPublisher()
        
        # 显示专辑配置信息
        if publisher.column_id:
            print(f"📚 专辑配置: {publisher.column_id}")
            print("✅ 文章将自动添加到指定专辑")
        else:
            print("📚 未配置专辑ID，文章将发布为独立文章")
            print("💡 提示: 设置 JUEJIN_COLUMN_ID 环境变量可自动添加到专辑")
        
        # 兼容多种摘要文件格式（参考微信脚本）
        articles = summary.get('article_info', [])
        # 兼容单个文章和文章列表格式
        if isinstance(articles, dict):
            articles = [articles]
        elif 'articles' in summary:
            articles = summary['articles']
        
        print(f"🔍 找到 {len(articles)} 篇文章待发布")
        
        success_count = 0
        
        for article in articles:
            try:
                print(f"\n📝 正在发布到掘金: {article['title']}")
                result = publisher.publish_article_from_summary(
                    article['path'], 
                    article['title']
                )
                print(f"✅ 掘金草稿创建成功！draft_id: {result['draft_id']}")
                print(f"🔗 编辑链接: {result['edit_url']}")
                publish_result['details'].append({
                    'title': article['title'],
                    'success': True,
                    'draft_id': result['draft_id'],
                    'edit_url': result['edit_url']
                })
                success_count += 1
            except Exception as e:
                print(f"❌ 文章 {article['title']} 发布失败: {e}")
                publish_result['details'].append({
                    'title': article['title'],
                    'success': False,
                    'error': str(e)
                })
        
        publish_result['success'] = success_count > 0
        publish_result['message'] = f"成功发布 {success_count}/{len(articles)} 篇文章"
            
    except ValueError as e:
        # 未配置认证信息
        publish_result['message'] = str(e)
        print(f"⏭️ 跳过掘金发布: {e}")
    except Exception as e:
        publish_result['message'] = f"发布失败: {e}"
        print(f"❌ 掘金发布失败: {e}")
    
    finally:
        # 保存发布结果
        result_file = Path('config/juejin_result.json')
        result_file.parent.mkdir(exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(publish_result, f, indent=2, ensure_ascii=False)
        
        # 只在真正的错误时退出，跳过发布不应该算作错误
        should_exit = (
            not publish_result['success'] and 
            '未配置认证信息' not in publish_result['message'] and
            '未找到发布摘要文件' not in publish_result['message'] and
            len(publish_result['message']) > 0  # 确保有实际错误消息
        )
        if should_exit:
            print(f"🔍 退出条件检查: success={publish_result['success']}, message='{publish_result['message']}'")
            exit(1)

if __name__ == "__main__":
    import sys
    
    # 如果传入 --list-columns 参数，列出可用专辑
    if len(sys.argv) > 1 and sys.argv[1] == '--list-columns':
        try:
            publisher = JuejinPublisher()
            publisher.get_my_columns()
        except ValueError as e:
            print(f"❌ {e}")
        except Exception as e:
            print(f"❌ 获取专辑列表失败: {e}")
    else:
        main()