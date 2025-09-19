#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

class HidenCloudSignIn:
    def __init__(self):
        """初始化配置"""
        self.login_url = 'https://dash.hidencloud.com/auth/login'
        self.service_url = os.getenv('HIDEN_SERVICE_URL', '')
        self.remember_web_cookie = os.getenv('REMEMBER_WEB_COOKIE', '')
        self.email = os.getenv('HIDEN_EMAIL', '')
        self.password = os.getenv('HIDEN_PASSWORD', '')
        self.headless = True

    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {msg}")

    def has_cookie_auth(self):
        return bool(self.remember_web_cookie)

    def has_email_auth(self):
        return bool(self.email and self.password)

    def login_with_cookie(self, context, page):
        """使用 Cookie 登录"""
        if not self.remember_web_cookie:
            self.log("未设置 REMEMBER_WEB_COOKIE，无法使用 Cookie 登录", "WARNING")
            return False
        try:
            self.log("尝试使用 REMEMBER_WEB_COOKIE 登录...")
            page.goto("https://dash.hidencloud.com", wait_until="domcontentloaded")
            session_cookie = {
                'name': 'remember_web',
                'value': self.remember_web_cookie,
                'domain': 'dash.hidencloud.com',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }
            context.add_cookies([session_cookie])
            self.log("✅ 已添加 REMEMBER_WEB_COOKIE")
            return True
        except Exception as e:
            self.log(f"设置 REMEMBER_WEB_COOKIE 时出错: {e}", "ERROR")
            return False

    def login_with_email(self, page):
        """邮箱密码登录"""
        try:
            self.log("尝试使用邮箱密码登录...")
            page.goto(self.login_url, wait_until="domcontentloaded")
            page.fill('input[name="email"]', self.email)
            page.fill('input[name="password"]', self.password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            if "login" in page.url or "auth" in page.url:
                self.log("邮箱密码登录失败", "ERROR")
                return False
            self.log("邮箱密码登录成功")
            return True
        except Exception as e:
            self.log(f"邮箱密码登录时出错: {e}", "ERROR")
            return False

    def check_renew_button(self, page):
        """检查 Renew 按钮"""
        try:
            button = page.locator('button:has-text("Renew")')
            if button.is_visible() and button.is_enabled():
                return button
            return None
        except:
            return None

    def run(self):
        if not self.service_url:
            self.log("未设置 HIDEN_SERVICE_URL", "ERROR")
            return ["error: no_service_url"]

        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            login_success = False

            # 尝试 Cookie 登录
            if self.has_cookie_auth():
                self.login_with_cookie(context, page)
                page.goto(self.service_url, wait_until="domcontentloaded")
                if "login" not in page.url and "auth" not in page.url:
                    login_success = True

            # 如果 Cookie 登录失败，尝试邮箱密码登录
            if not login_success and self.has_email_auth():
                if self.login_with_email(page):
                    login_success = True

            if not login_success:
                self.log("所有登录方式均失败", "ERROR")
                results.append("login_failed")
                browser.close()
                self.write_readme(results)
                return results

            # 访问服务页面并点击 Renew
            page.goto(self.service_url, wait_until="networkidle")
            button = self.check_renew_button(page)
            if button:
                button.click()
                time.sleep(3)
                self.log("✅ 点击 Renew 完成")
                results.append("success")
            else:
                self.log("⚠️ 未找到 Renew 按钮或已续期")
                results.append("already_renewed_or_missing")

            browser.close()
        self.write_readme(results)
        return results

    def write_readme(self, results):
        timestamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        status_map = {
            "success": "✅ 续期成功",
            "already_renewed_or_missing": "⚠️ 已续期或按钮未找到",
            "login_failed": "❌ 登录失败",
            "error: no_service_url": "❌ 未设置服务 URL"
        }
        content = f"# HidenCloud 自动签到\n\n**最后运行时间**: `{timestamp}`\n\n## 运行结果\n\n"
        for r in results:
            content += f"- {status_map.get(r, '❓ 未知状态')} \n"
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(content)
        self.log("📝 README 已更新")

if __name__ == "__main__":
    sign_in = HidenCloudSignIn()
    sign_in.run()
