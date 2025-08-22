#!/usr/bin/env python3
import os
import json
import requests
import markdown
import time
from pathlib import Path
from datetime import datetime

class ZhihuPublisher:
    def __init__(self):
        self.username = os.getenv('ZHIHU_USERNAME')
        self.password = os.getenv('ZHIHU_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("未设置知乎配置，跳过知乎发布")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def login(self):
        """登录知乎（简化版，实际需要处理验证码等）"""
        # 注意：知乎登录比较复杂，需要处理验证码、加密等
        # 这里只是一个示例框架
        login_url = "https://www.zhihu.com/api/v3/oauth/sign_in"
        
        data = {
            "client_id": "c3cef7c66a1843f8b3a9e6a1e3160e20",
            "grant_type": "password",
            "source": "com.zhihu.web",
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = self.session.post(login_url, json=data)
            result = response.json()
            
            if 'access_token' in result:
                self.session.headers.update({
                    'Authorization': f"Bearer {result['access_token']}"
                })
                return True
            else:
                print(f"知乎登录失败: {result}")
                return False
        except Exception as e:
            print(f"知乎登录异常: {e}")
            return False
    
    def process_markdown_content(self, markdown_content, article_dir):
        """处理Markdown内容，转换为知乎格式"""
        # 知乎支持Markdown，但可能需要一些格式调整
        
        # 处理图片路径
        def replace_images(match):
            img_alt = match.group(1)
            img_path = match.group(2)
            
            # 如果是相对路径，需要转换为绝对URL或上传到知乎
            if not img_path.startswith(('http://', 'https://')):
                # 这里应该上传图片到知乎图床
                # 暂时保持原样
                pass
            
            return f'![{img_alt}]({img_path})'
        
        processed_content = markdown_content
        
        # 添加HelloAI署名
        footer = "\n\n---\n\n本文首发于 [ai.HelloDev.io](https://ai.HelloDev.io)，专注于AI行业技术分享。"
        processed_content += footer
        
        return processed_content
    
    def create_article(self, title, content):
        """创建知乎文章"""
        # 知乎创建文章API（示例）
        url = "https://www.zhihu.com/api/v4/articles"
        
        data = {
            "title": title,
            "content": content,
            "delta_time": 0,
            "reprint_policy": "cc_by_sa",  # 知识共享协议
            "topics": []  # 话题标签
        }
        
        try:
            response = self.session.post(url, json=data)
            result = response.json()
            
            if 'id' in result:
                return result['id']
            else:
                raise Exception(f"创建文章失败: {result}")
                
        except Exception as e:
            print(f"⚠️  知乎发布暂不可用: {e}")
            return None
    
    def publish_article_from_summary(self, article_path, title):
        """根据摘要信息发布文章到知乎"""
        if not self.login():
            raise Exception("知乎登录失败")
        
        file_path = Path(article_path)
        article_dir = file_path.parent
        
        # 读取文章内容
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 处理内容
        processed_content = self.process_markdown_content(markdown_content, article_dir)
        
        # 创建文章
        article_id = self.create_article(title, processed_content)
        
        if article_id:
            return {
                'article_id': article_id,
                'published_time': datetime.now().isoformat(),
                'platform': 'zhihu'
            }
        else:
            raise Exception("知乎发布失败")

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
            publish_result['message'] = "未找到发布摘要文件，跳过知乎发布"
            print(publish_result['message'])
            return
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        publisher = ZhihuPublisher()
        
        success_count = 0
        articles = summary.get('articles', [])
        
        for article in articles:
            try:
                print(f"\n📝 正在发布到知乎: {article['title']}")
                result = publisher.publish_article_from_summary(
                    article['path'], 
                    article['title']
                )
                print(f"✅ 知乎发布成功！article_id: {result['article_id']}")
                publish_result['details'].append({
                    'title': article['title'],
                    'success': True,
                    'article_id': result['article_id']
                })
                success_count += 1
                time.sleep(5)  # 避免频率限制
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
        print(f"⏭️ 跳过知乎发布: {e}")
    except Exception as e:
        publish_result['message'] = f"发布失败: {e}"
        print(f"❌ 知乎发布失败: {e}")
    
    finally:
        # 保存发布结果
        result_file = Path('config/zhihu_result.json')
        result_file.parent.mkdir(exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(publish_result, f, indent=2, ensure_ascii=False)
        
        if not publish_result['success'] and '未配置认证信息' not in publish_result['message']:
            exit(1)

if __name__ == "__main__":
    main()