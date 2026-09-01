#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酷我音乐管理插件 - AstrBot 交互式菜单
版本: 2.0.1 (修复生成器调用错误)
"""
# ... (加密常量与函数同前，省略以节省篇幅，但实际代码中必须完整保留)
# 注：此处为节省显示，省略了加密常量定义，您实际使用时必须复制完整的加密部分。
# 我会在回答最后附上完整代码的下载链接或直接粘贴完整版。

import asyncio
import json
import os
import time
import re
import base64
import random
import string
import uuid
import hashlib
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from astrbot.api.all import *
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register

# ========================== 加密常量与函数（同前，此处省略，请从原代码复制） ==========================
# ... (这里必须完整粘贴 static_c, static_i 等所有加密相关数组和函数)

# ========================== 酷我 API 封装（同前） ==========================
class KuwoAPI:
    # ... 保持原样

# ========================== 插件主类 ==========================
@register("astrbot_plugin_kuwo", "YourName", "酷我音乐管理插件", "2.0.1",
          "https://github.com/YourName/astrbot_plugin_kuwo")
class KuwoPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.default_auth_limit = self.config.get('default_auth_limit', 3)
        self.verification_cron = self.config.get('verification_cron', "55 8,12,16,19 * * *")
        self.withdraw_cron = self.config.get('withdraw_cron', "59 8,12,16,19 * * *")
        self.verification_id = self.config.get('verification_id', "BVB5cctRxT%252FifPHwGzM9q2c%252BG53szUY8iDipOhkIAb%252FmSy64bK1Od%252FTftF%252F1NrBdTYm7hqnmCc3go8IWpPs80nQ%253D%253D")
        self.q36 = self.config.get('q36', "a9441d902f38da7d2d25bf1f10001a319907")
        self.kwtxid = self.config.get('kwtxid', "30002")

        self.user_menu_state = {}
        self.user_last_active = {}
        self.user_waiting_input = {}
        self.user_temp_data = {}
        self.data = {}
        self.cron_job_ids = []

    async def _load_data(self):
        self.data = await self.get_kv_data("kuwo_data", {})
        for uid in list(self.data.keys()):
            if not isinstance(self.data[uid], dict):
                self.data[uid] = {}
            if "accounts" not in self.data[uid]:
                self.data[uid]["accounts"] = []
            if "auth_limit" not in self.data[uid]:
                self.data[uid]["auth_limit"] = self.default_auth_limit
            if "daily_withdraw" not in self.data[uid]:
                self.data[uid]["daily_withdraw"] = {}
            if "verification_codes" not in self.data[uid]:
                self.data[uid]["verification_codes"] = {}
        await self._save_data()

    async def _save_data(self):
        await self.put_kv_data("kuwo_data", self.data)

    def _get_user_data(self, user_id: str) -> dict:
        if user_id not in self.data:
            self.data[user_id] = {
                "accounts": [],
                "auth_limit": self.default_auth_limit,
                "daily_withdraw": {},
                "verification_codes": {},
            }
        return self.data[user_id]

    # ==================== 菜单文本 ====================
    def _main_menu(self) -> str:
        return """🎵 酷我音乐管理菜单
请回复对应数字：
1️⃣ 绑定账号
2️⃣ 解绑账号
3️⃣ 查看已绑账号
4️⃣ 获取验证码
5️⃣ 提交验证码
6️⃣ 提现
8️⃣ 帮助
0️⃣ 退出"""

    def _get_code_menu(self) -> str:
        return """📨 获取验证码
1️⃣ 定时获取（默认 cron 55 8,12,16,19 * * *）
2️⃣ 立即获取
0️⃣ 返回主菜单"""

    def _withdraw_menu(self) -> str:
        return """💰 提现
1️⃣ 自动提现（默认 cron 59 8,12,16,19 * * *）
2️⃣ 立即提现
0️⃣ 返回主菜单"""

    def _help_text(self) -> str:
        return """📖 酷我音乐管理帮助

绑定账号：格式 手机号#密码 或 手机号#密码#授权次数（可选）
解绑账号：解绑所有已绑账号
查看账号：显示所有已绑账号及剩余授权次数
获取验证码：选择定时或立即获取，验证码将缓存用于后续提现
提交验证码：手动输入6位验证码，缓存备用
提现：选择自动（定时触发）或立即执行，按顺序使用账号，受授权次数限制
退出：退出当前菜单，120秒无操作也会自动退出"""

    # ==================== 命令入口 ====================
    @command("酷我")
    async def kuwo_menu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        self.user_menu_state[user_id] = 'main'
        self.user_last_active[user_id] = time.time()
        await self._load_data()
        yield event.plain_result(self._main_menu())

    @filter.command("酷我")
    async def kuwo_handler(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        # 超时检查
        if self.user_menu_state.get(user_id):
            last = self.user_last_active.get(user_id, 0)
            if time.time() - last > 120:
                self.user_menu_state.pop(user_id, None)
                self.user_last_active.pop(user_id, None)
                self.user_waiting_input.pop(user_id, None)
                yield event.plain_result("⏰ 操作超时，已退出菜单，请重新发送“酷我”进入。")
                return
            self.user_last_active[user_id] = time.time()
        else:
            return

        text = event.message_str.strip()
        state = self.user_menu_state.get(user_id)

        # 处理等待输入
        if self.user_waiting_input.get(user_id):
            result = await self._handle_waiting_input(user_id, text, event)
            if result:
                yield event.plain_result(result)
            return

        if state == 'main':
            result = await self._handle_main_menu(user_id, text, event)
        elif state == 'get_code':
            result = await self._handle_get_code_menu(user_id, text, event)
        elif state == 'withdraw':
            result = await self._handle_withdraw_menu(user_id, text, event)
        else:
            return

        if result:
            yield event.plain_result(result)

    # ==================== 菜单处理函数（返回消息字符串或None） ====================
    async def _handle_main_menu(self, user_id: str, text: str, event: AstrMessageEvent) -> Optional[str]:
        if text == "0":
            self.user_menu_state.pop(user_id, None)
            return "👋 已退出菜单"
        elif text == "1":
            self.user_waiting_input[user_id] = 'binding'
            return "📱 请输入要绑定的账号，格式：手机号#密码 或 手机号#密码#授权次数（可选），多个账号请用 & 分隔"
        elif text == "2":
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                user_data["accounts"] = []
                await self._save_data()
                return "✅ 已解绑所有账号"
            else:
                return "❌ 您还没有绑定任何账号"
        elif text == "3":
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                lines = [f"📱 {acc['phone']}" for acc in user_data["accounts"]]
                auth_limit = user_data["auth_limit"]
                lines.append(f"📊 总授权次数：{auth_limit}")
                return "📋 您绑定的账号：\n" + "\n".join(lines)
            else:
                return "❌ 您还没有绑定任何账号"
        elif text == "4":
            self.user_menu_state[user_id] = 'get_code'
            return self._get_code_menu()
        elif text == "5":
            self.user_waiting_input[user_id] = 'submitting_code'
            return "🔢 请输入6位验证码（从手机短信获取）"
        elif text == "6":
            self.user_menu_state[user_id] = 'withdraw'
            return self._withdraw_menu()
        elif text == "8":
            return self._help_text()
        else:
            return "❌ 无效选项，请回复数字\n" + self._main_menu()

    async def _handle_get_code_menu(self, user_id: str, text: str, event: AstrMessageEvent) -> Optional[str]:
        if text == "0":
            self.user_menu_state[user_id] = 'main'
            return self._main_menu()
        elif text == "1":
            return "⏳ 定时获取已配置，将在 cron 时间自动执行。如需立即获取请选择 2。"
        elif text == "2":
            user_data = self._get_user_data(user_id)
            accounts = user_data["accounts"]
            if not accounts:
                return "❌ 请先绑定账号"
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            daily = user_data.get("daily_withdraw", {}).get(today, {})
            if now.hour == 23:
                accounts_to_send = accounts
            else:
                accounts_to_send = [acc for acc in accounts if not daily.get(acc["phone"], False)]
            if not accounts_to_send:
                return "ℹ️ 所有账户今日已提现，无需获取验证码"
            results = await self._send_codes_batch(user_id, accounts_to_send)
            msg = "📨 验证码发送结果：\n"
            for phone, success, info in results:
                msg += f"{'✅' if success else '❌'} {phone}: {info}\n"
            return msg
        else:
            return "❌ 无效选项\n" + self._get_code_menu()

    async def _handle_withdraw_menu(self, user_id: str, text: str, event: AstrMessageEvent) -> Optional[str]:
        if text == "0":
            self.user_menu_state[user_id] = 'main'
            return self._main_menu()
        elif text == "1":
            return "⏳ 自动提现已配置，将在 cron 时间自动执行。如需立即提现请选择 2。"
        elif text == "2":
            user_data = self._get_user_data(user_id)
            accounts = user_data["accounts"]
            if not accounts:
                return "❌ 请先绑定账号"
            auth_limit = user_data["auth_limit"]
            if auth_limit > 0 and len(accounts) > auth_limit:
                accounts_to_withdraw = accounts[:auth_limit]
            else:
                accounts_to_withdraw = accounts
            results = await self._withdraw_batch(user_id, accounts_to_withdraw)
            success_count = sum(1 for r in results if r[1])
            fail_count = len(results) - success_count
            remaining = auth_limit - success_count if auth_limit > 0 else "不限"
            msg = f"📊 【立即提现完成】\n✅ 成功: {success_count} | ❌ 失败: {fail_count} | ⏭️ 跳过: 0\n📈 剩余可用次数: {remaining}\n━━━━━━━━━━━━━━━━━━\n"
            for phone, success, detail in results:
                status = "✅ 提现成功" if success else "❌ 提现失败"
                msg += f"{status} - {phone}：{detail}\n"
            return msg
        else:
            return "❌ 无效选项\n" + self._withdraw_menu()

    async def _handle_waiting_input(self, user_id: str, text: str, event: AstrMessageEvent) -> Optional[str]:
        wait_type = self.user_waiting_input.get(user_id)
        if wait_type == 'binding':
            parts = text.split('&')
            new_accounts = []
            error_msgs = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                items = part.split('#')
                if len(items) < 2:
                    error_msgs.append(f"❌ 格式错误: {part}")
                    continue
                phone = items[0].strip()
                password = items[1].strip()
                limit = None
                if len(items) >= 3 and items[2].strip().isdigit():
                    limit = int(items[2].strip())
                if not phone or not password:
                    error_msgs.append(f"❌ 手机号或密码为空: {part}")
                    continue
                new_accounts.append({"phone": phone, "password": password, "limit": limit})
            if error_msgs:
                self.user_waiting_input.pop(user_id, None)
                return "绑定失败：\n" + "\n".join(error_msgs) + "\n请重新发送“酷我”进入菜单重试。"
            if not new_accounts:
                return "未解析到有效账号，请重新输入"
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                for acc in new_accounts:
                    if acc.get("limit") is not None:
                        user_data["auth_limit"] = acc["limit"]
                        break
                existing_phones = {acc["phone"] for acc in user_data["accounts"]}
                for acc in new_accounts:
                    if acc["phone"] not in existing_phones:
                        user_data["accounts"].append({"phone": acc["phone"], "password": acc["password"]})
                        existing_phones.add(acc["phone"])
            else:
                for acc in new_accounts:
                    if acc.get("limit") is not None:
                        user_data["auth_limit"] = acc["limit"]
                        break
                user_data["accounts"] = [{"phone": acc["phone"], "password": acc["password"]} for acc in new_accounts]
            await self._save_data()
            self.user_waiting_input.pop(user_id, None)
            return f"✅ 绑定成功，共 {len(user_data['accounts'])} 个账号，总授权次数 {user_data['auth_limit']}\n" + self._main_menu()
        elif wait_type == 'submitting_code':
            code = text.strip()
            if not code.isdigit() or len(code) != 6:
                return "❌ 验证码格式错误，请输入6位数字"
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                for acc in user_data["accounts"]:
                    user_data["verification_codes"][acc["phone"]] = {"code": code, "expire": time.time() + 300}
                await self._save_data()
                self.user_waiting_input.pop(user_id, None)
                return f"✅ 验证码 {code} 已缓存，有效5分钟。\n" + self._main_menu()
            else:
                return "❌ 您还没有绑定账号，请先绑定"
        return None

    # ==================== 核心业务函数 ====================
    async def _send_codes_batch(self, user_id: str, accounts: List[dict]) -> List[Tuple[str, bool, str]]:
        results = []
        login_infos = []
        for acc in accounts:
            login_result = await asyncio.to_thread(KuwoAPI.login, acc["phone"], acc["password"])
            if login_result:
                loginUid, loginSid, appUid, encrypted_dev_id = login_result
                login_infos.append((acc["phone"], loginUid, loginSid, appUid, encrypted_dev_id))
            else:
                results.append((acc["phone"], False, "登录失败"))
        for phone, loginUid, loginSid, appUid, _ in login_infos:
            encrypted_phone = encrypt_phone(phone)
            success, info = await asyncio.to_thread(KuwoAPI.send_code, loginUid, loginSid, appUid, encrypted_phone, self.kwtxid)
            results.append((phone, success, info))
        return results

    async def _withdraw_batch(self, user_id: str, accounts: List[dict]) -> List[Tuple[str, bool, str]]:
        results = []
        user_data = self._get_user_data(user_id)
        codes = user_data.get("verification_codes", {})
        for acc in accounts:
            phone = acc["phone"]
            login_result = await asyncio.to_thread(KuwoAPI.login, phone, acc["password"])
            if not login_result:
                results.append((phone, False, "登录失败"))
                continue
            loginUid, loginSid, appUid, _ = login_result
            if await asyncio.to_thread(KuwoAPI.check_withdraw_today, loginUid, loginSid):
                results.append((phone, False, "今日已提现，跳过"))
                continue
            code_info = codes.get(phone)
            if not code_info or time.time() > code_info.get("expire", 0):
                results.append((phone, False, "验证码未获取或已过期"))
                continue
            code = code_info["code"]
            encrypted_phone = encrypt_phone(phone)
            success, detail = await asyncio.to_thread(
                KuwoAPI.withdraw_confirm,
                loginUid, loginSid, appUid, encrypted_phone,
                code, self.kwtxid, self.verification_id, self.q36
            )
            results.append((phone, success, detail))
            if success:
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in user_data["daily_withdraw"]:
                    user_data["daily_withdraw"][today] = {}
                user_data["daily_withdraw"][today][phone] = True
                await self._save_data()
        return results

    # ==================== 定时任务 ====================
    async def _setup_cron(self):
        await asyncio.sleep(3)
        scheduler = getattr(self.context, 'scheduler', None)
        if scheduler is None:
            logger.warning("当前环境不支持调度器，定时任务不可用")
            return
        try:
            job1 = scheduler.add_job(
                self._auto_get_verification_codes,
                'cron',
                id='kuwo_auto_get_code',
                **self._parse_cron(self.verification_cron)
            )
            self.cron_job_ids.append(job1.id)
            job2 = scheduler.add_job(
                self._auto_withdraw,
                'cron',
                id='kuwo_auto_withdraw',
                **self._parse_cron(self.withdraw_cron)
            )
            self.cron_job_ids.append(job2.id)
            logger.info(f"酷我插件定时任务已注册: 获取验证码 {self.verification_cron}, 提现 {self.withdraw_cron}")
        except Exception as e:
            logger.error(f"注册定时任务失败: {e}")

    def _parse_cron(self, cron_expr: str) -> dict:
        parts = cron_expr.split()
        if len(parts) == 6:
            return {
                'second': parts[0],
                'minute': parts[1],
                'hour': parts[2],
                'day': parts[3],
                'month': parts[4],
                'day_of_week': parts[5]
            }
        elif len(parts) == 5:
            return {
                'minute': parts[0],
                'hour': parts[1],
                'day': parts[2],
                'month': parts[3],
                'day_of_week': parts[4]
            }
        else:
            raise ValueError(f"cron表达式格式错误: {cron_expr}")

    async def _auto_get_verification_codes(self):
        logger.info("执行定时获取验证码任务")
        await self._load_data()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        for user_id, user_data in self.data.items():
            accounts = user_data.get("accounts", [])
            if not accounts:
                continue
            daily = user_data.get("daily_withdraw", {}).get(today, {})
            if now.hour == 23:
                accounts_to_send = accounts
            else:
                accounts_to_send = [acc for acc in accounts if not daily.get(acc["phone"], False)]
            if accounts_to_send:
                asyncio.create_task(self._send_codes_batch(user_id, accounts_to_send))

    async def _auto_withdraw(self):
        logger.info("执行自动提现任务")
        await self._load_data()
        for user_id, user_data in self.data.items():
            accounts = user_data.get("accounts", [])
            if not accounts:
                continue
            auth_limit = user_data["auth_limit"]
            if auth_limit > 0 and len(accounts) > auth_limit:
                accounts_to_withdraw = accounts[:auth_limit]
            else:
                accounts_to_withdraw = accounts
            if accounts_to_withdraw:
                asyncio.create_task(self._withdraw_batch(user_id, accounts_to_withdraw))

    # ==================== 生命周期 ====================
    async def initialize(self):
        await self._load_data()
        asyncio.create_task(self._setup_cron())

    async def terminate(self):
        scheduler = getattr(self.context, 'scheduler', None)
        if scheduler:
            for job_id in self.cron_job_ids:
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
        logger.info("酷我插件已卸载")
