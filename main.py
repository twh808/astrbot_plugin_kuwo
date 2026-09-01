"""
astrbot_plugin_kuwo - 酷我音乐管理插件
功能：交互式菜单，支持账号绑定、解绑、查看、验证码、提现（模拟）
数据持久化：存储在 data/kuwo_data.json
"""

import json
import os
from typing import Dict, Optional

# AstrBot 核心 API
from astrbot.api.all import *
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register

# ==================== 数据目录配置 ====================
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "kuwo_data.json")
os.makedirs(DATA_DIR, exist_ok=True)  # 确保数据目录存在


# ==================== 数据管理器 ====================
class KuwoDataManager:
    """负责用户数据的读写和账号绑定管理"""

    def __init__(self):
        self.data: Dict = self._load_data()

    def _load_data(self) -> Dict:
        """从 JSON 文件加载数据，若文件不存在或损坏则返回空字典"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_data(self):
        """将内存数据写入 JSON 文件"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"⚠️ 保存数据失败: {e}")

    # ---------- 用户基本操作 ----------
    def get_user(self, user_id: str) -> Optional[Dict]:
        return self.data.get(user_id)

    def set_user(self, user_id: str, user_data: Dict):
        self.data[user_id] = user_data
        self._save_data()

    def delete_user(self, user_id: str) -> bool:
        if user_id in self.data:
            del self.data[user_id]
            self._save_data()
            return True
        return False

    # ---------- 账号绑定操作 ----------
    def get_bound_account(self, user_id: str) -> Optional[str]:
        user = self.get_user(user_id)
        return user.get("account") if user else None

    def bind_account(self, user_id: str, account: str):
        user = self.get_user(user_id) or {}
        user["account"] = account
        self.set_user(user_id, user)

    def unbind_account(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if user and "account" in user:
            del user["account"]
            self.set_user(user_id, user)
            return True
        return False


# ==================== 插件主类 ====================
@register("astrbot_plugin_kuwo", "YourName", "酷我音乐管理插件", "1.0.0",
          "https://github.com/YourName/astrbot_plugin_kuwo")
class KuwoPlugin(Star):
    """酷我音乐管理交互式菜单插件"""

    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.data_manager = KuwoDataManager()

        # 用户状态管理
        self.user_menu_state: Dict[str, bool] = {}        # 是否在菜单模式
        self.user_waiting_state: Dict[str, str] = {}      # 等待输入类型: 'binding' / 'verifying'

    # ---------- 菜单文本 ----------
    def _get_menu_text(self) -> str:
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

    def _get_help_text(self) -> str:
        return """📖 酷我音乐管理帮助

1. 绑定账号 - 输入手机号/邮箱绑定酷我账号
2. 解绑账号 - 解绑当前绑定的账号
3. 查看已绑账号 - 查看当前绑定的账号信息
4. 获取验证码 - 向绑定的手机号发送验证码（模拟）
5. 提交验证码 - 提交验证码完成验证（模拟）
6. 提现 - 提现账户余额（模拟）
8. 帮助 - 显示此帮助信息
0. 退出 - 退出当前菜单"""

    # ---------- 状态管理辅助方法 ----------
    def _set_waiting(self, user_id: str, state: str):
        self.user_waiting_state[user_id] = state

    def _get_waiting(self, user_id: str) -> Optional[str]:
        return self.user_waiting_state.get(user_id)

    def _clear_waiting(self, user_id: str):
        if user_id in self.user_waiting_state:
            del self.user_waiting_state[user_id]

    # ---------- 主命令：显示菜单 ----------
    @command("kuwo")
    async def kuwo_menu(self, event: AstrMessageEvent):
        """用户发送 'kuwo' 时进入菜单"""
        user_id = event.get_sender_id()
        self.user_menu_state[user_id] = True
        yield event.plain_result(self._get_menu_text())

    # ---------- 菜单选项处理器 ----------
    @filter.command("kuwo")
    async def kuwo_handler(self, event: AstrMessageEvent):
        """处理菜单中的数字选择或用户输入"""
        user_id = event.get_sender_id()

        # 仅当用户处于菜单模式时才处理
        if not self.user_menu_state.get(user_id, False):
            return

        text = event.message_str.strip()

        # ---------- 数字选项 ----------
        if text == "0":
            self.user_menu_state[user_id] = False
            yield event.plain_result("👋 已退出酷我音乐管理菜单")
            return

        elif text == "1":
            yield event.plain_result("📱 请输入要绑定的手机号或邮箱：")
            self._set_waiting(user_id, "binding")
            return

        elif text == "2":
            if self.data_manager.unbind_account(user_id):
                yield event.plain_result("✅ 账号解绑成功")
            else:
                yield event.plain_result("❌ 您还没有绑定账号")
            return

        elif text == "3":
            account = self.data_manager.get_bound_account(user_id)
            if account:
                yield event.plain_result(f"📋 您绑定的账号：{account}")
            else:
                yield event.plain_result("❌ 您还没有绑定账号")
            return

        elif text == "4":
            account = self.data_manager.get_bound_account(user_id)
            if account:
                # 🟢 模拟发送验证码（实际开发请替换为真实 API 调用）
                yield event.plain_result(f"📨 验证码已发送至 {account}（模拟）")
                # 真实场景示例：
                # import aiohttp
                # async with aiohttp.ClientSession() as session:
                #     async with session.post("https://api.kuwo.com/send_code", json={"phone": account}) as resp:
                #         ...
            else:
                yield event.plain_result("❌ 请先绑定账号（回复 1）")
            return

        elif text == "5":
            account = self.data_manager.get_bound_account(user_id)
            if not account:
                yield event.plain_result("❌ 请先绑定账号（回复 1）")
                return
            yield event.plain_result("🔢 请输入6位验证码：")
            self._set_waiting(user_id, "verifying")
            return

        elif text == "6":
            account = self.data_manager.get_bound_account(user_id)
            if not account:
                yield event.plain_result("❌ 请先绑定账号（回复 1）")
                return
            # 🟢 模拟提现（实际开发请替换为真实 API 调用）
            yield event.plain_result(f"💰 提现请求已提交（模拟），请等待处理")
            return

        elif text == "8":
            yield event.plain_result(self._get_help_text())
            return

        # ---------- 处理等待输入 ----------
        waiting = self._get_waiting(user_id)

        if waiting == "binding":
            account = text.strip()
            if len(account) < 3:
                yield event.plain_result("❌ 账号格式不正确，请重新输入")
                return
            self.data_manager.bind_account(user_id, account)
            self._clear_waiting(user_id)
            yield event.plain_result(f"✅ 账号绑定成功：{account}\n{self._get_menu_text()}")
            return

        elif waiting == "verifying":
            if not text.isdigit() or len(text) != 6:
                yield event.plain_result("❌ 验证码格式错误，请输入6位数字")
                return
            # 🟢 模拟验证码校验（实际开发请替换为真实 API 调用）
            self._clear_waiting(user_id)
            yield event.plain_result(f"✅ 验证码 {text} 提交成功（模拟）\n{self._get_menu_text()}")
            return

        # ---------- 无效输入 ----------
        yield event.plain_result("❌ 无效选项，请回复对应数字\n" + self._get_menu_text())

    # ---------- 插件卸载清理 ----------
    async def terminate(self):
        """插件被卸载时调用，可执行资源释放操作"""
        pass
