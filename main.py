#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

class HidenCloudSignIn:
    def __init__(self):
        self.login_url = 'https://dash.hidencloud.com/auth/login'
        self.service_url = os.getenv('HIDEN_SERVICE_URL', '')
        self.email = os.getenv('HIDEN_EMAIL', '')
        self.password = os.getenv('HIDEN_PASSWORD', '')
        self.cookie = os.getenv('HIDEN_COOKIE', '')
        self.headless = True

    def log(self, msg):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    def login_with_email(self, page):
        self.log("使用邮箱密码登录...")
        page.goto(self.login_url, wait_until="domcontentloaded")
        page.fill('input[name="email"]', self.email)
        page.fill('input[name="password"]', self.password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        if "login" in page.url or "auth" in page.url:
            self.log("登录失败")
            return False
        self.log("登录成功")
        return True

    def login_with_cookie(self, context):
        if not self.cookie:
            return False
        self.log("使用 Cookie 登录...")
        session_cookie = {
            'name': 'remember_web',
            'value': self.cookie,
            'domain': 'dash.hidencloud.com',
            'path': '/',
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        }
        context.add_cookies([session_cookie])
        return True

    def check_renew_button(self, page):
        try:
            button = page.locator('button:has-text("Renew")')
            if button.is_visible() and button.is_enabled():
                return button
            return None
        except:
            return None

    def run(self):
        if not self.service_url:
            self.log("未设置服务 URL")
            return "error: no_service_url"
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            login_success = False

            if self.cookie:
                self.login_with_cookie(context)
                page.goto(self.service_url, wait_until="domcontentloaded")
                if "login" not in page.url and "auth" not in page.url:
                    login_success = True

            if not login_success and self.email and self.password:
                if self.login_with_email(page):
                    login_success = True

            if not login_success:
                self.log("登录失败")
                results.append("login_failed")
                browser.close()
                return results

            page.goto(self.service_url, wait_until="networkidle")
            button = self.check_renew_button(page)
            if button:
                button.click()
                time.sleep(3)
                self.log("点击 Renew 完成")
                results.append("success")
            else:
                self.log("未找到 Renew 按钮或已续期")
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
        self.log("README 已更新")

if __name__ == "__main__":
    sign_in = HidenCloudSignIn()
    sign_in.run()
