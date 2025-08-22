#!/usr/bin/env python3
import os
import json
import requests
import markdown
import re
import time
from pathlib import Path
from datetime import datetime

class WeChatPublisher:
    def __init__(self):
        self.app_id = os.getenv('WECHAT_APP_ID')
        self.app_secret = os.getenv('WECHAT_APP_SECRET')
        self.author = os.getenv('AUTHOR_NAME', 'HelloAI日报')
        self.source_url = os.getenv('SOURCE_URL', 'https://ai.HelloDev.io')
        self.access_token = None
        self.access_token_expires = 0
        
        if not self.app_id or not self.app_secret:
            raise ValueError("未设置微信公众号配置")
    
    def get_access_token(self):
        """获取access_token"""
        if self.access_token and time.time() < self.access_token_expires:
            return self.access_token
            
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        response = requests.get(url)
        result = response.json()
        
        if 'access_token' in result:
            self.access_token = result['access_token']
            self.access_token_expires = time.time() + result['expires_in'] - 600
            return self.access_token
        else:
            raise Exception(f"获取access_token失败: {result}")
    
    def upload_image(self, image_path):
        """上传图片到微信服务器"""
        access_token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
        
        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/jpeg')}
            response = requests.post(url, files=files)
            result = response.json()
            
        if 'errcode' not in result and 'url' in result:
            return result['url']
        else:
            raise Exception(f"图片上传失败: {result}")
    
    def upload_thumb_media(self, image_path):
        """上传缩略图素材"""
        print(f"🔍 开始上传缩略图: {image_path}")
        access_token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
        
        with open(image_path, 'rb') as f:
            files = {'media': (os.path.basename(image_path), f, 'image/jpeg')}
            response = requests.post(url, files=files)
            result = response.json()
            
        if 'errcode' not in result and 'media_id' in result:
            media_id = result['media_id']
            print(f"✅ 缩略图上传成功，media_id: {media_id}")
            return media_id
        else:
            print(f"❌ 缩略图上传失败: {result}")
            raise Exception(f"缩略图上传失败: {result}")
    
    def get_inline_styles(self):
        """获取内联样式映射（微信公众号不支持style标签）"""
        return {
            'body': 'font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "Microsoft YaHei", Arial, sans-serif; font-size: 15px; line-height: 1.8; letter-spacing: 0.3px; color: #2c3e50; word-spacing: 0.5px;',
            'h1': 'font-size: 22px; font-weight: 700; color: #1a202c; margin: 40px 0 24px 0; line-height: 1.3; letter-spacing: 0.5px; padding-bottom: 12px; border-bottom: 2px solid #4299e1;',
            'h2': 'font-size: 19px; font-weight: 600; color: #2d3748; margin: 36px 0 18px 0; line-height: 1.4; letter-spacing: 0.3px; position: relative; padding-left: 16px;',
            'h3': 'font-size: 17px; font-weight: 600; color: #4a5568; margin: 32px 0 16px 0; line-height: 1.4; letter-spacing: 0.2px;',
            'p': 'margin: 18px 0; text-align: justify; line-height: 1.8; letter-spacing: 0.3px; word-spacing: 0.5px; color: #2c3e50; text-justify: inter-ideograph;',
            'ul': 'margin: 16px 0; padding-left: 0; list-style: none;',
            'ol': 'margin: 16px 0; padding-left: 20px; list-style-type: decimal;',
            'li': 'margin: 6px 0; line-height: 1.7; color: #2c3e50; letter-spacing: 0.3px; padding-left: 0; position: relative;',
            'blockquote': 'border-left: 3px solid #4299e1; margin: 28px 0; padding: 20px 24px; background-color: #f8fafc; color: #4a5568; border-radius: 6px; letter-spacing: 0.2px; line-height: 1.7; font-style: normal;',
            'code': 'background-color: #f1f5f9; padding: 2px 6px; border-radius: 3px; font-family: "SF Mono", Consolas, "Liberation Mono", Menlo, monospace; color: #e53e3e; font-size: 13px; letter-spacing: 0px;',
            'pre': 'background-color: #f8fafc; padding: 24px; border-radius: 8px; overflow-x: auto; border: 1px solid #e2e8f0; margin: 28px 0; line-height: 1.6; font-size: 13px;',
            'pre code': 'background-color: transparent; padding: 0; color: #2d3748; font-size: 13px; letter-spacing: 0px;',
            'strong': 'color: #1a202c; font-weight: 600; letter-spacing: 0.2px;',
            'em': 'color: #4299e1; font-style: normal; font-weight: 500; letter-spacing: 0.1px;',
            'img': 'max-width: 100%; height: auto; border-radius: 6px; margin: 28px auto; display: block; box-shadow: 0 4px 20px rgba(0,0,0,0.08);',
            'table': 'border-collapse: collapse; width: 100%; margin: 28px 0; font-size: 14px; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);',
            'th': 'border: none; padding: 16px 20px; text-align: left; background-color: #f8fafc; color: #2d3748; font-weight: 600; letter-spacing: 0.2px;',
            'td': 'border: none; border-bottom: 1px solid #e2e8f0; padding: 16px 20px; text-align: left; color: #2c3e50; letter-spacing: 0.2px;',
            'hr': 'border: none; height: 1px; background: linear-gradient(to right, transparent, #e2e8f0, transparent); margin: 40px 0;'
        }
    
    def apply_inline_styles(self, html):
        """将CSS样式转换为内联样式（微信公众号兼容）"""
        from bs4 import BeautifulSoup
        
        try:
            # 使用lxml-xml解析器保持更好的HTML结构
            soup = BeautifulSoup(html, 'html.parser')
            styles = self.get_inline_styles()
            
            # 应用样式到各个标签
            for tag_name, style in styles.items():
                if tag_name == 'pre code':
                    # 特殊处理 pre code
                    for pre in soup.find_all('pre'):
                        for code in pre.find_all('code'):
                            code['style'] = style
                else:
                    for tag in soup.find_all(tag_name):
                        # 保持现有style属性，合并新样式
                        existing_style = tag.get('style', '')
                        if existing_style:
                            tag['style'] = existing_style + '; ' + style
                        else:
                            tag['style'] = style
            
            # 特殊处理表格样式
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for i, row in enumerate(rows):
                    if i % 2 == 1:  # 奇数行（除了表头）
                        existing_style = row.get('style', '')
                        if existing_style:
                            row['style'] = existing_style + '; background-color: #f8fafc;'
                        else:
                            row['style'] = 'background-color: #f8fafc;'
            
            # 为h2标签添加左侧装饰线
            for h2 in soup.find_all('h2'):
                current_style = h2.get('style', '')
                if 'border-left' not in current_style:
                    h2['style'] = current_style + '; border-left: 4px solid #4299e1;'
            
            # 优化链接样式
            for a in soup.find_all('a'):
                a['style'] = 'color: #4299e1; text-decoration: none; font-weight: 500;'
            
            # 处理特殊格式（加粗的标题行）
            for p in soup.find_all('p'):
                if p.find('strong') and len(p.get_text().strip()) < 50:
                    # 可能是小标题
                    strong = p.find('strong')
                    if strong and strong.get_text() in ['技术解析', '核心特性', 'AI洞察', '应用场景', '商业价值', '延伸思考', '明日预告', '互动时间', '关注HelloAI', '多平台发布', '今日统计']:
                        strong['style'] = 'color: #2d3748; font-weight: 600; font-size: 16px; letter-spacing: 0.3px;'
                        p['style'] = 'margin: 28px 0 16px 0; line-height: 1.6;'
            
            # 优化列表显示效果
            for ul in soup.find_all('ul'):
                # 应用无序列表样式
                ul_style = styles.get('ul', '')
                ul['style'] = ul_style
                
                for li in ul.find_all('li'):
                    # 应用列表项样式
                    li_style = styles.get('li', '')
                    li['style'] = li_style
                    
                    # 为无序列表项添加自定义项目符号
                    text_content = li.get_text().strip()
                    if text_content and not text_content.startswith(('•', '·', '-', '*')):
                        # 如果内容不是以常见符号开始，添加项目符号
                        if li.string:
                            li.string.replace_with(f"• {text_content}")
                        elif li.contents:
                            # 处理包含其他标签的情况
                            from bs4 import NavigableString
                            first_text = None
                            for content in li.contents:
                                if isinstance(content, NavigableString) and content.strip():
                                    first_text = content
                                    break
                            if first_text and not first_text.strip().startswith(('•', '·', '-', '*')):
                                first_text.replace_with(f"• {first_text}")
            
            # 处理有序列表
            for ol in soup.find_all('ol'):
                ol_style = styles.get('ol', '')
                ol['style'] = ol_style
            
            return str(soup)
            
        except ImportError:
            print("⚠️  BeautifulSoup4 未安装，无法应用内联样式")
            return html
        except Exception as e:
            print(f"⚠️  应用内联样式失败: {e}")
            return html
    
    
    def process_markdown_content(self, markdown_content, article_dir):
        """处理Markdown内容，上传图片并转换HTML"""
        
        def replace_images(match):
            img_alt = match.group(1)
            img_path = match.group(2)
            
            # 处理相对路径
            if not img_path.startswith(('http://', 'https://')):
                full_path = Path(article_dir) / img_path
                if full_path.exists():
                    try:
                        wx_url = self.upload_image(str(full_path))
                        # 使用内联样式
                        img_style = self.get_inline_styles()['img']
                        return f'<img src="{wx_url}" alt="{img_alt}" style="{img_style}">'
                    except Exception as e:
                        print(f"⚠️  图片上传失败 {img_path}: {e}")
                        return f'<p>[图片上传失败: {img_alt}]</p>'
            
            # 使用内联样式
            img_style = self.get_inline_styles()['img']
            return f'<img src="{img_path}" alt="{img_alt}" style="{img_style}">'
        
        # 移除主标题（微信公众号标题单独设置）
        lines = markdown_content.split('\n')
        if lines and lines[0].startswith('# '):
            # 移除第一行的主标题
            lines = lines[1:]
            # 移除标题后可能的空行
            while lines and lines[0].strip() == '':
                lines = lines[1:]
            markdown_content = '\n'.join(lines)
        
        
        # 替换图片
        markdown_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_images, markdown_content)
        
        # 转换为HTML
        html = markdown.markdown(
            markdown_content,
            extensions=['codehilite', 'tables', 'toc', 'fenced_code', 'nl2br'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                },
                'nl2br': {}
            }
        )
        
        # 应用内联样式（微信公众号兼容）
        html_with_styles = self.apply_inline_styles(html)
        
        # 包装在一个带样式的div中
        body_style = self.get_inline_styles()['body']
        return f'<div style="{body_style}">{html_with_styles}</div>'
    
    def create_draft(self, title, content, author, digest, thumb_media_id, source_url):
        """创建草稿"""
        access_token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
        
        article_data = {
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "content_source_url": source_url,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }
        
        # thumb_media_id 是必填字段
        if not thumb_media_id or not thumb_media_id.strip():
            raise Exception("缩略图 media_id 不能为空")
        
        article_data["thumb_media_id"] = thumb_media_id
        
        data = {"articles": [article_data]}
        
        # 确保正确的编码处理
        json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        response = requests.post(url, data=json_data.encode('utf-8'), headers=headers)
        result = response.json()
        
        if 'errcode' not in result and 'media_id' in result:
            print(f"✅ 草稿创建成功，media_id: {result['media_id']}")
            return result['media_id']
        else:
            raise Exception(f"创建草稿失败: {result}")
    
    def publish_draft(self, media_id):
        """发布草稿"""
        access_token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={access_token}"
        
        data = {"media_id": media_id}
        
        # 确保正确的编码处理
        json_data = json.dumps(data, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        response = requests.post(url, data=json_data.encode('utf-8'), headers=headers)
        result = response.json()
        
        if 'errcode' not in result and 'publish_id' in result:
            return result.get('publish_id')
        else:
            raise Exception(f"发布失败: {result}")
    
    def truncate_text(self, text, max_length, field_name="文本"):
        """截断文本到指定长度"""
        if len(text) <= max_length:
            return text
        
        # 截断并添加省略号
        truncated = text[:max_length-3] + "..."
        print(f"⚠️  {field_name}过长已截断: {text[:20]}... -> {truncated}")
        return truncated
    
    def publish_article_from_summary(self, article_path, title):
        """根据摘要信息发布文章"""
        file_path = Path(article_path)
        article_dir = file_path.parent
        
        # 处理标题长度限制（微信上限64字符）
        title = self.truncate_text(title, max_length=64, field_name="标题")
        
        # 读取文章内容
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 处理内容
        html_content = self.process_markdown_content(markdown_content, article_dir)
        
        # 生成摘要
        content_text = re.sub(r'[#*`\[\]()]', '', markdown_content)
        digest = content_text[:100].strip() + "..." if len(content_text) > 100 else content_text
        
        # 限制摘要长度（微信上限120字符）
        digest = self.truncate_text(digest, max_length=120, field_name="摘要")
        
        # 查找缩略图
        thumb_media_id = ""
        for thumb_name in ['thumb.jpg', 'thumb.jpeg', 'thumb.png', 'cover.jpg', 'cover.png']:
            thumb_path = article_dir / thumb_name
            if thumb_path.exists():
                try:
                    thumb_media_id = self.upload_thumb_media(str(thumb_path))
                    break
                except Exception as e:
                    print(f"⚠️  缩略图上传失败 {thumb_name}: {e}")
                    continue
        
        if not thumb_media_id:
            # 使用默认缩略图
            default_thumb_path = Path(__file__).parent.parent / 'config' / 'default_thumb.jpg'
            if default_thumb_path.exists():
                try:
                    thumb_media_id = self.upload_thumb_media(str(default_thumb_path))
                except Exception as e:
                    raise Exception(f"默认缩略图上传失败: {e}")
            else:
                raise Exception(f"默认缩略图文件不存在: {default_thumb_path}")
        
        # 创建草稿（仅创建草稿，不自动发布）
        media_id = self.create_draft(
            title=title,
            content=html_content,
            author=self.author,
            digest=digest,
            thumb_media_id=thumb_media_id,
            source_url=self.source_url
        )
        
        print(f"✅ 草稿创建成功，可在微信公众号后台查看 (media_id: {media_id})")
        print("ℹ️  草稿已准备就绪，需要手动在微信公众号后台发布")
        
        return {
            'media_id': media_id,
            'draft_created_time': datetime.now().isoformat(),
            'status': 'draft_created'
        }

def main():
    """主函数 - 与 create_summary.py 配合使用"""
    publish_result = {
        'success': False,
        'message': '',
        'details': []
    }
    
    try:
        publisher = WeChatPublisher()
        
        # 检查标准摘要文件
        summary_file = Path('config/latest_summary.json')
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            articles = summary_data.get('article_info', [])
            # 兼容单个文章和文章列表格式
            if isinstance(articles, dict):
                articles = [articles]
            elif 'articles' in summary_data:
                articles = summary_data['articles']
            
            success_count = 0
            for article in articles:
                try:
                    print(f"\n📝 正在创建草稿: {article['title']}")
                    result = publisher.publish_article_from_summary(
                        article['path'], 
                        article['title']
                    )
                    print(f"✅ 草稿创建成功！media_id: {result['media_id']}")
                    publish_result['details'].append({
                        'title': article['title'],
                        'success': True,
                        'media_id': result['media_id']
                    })
                    success_count += 1
                    time.sleep(3)  # 避免频率限制
                except Exception as e:
                    print(f"❌ 文章 {article['title']} 发布失败: {e}")
                    publish_result['details'].append({
                        'title': article['title'],
                        'success': False,
                        'error': str(e)
                    })
            
            publish_result['success'] = success_count > 0
            publish_result['message'] = f"成功发布 {success_count}/{len(articles)} 篇文章"
        else:
            publish_result['message'] = "未找到发布摘要文件: config/latest_summary.json"
            
    except ValueError as e:
        # 未配置认证信息
        publish_result['message'] = str(e)
        print(f"⏭️ 跳过微信发布: {e}")
    except Exception as e:
        publish_result['message'] = f"发布失败: {e}"
        print(f"❌ 草稿创建失败: {e}")
    
    finally:
        # 保存发布结果
        result_file = Path('config/wechat_result.json')
        result_file.parent.mkdir(exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(publish_result, f, indent=2, ensure_ascii=False)
        
        if not publish_result['success'] and '未设置微信公众号配置' not in publish_result['message']:
            exit(1)

if __name__ == "__main__":
    main()