#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import time
import re
import base64
import random
import string
import uuid
import hashlib
from datetime import datetime
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from urllib.parse import quote

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger

# ======================================================================
# 1. 加密常量（完整，省略以节省篇幅，实际请保留完整）
# ======================================================================
# ...（此处省略，与之前完全相同，请复制您原有的常量部分）
# 注意：实际代码中必须包含 static_c, static_i, ... 等所有常量定义
# 由于回答长度限制，此处不重复粘贴，但您必须保留它们。

# ======================================================================
# 2. 酷我 API 函数（完整，省略）
# ======================================================================
# ...（与之前完全相同，请保留 login_kuwo, check_withdraw_today, send_code_once, withdraw_confirm_once 等）
# 同样，这些函数与之前完全相同，此处不重复。

# ======================================================================
# 3. AstrBot 插件主类（修改版）
# ======================================================================
class KuwoPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.default_auth_limit = self.config.get('default_auth_limit', 3)
        self.verification_cron = self.config.get('verification_cron', "12 55 8,12,16,19 * * *")
        self.verification_id = self.config.get('verification_id', "BVB5cctRxT%252FifPHwGzM9q2c%252BG53szUY8iDipOhkIAb%252FmSy64bK1Od%252FTftF%252F1NrBdTYm7hqnmCc3go8IWpPs80nQ%253D%253D")
        self.q36 = self.config.get('q36', "a9441d902f38da7d2d25bf1f10001a319907")
        self.kwtxid = self.config.get('kwtxid', "30002")
        self.timeout = self.config.get('timeout', 120)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay_ms = self.config.get('retry_delay_ms', 4000)
        self.quota_id = self.config.get('quota_id', "60004")

        self.states = {}
        self.TIMEOUT = self.timeout
        self.timeout_tasks = {}

    # ---------- 数据持久化（与之前相同） ----------
    async def _load_data(self, user_id: str) -> dict:
        data = await self.get_kv_data("kuwo_data", {})
        if user_id not in data:
            data[user_id] = {
                "accounts": [],
                "auth_limit": self.default_auth_limit,
                "daily_withdraw": {},
                "verification_codes": {},
                "cron": self.verification_cron
            }
            await self.put_kv_data("kuwo_data", data)
        return data[user_id]

    async def _save_data(self, user_id: str, user_data: dict):
        data = await self.get_kv_data("kuwo_data", {})
        data[user_id] = user_data
        await self.put_kv_data("kuwo_data", data)

    # ---------- 状态管理（与之前相同） ----------
    def _get_state(self, user_id: str) -> dict:
        if user_id not in self.states:
            self.states[user_id] = {
                'menu': None,
                'step': None,
                'last_active': time.time(),
                'tmp_data': {},
                'umo': None,
            }
        return self.states[user_id]

    def _update_state(self, user_id: str, **kwargs):
        state = self._get_state(user_id)
        for key, value in kwargs.items():
            state[key] = value
        state['last_active'] = time.time()

    def _clear_state(self, user_id: str):
        if user_id in self.states:
            del self.states[user_id]
        if user_id in self.timeout_tasks:
            self.timeout_tasks[user_id].cancel()
            del self.timeout_tasks[user_id]

    def _cancel_timeout(self, user_id: str):
        if user_id in self.timeout_tasks:
            self.timeout_tasks[user_id].cancel()
            del self.timeout_tasks[user_id]

    # ---------- 超时管理（与之前相同） ----------
    async def _timeout_callback(self, user_id: str):
        state = self._get_state(user_id)
        if state.get('menu') or state.get('step'):
            umo = state.get('umo')
            if umo:
                try:
                    await self.context.send_message(umo, MessageChain().message("⏰ 操作已超时，已退出交互。"))
                except:
                    pass
            self._clear_state(user_id)

    def _schedule_timeout(self, user_id: str):
        if user_id in self.timeout_tasks:
            self.timeout_tasks[user_id].cancel()
        task = asyncio.create_task(self._timeout_after_delay(user_id))
        self.timeout_tasks[user_id] = task

    async def _timeout_after_delay(self, user_id: str):
        try:
            await asyncio.sleep(self.TIMEOUT)
            await self._timeout_callback(user_id)
        except asyncio.CancelledError:
            pass

    # ---------- 菜单 ----------
    def _main_menu(self) -> str:
        return (
            "🎵 酷我音乐管理菜单\n"
            "1️⃣ 账号管理\n"
            "2️⃣ 获取验证码\n"
            "3️⃣ 提交验证码\n"
            "4️⃣ 设置定时规则\n"
            "5️⃣ 立即提现\n"
            "6️⃣ 帮助\n"
            "0️⃣ 退出"
        )

    def _account_menu(self) -> str:
        return (
            "📂 账号管理\n"
            "1️⃣ 绑定账号\n"
            "2️⃣ 解绑账号\n"
            "3️⃣ 查看账号\n"
            "0️⃣ 返回主菜单"
        )

    def _verify_menu(self) -> str:
        return (
            "📨 获取验证码\n"
            "1️⃣ 立即获取\n"
            "2️⃣ 定时获取（默认12 55 8,12,16,19 * * *）\n"
            "3️⃣ 设置定时规则\n"
            "0️⃣ 返回主菜单"
        )

    # ---------- 命令入口 ----------
    @filter.command("酷我")
    async def kuwo_menu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        self._update_state(user_id, menu='main', step=None, umo=event.unified_msg_origin)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._main_menu())

    # ---------- 主菜单数字选择（更新序号） ----------
    @filter.regex(r'^[0-6]$')
    async def handle_main_choice(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'main' or state.get('step'):
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        text = event.message_str.strip()
        umo = event.unified_msg_origin

        if text == "0":
            self._clear_state(user_id)
            yield event.plain_result("👋 已退出菜单")
            return

        elif text == "1":
            self._update_state(user_id, menu='account', step=None)
            yield event.plain_result(self._account_menu())

        elif text == "2":
            self._update_state(user_id, menu='verify', step=None)
            yield event.plain_result(self._verify_menu())

        elif text == "3":
            user_data = await self._load_data(user_id)
            if not user_data["accounts"]:
                yield event.plain_result("❌ 您还没有绑定账号")
                yield event.plain_result(self._main_menu())
                return
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(user_data["accounts"])]
            prompt = "请选择要提交验证码的账号序号：\n" + "\n".join(lines) + "\n请输入序号，输入 0 取消："
            yield event.plain_result(prompt)
            self._update_state(user_id, step='waiting_code_phone', tmp_data={'accounts': user_data["accounts"], 'trigger_msg': text})

        elif text == "4":
            self._update_state(user_id, step='set_cron')
            current_cron = (await self._load_data(user_id)).get("cron", "未设置")
            yield event.plain_result(f"📝 当前定时规则：{current_cron}\n请输入新的cron表达式（格式：秒 分 时 日 月 周）\n例如：12 55 8,12,16,19 * * *\n输入 0 取消，输入 off 关闭定时。")

        elif text == "5":
            await self._do_withdraw(user_id, event)

        elif text == "6":
            yield event.plain_result("帮助：发送“酷我”进入菜单，回复数字操作。\n120秒无操作自动退出。")
            yield event.plain_result(self._main_menu())

    # ---------- 账号管理子菜单 ----------
    @filter.regex(r'^[0-3]$')
    async def handle_account_choice(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'account' or state.get('step'):
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        elif text == "1":  # 绑定
            self._update_state(user_id, step='binding')
            yield event.plain_result("📱 请输入手机号#密码（可多个用 & 分隔），输入 0 取消")

        elif text == "2":  # 解绑
            user_data = await self._load_data(user_id)
            if not user_data["accounts"]:
                yield event.plain_result("❌ 您还没有绑定任何账号")
                self._update_state(user_id, menu='account', step=None)
                yield event.plain_result(self._account_menu())
                return
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(user_data["accounts"])]
            prompt = "您的账号：\n" + "\n".join(lines) + "\n请输入要删除的序号（如 1），输入 0 取消："
            yield event.plain_result(prompt)
            self._update_state(user_id, step='waiting_delete', tmp_data={'accounts': user_data["accounts"], 'trigger_msg': text})

        elif text == "3":  # 查看
            user_data = await self._load_data(user_id)
            if user_data["accounts"]:
                lines = [f"📱 {a['phone']}" for a in user_data["accounts"]]
                lines.append(f"📊 剩余授权次数：{user_data['auth_limit']}")
                yield event.plain_result("📋 您绑定的账号：\n" + "\n".join(lines))
            else:
                yield event.plain_result("❌ 您还没有绑定任何账号")
            self._update_state(user_id, menu='account', step=None)
            yield event.plain_result(self._account_menu())

    # ---------- 提现逻辑（与之前相同） ----------
    async def _do_withdraw(self, user_id: str, event: AstrMessageEvent):
        user_data = await self._load_data(user_id)
        if not user_data["accounts"]:
            yield event.plain_result("❌ 请先绑定账号")
            yield event.plain_result(self._main_menu())
            return
        if user_data["auth_limit"] <= 0:
            yield event.plain_result("❌ 授权次数已用完")
            yield event.plain_result(self._main_menu())
            return

        accounts = user_data["accounts"][:user_data["auth_limit"]]
        results = []
        success_count = 0
        codes = user_data.get("verification_codes", {})

        for acc in accounts:
            phone = acc["phone"]
            code_info = codes.get(phone)
            if not code_info or time.time() > code_info.get("expire", 0):
                results.append(f"❌ {phone}: 验证码未获取或已过期")
                continue

            login = login_kuwo(phone, acc["password"])
            if not login:
                results.append(f"❌ {phone}: 登录失败")
                continue
            uid, sid, appuid, _ = login

            if check_withdraw_today(uid, sid):
                results.append(f"⏭️ {phone}: 今日已提现，跳过")
                continue

            encrypted_phone = encrypt_phone(phone)
            code = code_info["code"]
            log_lines, final_msg, is_success = withdraw_confirm_once(
                phone, uid, sid, appuid, encrypted_phone, code,
                self.kwtxid, self.verification_id, self.q36,
                seq=1, max_extra_retries=self.max_retries, retry_delay_ms=self.retry_delay_ms
            )
            if is_success:
                success_count += 1
                user_data["auth_limit"] -= 1
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in user_data["daily_withdraw"]:
                    user_data["daily_withdraw"][today] = {}
                user_data["daily_withdraw"][today][phone] = True
                await self._save_data(user_id, user_data)
                results.append(f"✅ 提现成功 {phone}: {final_msg}")
            else:
                results.append(f"❌ 提现失败 {phone}: {final_msg}")

        summary = f"📊 【提现完成】\n✅ 成功: {success_count} | ❌ 失败: {len(results)-success_count}\n📈 剩余可用次数: {user_data['auth_limit']}\n━━━━━━━━━━━━\n"
        yield event.plain_result(summary + "\n".join(results))
        yield event.plain_result(self._main_menu())

    # ---------- 验证码子菜单（与之前相同） ----------
    @filter.regex(r'^[0-3]$')
    async def handle_verify_choice(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'verify' or state.get('step'):
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        elif text == "1":
            setattr(event, '_verify_choice_processed', True)
            logger.info(f"用户 {user_id} 选择立即获取验证码")
            result_msg = await self._do_send_code(user_id)
            if result_msg:
                yield event.plain_result(result_msg)
            else:
                yield event.plain_result("⚠️ 内部错误，未能获取验证码菜单，请重试或重新绑定账号。")
            return

        elif text == "2":
            user_data = await self._load_data(user_id)
            cron = user_data.get("cron", self.verification_cron)
            yield event.plain_result(f"⏰ 定时获取已配置（{cron}），但本版本暂不实现实际定时功能，请使用立即获取。")
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())

        elif text == "3":
            self._update_state(user_id, step='set_cron')
            current_cron = (await self._load_data(user_id)).get("cron", "未设置")
            yield event.plain_result(f"📝 当前定时规则：{current_cron}\n请输入新的cron表达式（格式：秒 分 时 日 月 周）\n例如：12 55 8,12,16,19 * * *\n输入 0 取消，输入 off 关闭定时。")

    # ---------- 设置定时规则输入处理 ----------
    @filter.regex(r'^(\d+\s+.*|off|0)$')
    async def handle_set_cron_input(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'set_cron':
            return

        text = event.message_str.strip().lower()
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        if text == "off":
            user_data = await self._load_data(user_id)
            user_data["cron"] = ""
            await self._save_data(user_id, user_data)
            yield event.plain_result("✅ 已关闭定时获取验证码")
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        parts = text.split()
        if len(parts) not in (5, 6):
            yield event.plain_result("❌ cron表达式格式错误，应为5或6个字段，请重新输入")
            return

        user_data = await self._load_data(user_id)
        user_data["cron"] = text
        await self._save_data(user_id, user_data)

        yield event.plain_result(f"✅ 定时规则已更新：{text}\n⚠️ 注意：当前环境不支持调度器，定时自动获取功能不可用，请使用立即获取。")
        self._update_state(user_id, menu='main', step=None)
        yield event.plain_result(self._main_menu())

    # ---------- 发送验证码 ----------
    async def _do_send_code(self, user_id: str) -> str:
        logger.info(f"🟢 _do_send_code 被调用，用户 {user_id}")
        user_data = await self._load_data(user_id)
        accounts = user_data.get("accounts", [])
        logger.info(f"用户 {user_id} 当前账号数量: {len(accounts)}")

        if not accounts:
            logger.warning("账号列表为空")
            self._update_state(user_id, menu='main', step=None)
            return "❌ 您还没有绑定任何账号\n" + self._main_menu()

        try:
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(accounts)]
        except Exception as e:
            logger.error(f"构建账号列表时出错: {e}", exc_info=True)
            self._update_state(user_id, menu='main', step=None)
            return "❌ 账号数据格式异常，请重新绑定\n" + self._main_menu()

        prompt = "📨 请输入要发送验证码的账号序号（多个用逗号分隔），输入 all 发送全部，输入 0 返回：\n" + "\n".join(lines)
        self._update_state(user_id, step='waiting_send_select', tmp_data={'accounts': accounts})
        logger.info(f"返回提示: {prompt[:50]}...")
        return prompt

    # ---------- 处理发送验证码的选择 ----------
    @filter.regex(r'^(all|[\d,]+|0|q|Q)$')
    async def handle_send_select(self, event: AstrMessageEvent):
        if getattr(event, '_verify_choice_processed', False):
            return

        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_send_select':
            return

        text = event.message_str.strip().lower()
        if text in ("0", "q"):
            self._update_state(user_id, menu='verify', step=None)
            yield event.plain_result(self._verify_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        accounts = state.get('tmp_data', {}).get('accounts', [])

        phones_to_send = []
        if text == "all":
            phones_to_send = [acc["phone"] for acc in accounts]
        else:
            indices = text.split(',')
            try:
                for idx_str in indices:
                    idx = int(idx_str.strip()) - 1
                    if 0 <= idx < len(accounts):
                        phones_to_send.append(accounts[idx]["phone"])
                    else:
                        yield event.plain_result(f"❌ 序号 {idx_str} 无效，请重新输入")
                        return
            except ValueError:
                yield event.plain_result("❌ 输入格式错误，请输入数字序号（用逗号分隔）或 all")
                return

        if not phones_to_send:
            yield event.plain_result("❌ 未选择任何账号")
            self._update_state(user_id, menu='verify', step=None)
            yield event.plain_result(self._verify_menu())
            return

        results = []
        for phone in phones_to_send:
            password = None
            for acc in accounts:
                if acc["phone"] == phone:
                    password = acc["password"]
                    break
            if not password:
                results.append(f"❌ {phone}: 未找到密码")
                continue

            login = login_kuwo(phone, password)
            if not login:
                results.append(f"❌ {phone}: 登录失败")
                continue
            uid, sid, appuid, _ = login
            encrypted_phone = encrypt_phone(phone)
            if check_withdraw_today(uid, sid):
                results.append(f"⏭️ {phone}: 今日已提现，跳过")
                continue
            success, msg = send_code_once(uid, sid, appuid, encrypted_phone, self.quota_id)
            results.append(f"{'✅' if success else '❌'} {phone}: {msg}")

        yield event.plain_result("📨 验证码发送结果：\n" + "\n".join(results))
        self._update_state(user_id, menu='main', step=None)
        yield event.plain_result(self._main_menu())

    # ---------- 提交验证码 - 选择账号 ----------
    @filter.regex(r'^\d+$')
    async def handle_code_phone_select(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_code_phone':
            return

        text = event.message_str.strip()
        if text == state.get('tmp_data', {}).get('trigger_msg'):
            return

        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        try:
            idx = int(text)
        except:
            yield event.plain_result("❌ 请输入有效的数字")
            return

        accounts = state.get('tmp_data', {}).get('accounts', [])
        if idx < 1 or idx > len(accounts):
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(accounts)} 之间的数字")
            return

        phone = accounts[idx-1]["phone"]
        self._update_state(user_id, step='waiting_code_input', tmp_data={'phone': phone})
        yield event.plain_result(f"已选择账号 {phone}，请输入验证码（发送 q 取消）：")

    # ---------- 提交验证码 - 输入验证码 ----------
    @filter.regex(r'^.+$')
    async def handle_code_input(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_code_input':
            return

        text = event.message_str.strip()
        if text in ("0", "q", "Q"):
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        code = text
        if not code:
            yield event.plain_result("❌ 验证码不能为空")
            return

        phone = state.get('tmp_data', {}).get('phone')
        if not phone:
            yield event.plain_result("❌ 会话错误，请重新操作")
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(self._main_menu())
            return

        user_data = await self._load_data(user_id)
        user_data["verification_codes"][phone] = {"code": code, "expire": time.time() + 300}
        await self._save_data(user_id, user_data)

        yield event.plain_result(f"✅ 验证码 {code} 已缓存（5分钟有效）")
        self._update_state(user_id, menu='main', step=None)
        yield event.plain_result(self._main_menu())

    # ---------- 绑定输入处理 ----------
    @filter.regex(r'^(0|\d{11}#.+)$')
    async def handle_binding_input(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'binding':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='account', step=None)
            yield event.plain_result(self._account_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        parts = text.split('&')
        user_data = await self._load_data(user_id)
        new_accounts = []
        errors = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                phone, password = part.split('#', 1)
                phone = phone.strip()
                password = password.strip()
                if not phone or not password:
                    errors.append(f"格式错误: {part}")
                    continue
                existing = [a for a in user_data["accounts"] if a["phone"] == phone]
                if existing:
                    existing[0]["password"] = password
                else:
                    new_accounts.append({"phone": phone, "password": password})
            except ValueError:
                errors.append(f"格式错误: {part}")

        if errors:
            yield event.plain_result("❌ 绑定失败：\n" + "\n".join(errors) + "\n请重新输入")
            return

        if new_accounts:
            user_data["accounts"].extend(new_accounts)
            await self._save_data(user_id, user_data)
            yield event.plain_result(f"✅ 成功绑定 {len(new_accounts)} 个账号，当前共 {len(user_data['accounts'])} 个账号")
        else:
            yield event.plain_result("✅ 账号信息已更新（无新增）")

        self._update_state(user_id, menu='account', step=None)
        yield event.plain_result(self._account_menu())

    # ---------- 删除账号 ----------
    @filter.regex(r'^\d+$')
    async def handle_delete_index(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_delete':
            return

        text = event.message_str.strip()
        if text == state.get('tmp_data', {}).get('trigger_msg'):
            return

        if text == "0":
            self._update_state(user_id, menu='account', step=None)
            yield event.plain_result(self._account_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        try:
            idx = int(text)
        except:
            yield event.plain_result("❌ 请输入有效的数字")
            self._update_state(user_id, menu='account', step=None)
            yield event.plain_result(self._account_menu())
            return

        accounts = state.get('tmp_data', {}).get('accounts', [])
        if idx < 1 or idx > len(accounts):
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(accounts)} 之间的数字")
            return

        user_data = await self._load_data(user_id)
        phone_to_del = accounts[idx-1]["phone"]
        user_data["accounts"] = [acc for acc in user_data["accounts"] if acc["phone"] != phone_to_del]
        await self._save_data(user_id, user_data)

        yield event.plain_result(f"✅ 已删除账号 {phone_to_del}")
        self._update_state(user_id, menu='account', step=None)
        yield event.plain_result(self._account_menu())

    # ---------- 全局 q 退出 ----------
    @filter.regex(r'^[qQ]$')
    async def handle_global_q(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)

        if state.get('step') or state.get('menu'):
            self._clear_state(user_id)
            yield event.plain_result("👋 已取消当前操作，返回主菜单")
            yield event.plain_result(self._main_menu())
        else:
            yield event.plain_result("👋 已退出")

    # ---------- 生命周期 ----------
    async def initialize(self):
        logger.info("✅ 酷我插件 2.2.5 账号管理整合版已加载")

    async def terminate(self):
        logger.info("✅ 酷我插件已卸载")
