#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HidenCloud 自动续期 / 签到脚本 - GitHub Actions 版本
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError


class HidenCloudSignIn:
    def __init__(self):
        """初始化，从环境变量读取配置"""
        self.service_url = os.getenv('HIDEN_SERVICE_URL', '')
        self.remember_web_cookie = os.getenv('REMEMBER_WEB_COOKIE', '')
        self.email = os.getenv('HIDEN_EMAIL', '')
        self.password = os.getenv('HIDEN_PASSWORD', '')
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def has_cookie_auth(self):
        return bool(self.remember_web_cookie)

    def has_email_auth(self):
        return bool(self.email and self.password)

    def login_with_cookie(self, context, page):
        try:
            self.log("使用 REMEMBER_WEB_COOKIE 登录...")
            cookie = {
                'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                'value': self.remember_web_cookie,
                'domain': 'dash.hidencloud.com',
                'path': '/',
                'expires': int(time.time()) + 3600 * 24 * 365,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }
            context.add_cookies([cookie])
            self.log("✅ 已添加 REMEMBER_WEB_COOKIE")
        except Exception as e:
            self.log(f"Cookie 登录失败: {e}", "ERROR")

    def login_with_email(self, page):
        try:
            self.log("尝试邮箱密码登录...")
            page.goto("https://dash.hidencloud.com/auth/login", wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="username"]', self.email)
            page.fill('input[name="password"]', self.password)
            page.click('button[type="submit"]')
            time.sleep(3)
            if "login" not in page.url and "auth" not in page.url:
                self.log("✅ 邮箱密码登录成功")
                return True
            else:
                self.log("❌ 邮箱密码登录失败", "ERROR")
                return False
        except Exception as e:
            self.log(f"邮箱密码登录异常: {e}", "ERROR")
            return False

    def run(self):
        results = []
        if not self.service_url:
            self.log("未设置 HIDEN_SERVICE_URL", "ERROR")
            self.write_readme(["error: no_service_url"])
            return ["error: no_service_url"]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            login_success = False

            # 尝试 Cookie 登录
            if self.has_cookie_auth():
                self.login_with_cookie(context, page)
                try:
                    page.goto(self.service_url, wait_until="domcontentloaded", timeout=60000)
                    time.sleep(3)
                    if "login" not in page.url and "auth" not in page.url:
                        login_success = True
                    else:
                        self.log("❌ Cookie 登录可能失效", "WARNING")
                except Exception as e:
                    self.log(f"访问服务页面失败: {e}", "ERROR")

            # Cookie 登录失败则邮箱密码登录
            if not login_success and self.has_email_auth():
                if self.login_with_email(page):
                    try:
                        page.goto(self.service_url, wait_until="domcontentloaded", timeout=60000)
                        time.sleep(3)
                        if "login" not in page.url and "auth" not in page.url:
                            login_success = True
                    except Exception as e:
                        self.log(f"邮箱登录访问服务页面失败: {e}", "ERROR")

            if not login_success:
                self.log("所有登录方式均失败", "ERROR")
                results.append("login_failed")
                browser.close()
                self.write_readme(results)
                return results

            # 点击 Renew 按钮
            try:
                time.sleep(2)
                button = page.locator('button:has-text("Renew")')
                if button.is_visible() and button.is_enabled():
                    button.click()
                    time.sleep(3)
                    self.log("✅ 点击 Renew 成功")
                    results.append("success")
                else:
                    self.log("⚠️ 未找到 Renew 按钮或已续期")
                    results.append("already_renewed_or_missing")
            except Exception as e:
                self.log(f"点击 Renew 失败: {e}", "ERROR")
                results.append("click_error")

            browser.close()

        self.write_readme(results)
        return results

    def write_readme(self, results):
        beijing_time = datetime.now(timezone(timedelta(hours=8)))
        timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        status_messages = {
            "success": "✅ 续期成功",
            "already_renewed_or_missing": "⚠️ 已经续期或按钮未找到",
            "click_error": "💥 点击按钮出错",
            "login_failed": "❌ 登录失败",
            "error: no_service_url": "❌ 未设置服务URL"
        }

        readme_content = f"# HidenCloud 自动续期脚本\n\n**最后运行时间**: `{timestamp}` (北京时间)\n\n## 运行结果\n\n"
        for result in results:
            readme_content += f"- {status_messages.get(result, f'❓ 未知状态 ({result})')}\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        self.log("📝 README 已更新")


def main():
    sign_in = HidenCloudSignIn()

    if not sign_in.has_cookie_auth() and not sign_in.has_email_auth():
        print("❌ 未设置认证信息！请在 GitHub Secrets 中设置 REMEMBER_WEB_COOKIE 或 HIDEN_EMAIL/HIDEN_PASSWORD")
        sys.exit(1)

    if not sign_in.service_url:
        print("❌ 未设置 HIDEN_SERVICE_URL")
        sys.exit(1)

    results = sign_in.run()
    if any("login_failed" in r or "error" in r for r in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
