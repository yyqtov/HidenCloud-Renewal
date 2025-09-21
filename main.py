#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HidenCloud 自动续期 / 签到脚本 - 多账号版本
"""

import os
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError


class HidenCloudSignIn:
    def __init__(self, account):
        """初始化，从传入的 account 字典中读取配置"""
        self.service_url = account.get('service_url', '')
        self.remember_web_cookie = account.get('remember_web_cookie', '')
        self.email = account.get('email', '')
        self.password = account.get('password', '')
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        # 使用 email 作为账号的唯一标识
        self.identifier = self.email if self.email else f"Cookie用户 (URL: {self.service_url})"

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def has_cookie_auth(self):
        return bool(self.remember_web_cookie)

    def has_email_auth(self):
        return bool(self.email and self.password)

    def login_with_cookie(self, context):
        try:
            self.log(f"账号 [{self.identifier}] 尝试使用 REMEMBER_WEB_COOKIE 登录...")
            # 注意: 此处 cookie name 和 domain 可能需要根据实际情况调整
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
            self.log(f"账号 [{self.identifier}] ✅ 已添加 REMEMBER_WEB_COOKIE")
        except Exception as e:
            self.log(f"账号 [{self.identifier}] Cookie 登录失败: {e}", "ERROR")

    def login_with_email(self, page):
        try:
            self.log(f"账号 [{self.identifier}] 尝试邮箱密码登录...")
            page.goto("https://dash.hidencloud.com/auth/login", wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="username"]', self.email)
            page.fill('input[name="password"]', self.password)
            page.click('button[type="submit"]')
            time.sleep(3)
            if "login" not in page.url and "auth" not in page.url:
                self.log(f"账号 [{self.identifier}] ✅ 邮箱密码登录成功")
                return True
            else:
                self.log(f"账号 [{self.identifier}] ❌ 邮箱密码登录失败", "ERROR")
                return False
        except Exception as e:
            self.log(f"账号 [{self.identifier}] 邮箱密码登录异常: {e}", "ERROR")
            return False

    def run(self):
        results = []
        if not self.service_url:
            self.log("未设置 HIDEN_SERVICE_URL", "ERROR")
            return ["error: no_service_url"]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            login_success = False

            if self.has_cookie_auth():
                self.login_with_cookie(context)
                try:
                    page.goto(self.service_url, wait_until="domcontentloaded", timeout=60000)
                    time.sleep(3)
                    if "login" not in page.url and "auth" not in page.url:
                        login_success = True
                    else:
                        self.log(f"账号 [{self.identifier}] ❌ Cookie 登录可能失效", "WARNING")
                except Exception as e:
                    self.log(f"账号 [{self.identifier}] 访问服务页面失败: {e}", "ERROR")

            if not login_success and self.has_email_auth():
                if self.login_with_email(page):
                    try:
                        page.goto(self.service_url, wait_until="domcontentloaded", timeout=60000)
                        time.sleep(3)
                        if "login" not in page.url and "auth" not in page.url:
                            login_success = True
                    except Exception as e:
                        self.log(f"账号 [{self.identifier}] 邮箱登录访问服务页面失败: {e}", "ERROR")

            if not login_success:
                self.log(f"账号 [{self.identifier}] 所有登录方式均失败", "ERROR")
                results.append("login_failed")
                browser.close()
                return results

            try:
                time.sleep(2)
                button = page.locator('button:has-text("Renew")')
                if button.is_visible() and button.is_enabled():
                    button.click()
                    time.sleep(3)
                    self.log(f"账号 [{self.identifier}] ✅ 点击 Renew 成功")
                    results.append("success")
                else:
                    self.log(f"账号 [{self.identifier}] ⚠️ 未找到 Renew 按钮或已续期")
                    results.append("already_renewed_or_missing")
            except Exception as e:
                self.log(f"账号 [{self.identifier}] 点击 Renew 失败: {e}", "ERROR")
                results.append("click_error")

            browser.close()
        
        return results


def generate_readme(all_results):
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
    
    for account_result in all_results:
        email = account_result['identifier']
        status_list = account_result['status']
        readme_content += f"### 账号: {email}\n"
        if not status_list:
            readme_content += "- 🤷‍♀️ 未知状态\n"
        for result in status_list:
             readme_content += f"- {status_messages.get(result, f'❓ 未知状态 ({result})')}\n"
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("📝 README 已更新")


def main():
    accounts_json = os.environ.get("ACCOUNTS_JSON")
    if not accounts_json:
        print("::error::错误：ACCOUNTS_JSON 这个 Secret 未设置。")
        generate_readme([{'identifier': '所有账号', 'status': ['❌ 未设置ACCOUNTS_JSON']}])
        sys.exit(1)

    try:
        accounts = json.loads(accounts_json)
    except json.JSONDecodeError:
        print("::error::错误：ACCOUNTS_JSON 的格式不正确，请检查。")
        generate_readme([{'identifier': '所有账号', 'status': ['❌ ACCOUNTS_JSON格式错误']}])
        sys.exit(1)

    print(f"检测到 {len(accounts)} 个账号，开始处理...")
    all_results = []
    
    for i, account in enumerate(accounts):
        identifier = account.get("email", f"账号_{i+1}")
        print(f"\n--- [账号 {i+1}/{len(accounts)}] 正在处理: {identifier} ---")
        
        if not account.get("service_url") or (not account.get("remember_web_cookie") and not (account.get("email") and account.get("password"))):
            print(f"::warning::警告：账号 {identifier} 的配置不完整（缺少 service_url 或认证信息），已跳过。")
            all_results.append({'identifier': identifier, 'status': ['❌ 配置不完整']})
            continue

        try:
            signin_instance = HidenCloudSignIn(account)
            result = signin_instance.run()
            all_results.append({'identifier': identifier, 'status': result})
        except Exception as e:
            print(f"::error::账号 {identifier} 处理时发生未知错误: {e}")
            all_results.append({'identifier': identifier, 'status': [f'💥 未知错误: {e}']})
    
    generate_readme(all_results)
    
    # 如果任何一个账号失败，则 workflow 失败
    if any("login_failed" in r['status'] or "error" in str(r['status']) for r in all_results):
        sys.exit(1)

if __name__ == "__main__":
    main()
