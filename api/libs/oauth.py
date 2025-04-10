import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class OAuthUserInfo:
    id: str
    name: str
    email: str


class OAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self):
        raise NotImplementedError()

    def get_access_token(self, code: str):
        raise NotImplementedError()

    def get_raw_user_info(self, token: str):
        raise NotImplementedError()

    def get_user_info(self, token: str) -> OAuthUserInfo:
        raw_info = self.get_raw_user_info(token)
        return self._transform_user_info(raw_info)

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        raise NotImplementedError()


class GitHubOAuth(OAuth):
    _AUTH_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _USER_INFO_URL = "https://api.github.com/user"
    _EMAIL_INFO_URL = "https://api.github.com/user/emails"

    def get_authorization_url(self, invite_token: Optional[str] = None):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",  # Request only basic user information
        }
        if invite_token:
            params["state"] = invite_token
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = requests.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = response.json()
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in GitHub OAuth: {response_json}")

        return access_token

    def get_raw_user_info(self, token: str):
        headers = {"Authorization": f"token {token}"}
        response = requests.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        email_response = requests.get(self._EMAIL_INFO_URL, headers=headers)
        email_info = email_response.json()
        primary_email: dict = next((email for email in email_info if email["primary"] == True), {})

        return {**user_info, "email": primary_email.get("email", "")}

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        email = raw_info.get("email")
        if not email:
            email = f"{raw_info['id']}+{raw_info['login']}@users.noreply.github.com"
        return OAuthUserInfo(id=str(raw_info["id"]), name=raw_info["name"], email=email)


class GoogleOAuth(OAuth):
    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_authorization_url(self, invite_token: Optional[str] = None):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "openid email",
        }
        if invite_token:
            params["state"] = invite_token
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = requests.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = response.json()
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in Google OAuth: {response_json}")

        return access_token

    def get_raw_user_info(self, token: str):
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        return OAuthUserInfo(id=str(raw_info["sub"]), name="", email=raw_info["email"])

class AILabOAuth(OAuth):
    """
    AI实验平台 OAuth provider for integrating with AI实验平台
    """
    _AUTH_URL = "https://industry-jystudy2.app.codewave.163.com/oauth/authorize"
    _TOKEN_URL = "https://industry-jystudy2.app.codewave.163.com/rest/token"
    _USER_INFO_URL = "https://industry-jystudy2.app.codewave.163.com/rest/userinfo"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)

    def get_authorization_url(self, invite_token: Optional[str] = None):
        """Generate the authorization URL for the OAuth flow"""
        params = {
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id
        }
        
        if invite_token:
            params["state"] = invite_token
            
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str):
        """Exchange authorization code for access token"""
        # 确保code是字符串
        code_value = code
        if isinstance(code, list) and len(code) > 0:
            code_value = code[0]
        
        # 打印接收到的code参数
        print(f"Received code: {code_value}")
        
        # 参考提供的OAuth配置参数
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code_value,
            "redirect_uri": self.redirect_uri
        }
        
        # 打印请求内容用于调试
        print(f"Token request data: {data}")
        print(f"Token URL: {self._TOKEN_URL}")
        
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        response = requests.post(self._TOKEN_URL, json=data, headers=headers)
        
        print(f"Token response: {response.text}")
        
        response_json = response.json()
        
        # 处理嵌套的JSON响应格式
        if "data" in response_json and isinstance(response_json["data"], dict):
            # 认证中心返回的格式是 {"code": 200, "msg": "...", "data": {"access_token": "..."}}
            access_token = response_json["data"].get("access_token")
        else:
            # 标准OAuth格式的直接返回 {"access_token": "..."}
            access_token = response_json.get("access_token")
        
        if not access_token:
            raise ValueError(f"Error in AI实验平台 OAuth: {response_json}")
            
        return access_token

    def get_raw_user_info(self, token: str):
        """Get user information using the access token"""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.get(self._USER_INFO_URL, headers=headers)
        
        print(f"User info response: {response.text}")
        
        if response.status_code != 200:
            raise ValueError(f"Error getting user info: {response.text}")
        
        response_json = response.json()
        
        # 处理嵌套的JSON响应格式
        if "data" in response_json and isinstance(response_json["data"], dict):
            # 认证中心返回的格式是 {"code": 200, "msg": "...", "data": {...}}
            return response_json["data"]
        
        return response_json

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        """Transform the raw user info into a standard format"""
        # 使用提供的登录配置参数中的映射关系获取用户信息
        user_id = str(raw_info.get("userId", ""))
        user_name = raw_info.get("username", "")  # 使用username作为name
        display_name = raw_info.get("displayName", "")
        name = display_name or user_name
        
        # 直接获取email字段
        email = raw_info.get("email", "")
        
        # 如果没有邮箱，生成一个默认邮箱
        if not email:
            email = f"{user_name}@example.com"
        
        return OAuthUserInfo(
            id=user_id,
            name=name,
            email=email
        )
