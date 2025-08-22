#!/usr/bin/env python3
import os
import json
import base64
import requests
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet

class JuejinTokenManager:
    def __init__(self):
        self.encrypted_token_file = Path('config/juejin_tokens.enc')
        self.session = requests.Session()
        
        # 从环境变量获取加密密钥
        encryption_key = os.getenv('JUEJIN_ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("未设置 JUEJIN_ENCRYPTION_KEY，无法进行令牌加密")
        
        # 确保密钥格式正确
        try:
            self.cipher = Fernet(encryption_key.encode())
        except Exception as e:
            raise ValueError(f"加密密钥格式错误: {e}")
    
    def load_cached_tokens(self):
        """加载并解密本地缓存的 token"""
        try:
            if self.encrypted_token_file.exists():
                with open(self.encrypted_token_file, 'rb') as f:
                    encrypted_data = f.read()
                
                # 解密数据
                decrypted_data = self.cipher.decrypt(encrypted_data)
                token_data = json.loads(decrypted_data.decode('utf-8'))
                
                print(f"✅ 成功加载缓存的令牌")
                return token_data
            else:
                print(f"ℹ️ 未找到令牌缓存文件")
        except Exception as e:
            print(f"⚠️ 读取缓存令牌失败: {e}")
        
        return None
    
    def save_tokens_to_cache(self, session_id, csrf_token):
        """加密保存 token 到本地缓存"""
        try:
            # 确保配置目录存在
            self.encrypted_token_file.parent.mkdir(exist_ok=True)
            
            token_data = {
                'session_id': session_id,
                'csrf_token': csrf_token,
                'updated_at': datetime.now().isoformat()
            }
            
            # 加密数据
            json_data = json.dumps(token_data, ensure_ascii=False)
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))
            
            with open(self.encrypted_token_file, 'wb') as f:
                f.write(encrypted_data)
            
            print(f"✅ 令牌已加密保存到缓存")
            return True
            
        except Exception as e:
            print(f"❌ 保存缓存令牌失败: {e}")
            return False
    
    def get_env_tokens(self):
        """从环境变量获取令牌（兜底冷启动）"""
        session_id = os.getenv('JUEJIN_SESSION_ID')
        csrf_token = os.getenv('JUEJIN_CSRF_TOKEN')
        
        if not session_id or not csrf_token:
            raise ValueError("未设置掘金环境变量配置")
        
        print(f"🔑 使用环境变量中的令牌")
        return session_id, csrf_token
    
    def test_token_validity(self, session_id, csrf_token):
        """测试 token 是否有效"""
        try:
            test_session = requests.Session()
            test_session.cookies.set('sessionid', session_id)
            test_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-CSRFToken': csrf_token,
                'Content-Type': 'application/json'
            })
            
            # 使用用户信息API测试令牌有效性
            test_url = "https://api.juejin.cn/user_api/v1/user/get"
            print(f"    🔍 测试URL: {test_url}")
            print(f"    🔍 测试Headers: {dict(test_session.headers)}")
            print(f"    🔍 测试Cookies: sessionid={session_id[:8]}...{session_id[-8:]}")
            
            response = test_session.get(test_url, timeout=10)
            print(f"    🔍 验证响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"    🔍 验证响应内容: {result}")
                if result.get('err_no') == 0:
                    user_info = result.get('data', {})
                    print(f"    ✅ 令牌验证成功, 用户ID: {user_info.get('user_id', 'unknown')}")
                    return True
                else:
                    print(f"    ❌ 令牌验证失败: {result.get('err_msg', '未知错误')}")
                    return False
            else:
                print(f"    ❌ 令牌验证请求失败: HTTP {response.status_code}")
                print(f"    📄 响应内容: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 令牌验证异常: {e}")
            return False
    
    def refresh_token_from_session(self, base_session_id, base_csrf_token):
        """
        基于现有 session 刷新获取新的 token
        模拟浏览器访问掘金主页来刷新 CSRF token
        """
        try:
            refresh_session = requests.Session()
            refresh_session.cookies.set('sessionid', base_session_id)
            refresh_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # 访问掘金主页来刷新 session 和获取新的 CSRF token
            print("🔄 正在刷新令牌...")
            response = refresh_session.get('https://juejin.cn/', timeout=15)
            
            if response.status_code == 200:
                # 从响应中提取新的 CSRF token
                import re
                csrf_match = re.search(r'window\.__NUXT__.*?csrf["\']:\s*["\']([^"\']+)["\']', response.text)
                if csrf_match:
                    new_csrf_token = csrf_match.group(1)
                    print(f"✅ 成功刷新 CSRF token")
                    
                    # 获取可能更新的 session id
                    new_session_id = base_session_id
                    for cookie in refresh_session.cookies:
                        if cookie.name == 'sessionid':
                            new_session_id = cookie.value
                            break
                    
                    return new_session_id, new_csrf_token
                else:
                    print(f"⚠️ 未能从页面中提取新的 CSRF token")
                    return None, None
            else:
                print(f"❌ 刷新请求失败: HTTP {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"❌ 刷新令牌异常: {e}")
            return None, None
    
    def refresh_from_cache(self):
        """基于缓存的令牌进行刷新"""
        cached_tokens = self.load_cached_tokens()
        if not cached_tokens:
            return None, None
        
        print("🔄 尝试基于缓存令牌进行刷新...")
        session_id, csrf_token = self.refresh_token_from_session(
            cached_tokens['session_id'], 
            cached_tokens['csrf_token']
        )
        
        if session_id and csrf_token:
            if self.test_token_validity(session_id, csrf_token):
                print("✅ 基于缓存的令牌刷新成功")
                return session_id, csrf_token
            else:
                print("⚠️ 刷新后的令牌验证失败")
        
        return None, None
    
    def refresh_from_env(self):
        """基于环境变量进行刷新（兜底）"""
        try:
            env_session_id, env_csrf_token = self.get_env_tokens()
            
            print("🔄 尝试基于环境变量令牌进行刷新...")
            session_id, csrf_token = self.refresh_token_from_session(env_session_id, env_csrf_token)
            
            if session_id and csrf_token:
                if self.test_token_validity(session_id, csrf_token):
                    print("✅ 基于环境变量的令牌刷新成功")
                    return session_id, csrf_token
                else:
                    print("⚠️ 刷新后的令牌验证失败")
            
            # 如果刷新失败，直接使用环境变量
            print("⚠️ 令牌刷新失败，直接使用环境变量")
            if self.test_token_validity(env_session_id, env_csrf_token):
                print("✅ 环境变量令牌验证成功")
                return env_session_id, env_csrf_token
            else:
                raise ValueError("环境变量中的令牌也已失效")
                
        except Exception as e:
            raise ValueError(f"基于环境变量刷新失败: {e}")
    
    def get_valid_tokens(self):
        """
        获取有效的令牌 - 每次调用都刷新
        优先级: 基于缓存刷新 → 基于环境变量刷新（兜底）
        """
        print("🔄 开始刷新掘金令牌...")
        
        # 1. 优先尝试基于缓存刷新
        session_id, csrf_token = self.refresh_from_cache()
        if session_id and csrf_token:
            # 保存刷新后的令牌到缓存
            self.save_tokens_to_cache(session_id, csrf_token)
            return session_id, csrf_token
        
        # 2. 缓存刷新失败，基于环境变量刷新（兜底）
        session_id, csrf_token = self.refresh_from_env()
        # 保存刷新后的令牌到缓存
        self.save_tokens_to_cache(session_id, csrf_token)
        return session_id, csrf_token
    
    def clear_cache(self):
        """清除令牌缓存（强制使用环境变量冷启动）"""
        try:
            if self.encrypted_token_file.exists():
                self.encrypted_token_file.unlink()
                print("✅ 已清除令牌缓存，下次运行将使用环境变量冷启动")
            else:
                print("ℹ️ 令牌缓存文件不存在")
        except Exception as e:
            print(f"❌ 清除令牌缓存失败: {e}")

def generate_encryption_key():
    """生成新的加密密钥（用于初始化）"""
    key = Fernet.generate_key()
    return key.decode()

def main():
    """主函数，用于命令行工具"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python juejin_token_manager.py refresh  - 刷新令牌")
        print("  python juejin_token_manager.py clear    - 清除缓存")
        print("  python juejin_token_manager.py genkey   - 生成加密密钥")
        return
    
    command = sys.argv[1]
    
    if command == "genkey":
        key = generate_encryption_key()
        print(f"生成的加密密钥: {key}")
        print("请将此密钥设置为 GitHub Secret: JUEJIN_ENCRYPTION_KEY")
        return
    
    try:
        manager = JuejinTokenManager()
        
        if command == "refresh":
            session_id, csrf_token = manager.get_valid_tokens()
            print("✅ 令牌刷新成功")
            print(f"Session ID: {session_id[:20]}...")
            print(f"CSRF Token: {csrf_token[:20]}...")
            exit(0)
                
        elif command == "clear":
            manager.clear_cache()
            
        else:
            print(f"未知命令: {command}")
            exit(1)
            
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        exit(1)

if __name__ == "__main__":
    main()