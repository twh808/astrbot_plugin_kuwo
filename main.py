#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
astrbot_plugin_kuwo 提现模块 — 预连接整点发射最优方案
版本: 2.7.0

核心改动（相对 2.6.3）：
1. 验证码提交只更新内存字典（零 IO），59:58 提交也能赶上整点。
2. 登录 + TCP/TLS 预连接在后台提前完成，不依赖验证码。
3. 每账号独立 requests.Session，每 Session 仅由一个线程使用。
4. 整点前 30 秒保活一次，避免 keep-alive 被回收。
5. 整点用 ThreadPoolExecutor 并发发射，复用已预热连接。
6. 频繁重试规则保持：最多 3 次额外重试，间隔 4000ms。
"""

import os
import sys
import time
import base64
import random
import string
import uuid
import json
import sqlite3
import re
import hashlib
import threading
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager
import urllib3

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star
from astrbot.api import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VERSION = "2.7.0"

# ============================================================
# 常量（与脚本保持一致）
# ============================================================
DB_PATH = os.getenv('DB_PATH', '/app/Dumb-Panel/daidai.db')
ENV_NAME_KWTX = 'kwtx'
DEFAULT_VERIFICATION_ID = (
    'BVB5cctRxT%252FifPHwGzM9q2c%252BG53szUY8iDipOhkIAb%252FmSy64bK1Od%252FTftF%252F1NrBdTYm7hqnmCc3go8IWpPs80nQ%253D%253D'
)
DEFAULT_Q36 = 'a9441d902f38da7d2d25bf1f10001a319907'
FREQUENT_ERROR_KEYWORD = "频繁"
MAX_EXTRA_RETRIES = 3
RETRY_DELAY_MS = 4000
PREWARM_AHEAD_SECONDS = 180          # 整点前 3 分钟开始登录+预连接
KEEPALIVE_AHEAD_SECONDS = 30        # 整点前 30 秒保活
WITHDRAW_API_HOST = "integralapi.kuwo.cn"

# ============================================================
# 加密函数（来自你的脚本，完整保留）
# ============================================================
static_c = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912, 1073741824, 2147483648, 4294967296, 8589934592, 17179869184, 34359738368, 68719476736, 137438953472, 274877906944, 549755813888, 1099511627776, 2199023255552, 4398046511104, 8796093022208, 17592186044416, 35184372088832, 70368744177664, 140737488355328, 281474976710656, 562949953421312, 1125899906842624, 2251799813685248, 4503599627370496, 9007199254740992, 18014398509481984, 36028797018963968, 72057594037927936, 144115188075855872, 288230376151711744, 576460752303423488, 1152921504606846976, 2305843009213693952, 4611686018427387904, -9223372036854775808]
static_i = [56, 48, 40, 32, 24, 16, 8, 0, 57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18, 10, 2, 59, 51, 43, 35, 62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5, 60, 52, 44, 36, 28, 20, 12, 4, 27, 19, 11, 3]
static_e = [31, 0, 1, 2, 3, 4, -1, -1, 3, 4, 5, 6, 7, 8, -1, -1, 7, 8, 9, 10, 11, 12, -1, -1, 11, 12, 13, 14, 15, 16, -1, -1, 15, 16, 17, 18, 19, 20, -1, -1, 19, 20, 21, 22, 23, 24, -1, -1, 23, 24, 25, 26, 27, 28, -1, -1, 27, 28, 29, 30, 31, 30, -1, -1]
static_l = [0, 1048577, 3145731]
static_g = [15, 6, 19, 20, 28, 11, 27, 16, 0, 14, 22, 25, 4, 17, 30, 9, 1, 7, 23, 13, 31, 26, 2, 8, 18, 12, 29, 5, 21, 10, 3, 24]
static_f = [[14, 4, 3, 15, 2, 13, 5, 3, 13, 14, 6, 9, 11, 2, 0, 5, 4, 1, 10, 12, 15, 6, 9, 10, 1, 8, 12, 7, 8, 11, 7, 0, 0, 15, 10, 5, 14, 4, 9, 10, 7, 8, 12, 3, 13, 1, 3, 6, 15, 12, 6, 11, 2, 9, 5, 0, 4, 2, 11, 14, 1, 7, 8, 13], [15, 0, 9, 5, 6, 10, 12, 9, 8, 7, 2, 12, 3, 13, 5, 2, 1, 14, 7, 8, 11, 4, 0, 3, 14, 11, 13, 6, 4, 1, 10, 15, 3, 13, 12, 11, 15, 3, 6, 0, 4, 10, 1, 7, 8, 4, 11, 14, 13, 8, 0, 6, 2, 15, 9, 5, 7, 1, 10, 12, 14, 2, 5, 9], [10, 13, 1, 11, 6, 8, 11, 5, 9, 4, 12, 2, 15, 3, 2, 14, 0, 6, 13, 1, 3, 15, 4, 10, 14, 9, 7, 12, 5, 0, 8, 7, 13, 1, 2, 4, 3, 6, 12, 11, 0, 13, 5, 14, 6, 8, 15, 2, 7, 10, 8, 15, 4, 9, 11, 5, 9, 0, 14, 3, 10, 7, 1, 12], [7, 10, 1, 15, 0, 12, 11, 5, 14, 9, 8, 3, 9, 7, 4, 8, 13, 6, 2, 1, 6, 11, 12, 2, 3, 0, 5, 14, 10, 13, 15, 4, 13, 3, 4, 9, 6, 10, 1, 12, 11, 0, 2, 5, 0, 13, 14, 2, 8, 15, 7, 4, 15, 1, 10, 7, 5, 6, 12, 11, 3, 8, 9, 14], [2, 4, 8, 15, 7, 10, 13, 6, 4, 1, 3, 12, 11, 7, 14, 0, 12, 2, 5, 9, 10, 13, 0, 3, 1, 11, 15, 5, 6, 8, 9, 14, 14, 11, 5, 6, 4, 1, 3, 10, 2, 12, 15, 0, 13, 2, 8, 5, 11, 8, 0, 15, 7, 14, 9, 4, 12, 7, 10, 9, 1, 13, 6, 3], [12, 9, 0, 7, 9, 2, 14, 1, 10, 15, 3, 4, 6, 12, 5, 11, 1, 14, 13, 0, 2, 8, 7, 13, 15, 5, 4, 10, 8, 3, 11, 6, 10, 4, 6, 11, 7, 9, 0, 6, 4, 2, 13, 1, 9, 15, 3, 8, 15, 3, 1, 14, 12, 5, 11, 0, 2, 12, 14, 7, 5, 10, 8, 13], [4, 1, 3, 10, 15, 12, 5, 0, 2, 11, 9, 6, 8, 7, 6, 9, 11, 4, 12, 15, 0, 3, 10, 5, 14, 13, 7, 8, 13, 14, 1, 2, 13, 6, 14, 9, 4, 1, 2, 14, 11, 13, 5, 0, 1, 10, 8, 3, 0, 11, 3, 5, 9, 4, 15, 2, 7, 8, 12, 15, 10, 7, 6, 12], [13, 7, 10, 0, 6, 9, 5, 15, 8, 4, 3, 10, 11, 14, 12, 5, 2, 11, 9, 6, 15, 12, 0, 3, 4, 1, 14, 13, 1, 2, 7, 8, 1, 2, 12, 15, 10, 4, 0, 3, 13, 14, 6, 9, 7, 8, 9, 6, 15, 1, 5, 12, 3, 10, 14, 5, 8, 7, 11, 0, 4, 13, 2, 11]]
static_h = [39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27, 34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25, 32, 0, 40, 8, 48, 16, 56, 24]
static_d = [57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3, 61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7, 56, 48, 40, 32, 24, 16, 8, 0, 58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38, 30, 22, 14, 6]
static_k = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
static_j = [13, 16, 10, 23, 0, 4, -1, -1, 2, 27, 14, 5, 20, 9, -1, -1, 22, 18, 11, 3, 25, 7, -1, -1, 15, 6, 26, 19, 12, 1, -1, -1, 40, 51, 30, 36, 46, 54, -1, -1, 29, 39, 50, 44, 32, 47, -1, -1, 43, 48, 38, 55, 33, 52, -1, -1, 45, 41, 49, 35, 28, 31, -1, -1]


def func_a1(iArr, i2, j2):
    j3 = 0
    for i3 in range(i2):
        if iArr[i3] >= 0:
            jArr = static_c
            if (jArr[iArr[i3]] & j2) != 0:
                j3 |= jArr[i3]
    return j3

def func_a2(j2, jArr, i2):
    a2 = func_a1(static_i, 56, j2)
    for i3 in range(16):
        jArr2 = static_l
        iArr = static_k
        a2 = ((a2 & ~jArr2[iArr[i3]]) >> iArr[i3]) | ((jArr2[iArr[i3]] & a2) << (28 - iArr[i3]))
        jArr[i3] = func_a1(static_j, 64, a2)
    if i2 == 1:
        for i4 in range(8):
            j3 = jArr[i4]
            i5 = 15 - i4
            jArr[i4] = jArr[i5]
            jArr[i5] = j3

def func_a3(jArr, j2):
    p = [0] * 2
    q = [0] * 8
    m = func_a1(static_d, 64, j2)
    iArr = p
    j3 = m
    iArr[0] = int(j3 & 4294967295)
    iArr[1] = int((j3 & -4294967296) >> 32)
    for i2 in range(16):
        o = iArr[1]
        o = func_a1(static_e, 64, o)
        o ^= jArr[i2]
        for i3 in range(8):
            q[i3] = int((o >> (i3 * 8)) & 255)
        r = 0
        i4 = 7
        while True:
            t = i4
            i5 = t
            if i5 >= 0:
                i6 = r
                i6 <<= 4
                if i6 > 2147483647:
                    i6 = -4294967296 + i6
                i6 |= static_f[i5][q[i5]]
                r = i6
                i4 = i5 - 1
            else:
                break
        o = r
        o = func_a1(static_g, 32, o)
        iArr2 = p
        n = iArr2[0]
        iArr2[0] = iArr2[1]
        xor_val = n ^ o
        if -2147483648 < xor_val < 2147483647:
            iArr2[1] = int(xor_val)
            continue
        if xor_val >= 2147483647:
            iArr2[1] = xor_val - 4294967296
        else:
            iArr2[1] = xor_val + 4294967296
    iArr3 = p
    s = iArr3[0]
    iArr3[0] = iArr3[1]
    iArr3[1] = s
    m = ((iArr3[1] << 32) & -4294967296) | (4294967295 & iArr3[0])
    m = func_a1(static_h, 64, m)
    return m

def generate_q(bArr, bArr2):
    length = len(bArr)
    jArr = [0] * 16
    j2 = 0
    j3 = 0
    for i3 in range(8):
        j3 |= bArr2[i3] << (i3 * 8)
    func_a2(j3, jArr, 0)
    i4 = length // 8
    jArr2 = [0] * i4
    for i5 in range(i4):
        for i6 in range(8):
            jArr2[i5] = jArr2[i5] | ((bArr[i5 * 8 + i6] & 255) << (i6 * 8))
    jArr3 = [0] * (((i4 + 1) * 8 + 1) // 8)
    for i7 in range(i4):
        jArr3[i7] = func_a3(jArr, jArr2[i7])
    i8 = length % 8
    i9 = i4 * 8
    i10 = length - i9
    r12 = [None] * i10
    r12[0:i10] = bArr[i9:i9 + i10]
    for i11 in range(i8):
        j2 |= (r12[i11] & 255) << (i11 * 8)
    jArr3[i4] = func_a3(jArr, j2)
    bArr3 = [None] * (len(jArr3) * 8)
    i12 = 0
    i13 = 0
    while i12 < len(jArr3):
        i14 = i13
        for i15 in range(8):
            bArr3[i14] = 255 & (jArr3[i12] >> (i15 * 8))
            i14 += 1
        i12 += 1
        i13 = i14
    return base64.b64encode(bytearray(bArr3)).decode()

def create_sx():
    timestamp = int(time.time() * 1000)
    combined_string = str(timestamp) + '12345678'
    return combined_string[:8]

def encrypt_devid(dev_id):
    padded_id = dev_id.ljust(16, '0')[:16]
    return base64.b64encode(padded_id.encode()).decode()

def get_q(username, password):
    dev_id = ''.join([random.choice(string.digits) for _ in range(10)])
    dev_name = '安卓设备'
    devType = 'arr'
    data = (f"username={requests.utils.quote(username)}"
            f"&password={requests.utils.quote(base64.b64encode(password.encode()).decode())}"
            f"&dev_id={dev_id}&user={str(uuid.uuid4()).replace('-', '')}"
            f"&dev_name={requests.utils.quote(dev_name)}&urlencode=0"
            f"&src=kwplayer_ar11.1.4.1_40.apk&devResolution=720*1080&&from=android"
            f"&devType={devType}&sx={create_sx()}&version=11.1.4.1")
    q_value = generate_q(data.encode('UTF-8'), 'kwks&@69'.encode('UTF-8'))
    encrypted_dev_id = encrypt_devid(dev_id)
    return q_value, encrypted_dev_id

def encrypt_phone(phone):
    key = b'ysiVkLJHHnvMWCHq'
    iv = b'ichYooX+Mb1gRetP'
    if isinstance(phone, str):
        phone = phone.encode('utf-8')
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(phone, AES.block_size)
    ciphertext = cipher.encrypt(padded_plaintext)
    return base64.b64encode(ciphertext).decode('utf-8')

def decrypt_phone(encrypted_phone):
    key = b'ysiVkLJHHnvMWCHq'
    iv = b'ichYooX+Mb1gRetP'
    aes = AES.new(key=key, mode=AES.MODE_CBC, iv=iv)
    encrypted_data = base64.b64decode(encrypted_phone)
    decrypted_data = unpad(aes.decrypt(encrypted_data), AES.block_size, style='pkcs7')
    return decrypted_data.decode('UTF-8')

# ============================================================
# 账户解析（保留你脚本的逻辑）
# ============================================================
def parse_account_item(account_str: str) -> Optional[dict]:
    parts = [x.strip() for x in account_str.split('#')]
    if len(parts) < 2:
        return None
    limit = None
    last = parts[-1]
    if last.isdigit() and int(last) > 0:
        limit = int(last)
        parts = parts[:-1]
    if len(parts) < 2:
        return None
    if len(parts) == 2:
        phone, password = parts[0], parts[1]
    else:
        phone = parts[1]
        password = '#'.join(parts[2:])
    if not phone or not password:
        return None
    return {'phone': phone, 'password': password, 'limit': limit}


def get_accounts_from_env() -> List[dict]:
    env_value = os.getenv(ENV_NAME_KWTX, '').strip()
    if not env_value:
        return []
    accounts = []
    for separator in ['&', '\n']:
        if separator in env_value:
            parts = env_value.split(separator)
            break
    else:
        parts = [env_value]
    for account_str in parts:
        account_str = account_str.strip()
        if not account_str:
            continue
        parsed = parse_account_item(account_str)
        if parsed:
            accounts.append(parsed)
    return accounts


# ============================================================
# 登录（返回凭证，不依赖验证码）
# ============================================================
def login(phone: str, password: str) -> Optional[dict]:
    """仅使用手机号+密码登录，返回凭证字典。与验证码完全解耦。"""
    try:
        q, encrypted_dev_id = get_q(phone, password)
        url = 'http://ar.i.kuwo.cn/US_NEW/kuwo/login_kw'
        headers = {
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; MI 8 MIUI/V12.5.2.0.QEACNXM)',
            'Accept': '*/*',
            'Host': 'ar.i.kuwo.cn',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
        }
        response = requests.get(url, headers=headers, params={'f': 'ar', 'q': q}, timeout=10)
        set_cookie = response.headers.get('Set-Cookie', '')
        username_match = re.search(r'uname3=([^;]+)', set_cookie)
        sid_match = re.search(r'websid=([^;]+)', set_cookie)
        uid_match = re.search(r'userid=([^;]+)', set_cookie)
        account_match = re.search(r't3kwid=([^;]+)', set_cookie)
        if not all([username_match, sid_match, uid_match, account_match]):
            logger.warning(f"❌ 账号 {phone} 登录响应缺少必要 Cookie")
            return None
        return {
            'phone': phone,
            'loginUid': uid_match.group(1),
            'loginSid': sid_match.group(1),
            'appUid': account_match.group(1),
            'encrypted_phone': encrypt_phone(phone),
        }
    except Exception as e:
        logger.warning(f"❌ 账号 {phone} 登录异常: {e}")
        return None


# ============================================================
# 预连接：强制与提现域名建立 TCP/TLS 连接并放入 Session 池
# ============================================================
def prewarm_session(session: requests.Session, host: str = WITHDRAW_API_HOST) -> bool:
    """使用 urllib3 的 connection_from_host 强制建连，不发业务请求。"""
    try:
        adapter = session.get_adapter(f"https://{host}")
        adapter.poolmanager.connection_from_host(host, port=443, scheme="https")
        return True
    except Exception as e:
        logger.warning(f"⚠️ 预连接 {host} 失败: {e}")
        return False


def keepalive_session(session: requests.Session, host: str = WITHDRAW_API_HOST) -> None:
    """整点前轻量保活，确保 keep-alive 连接未被回收。"""
    try:
        session.head(f"https://{host}/", timeout=3, verify=False)
    except Exception:
        pass


# ============================================================
# 提现请求（接受外部 Session，复用预热连接）
# ============================================================
def withdraw_confirm_once(
    session: requests.Session,
    phone: str,
    loginUid: str,
    loginSid: str,
    appUid: str,
    encrypted_phone: str,
    code: str,
    kwtxid: str,
    verification_id: str,
    q36: str,
    seq: int = 1,
    max_extra_retries: int = MAX_EXTRA_RETRIES,
    retry_delay_ms: int = RETRY_DELAY_MS,
) -> Tuple[List[str], str, bool]:
    url = 'https://integralapi.kuwo.cn/api/v1/online/sign/v1/getWithdraw'
    params = {
        'encry': '',
        'type': 'highValue',
        'quotaId': kwtxid,
        'loginUid': loginUid,
        'loginSid': loginSid,
        'appuid': appUid,
        'source': 'kwplayer_ar_12.1.4.0_meizu.apk',
        'version': '1',
        'phone': encrypted_phone,
        'verificationId': verification_id,
        'apiv': '9',
        'code': code,
        'platform': 'android',
        'cliVersion': '12.1.4.0',
        'q36': q36,
    }
    headers = {
        'Host': 'integralapi.kuwo.cn',
        'Connection': 'keep-alive',
        'sec-ch-ua-platform': '"Android"',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; MEIZU 18 Pro Build/TKQ1.221114.001; wv) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                      'Chrome/148.0.7778.120 Mobile Safari/537.36/ kuwopage',
        'Accept': 'application/json, text/plain, */*',
        'sec-ch-ua': '"Chromium";v="148", "Android WebView";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'Origin': 'https://h5app.kuwo.cn',
        'X-Requested-With': 'cn.kuwo.player',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://h5app.kuwo.cn/',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    total_attempts = max_extra_retries + 1
    last_combined = ""
    log_lines = []

    for attempt in range(1, total_attempts + 1):
        try:
            start = time.time()
            resp = session.get(url, headers=headers, params=params, timeout=5, verify=False)
            elapsed_ms = (time.time() - start) * 1000
            result = resp.json() if resp.status_code == 200 else {}
            msg = result.get('msg', '')
            data = result.get('data', {})
            text = data.get('text', '')
            description = data.get('description', '')
            combined = f"{msg}|{text}|{description}"
            last_combined = combined

            if attempt == 1:
                line = (f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (第1次请求) "
                        f"| {resp.status_code} | {elapsed_ms:.1f}ms | {combined[:200]}")
            else:
                retry_num = attempt - 1
                line = (f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (重试第{retry_num}次) "
                        f"| {resp.status_code} | {elapsed_ms:.1f}ms | {combined[:200]}")
            log_lines.append(line)

            if FREQUENT_ERROR_KEYWORD in combined and attempt <= max_extra_retries:
                log_lines.append(f"⚠️ {phone} 遭遇频繁错误（包含'{FREQUENT_ERROR_KEYWORD}'），"
                                 f"{retry_delay_ms}ms 后重试...")
                time.sleep(retry_delay_ms / 1000.0)
                continue

            is_success = "提现申请发起成功" in combined
            return log_lines, combined, is_success
        except Exception as e:
            error_msg = f"异常: {e}"
            if attempt == 1:
                line = f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (第1次请求) | {error_msg}"
            else:
                retry_num = attempt - 1
                line = f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (重试第{retry_num}次) | {error_msg}"
            log_lines.append(line)
            if attempt <= max_extra_retries:
                log_lines.append(f"⚠️ {phone} 发生异常，{retry_delay_ms}ms 后重试...")
                time.sleep(retry_delay_ms / 1000.0)
                continue
            return log_lines, error_msg, False

    log_lines.append(f"重试{max_extra_retries}次后仍失败")
    return log_lines, last_combined if last_combined else "未知错误", False


# ============================================================
# 推送（保留你原有的 XTS_TOKEN 推送）
# ============================================================
def send_xtuis_notification(title: str, content: str) -> None:
    token = os.getenv('XTS_TOKEN', '').strip()
    if not token:
        logger.info("⚠️ 虾推啥未配置（缺少 XTS_TOKEN），跳过推送")
        return
    if not title:
        title = "酷我提现通知"
    url = f"https://wx.xtuis.cn/{token}.send"
    try:
        resp = requests.get(url, params={"text": title, "desp": content}, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ 虾推啥推送通知发送成功")
        else:
            logger.warning(f"⚠️ 虾推啥推送通知发送失败: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"⚠️ 虾推啥推送通知异常: {e}")


# ============================================================
# 成功计数文件（保留）
# ============================================================
SUCCESS_COUNT_FILE = 'success_count.json'

def load_success_data() -> dict:
    if os.path.exists(SUCCESS_COUNT_FILE):
        try:
            with open(SUCCESS_COUNT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for phone, value in list(data.items()):
                    if isinstance(value, int):
                        data[phone] = {"limit": None, "count": value}
                    elif isinstance(value, dict):
                        value.setdefault("count", 0)
                        value.setdefault("limit", None)
                return data
        except Exception:
            return {}
    return {}

def save_success_data(data: dict) -> None:
    with open(SUCCESS_COUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# 数据库更新（保留）
# ============================================================
def update_kwtx_in_db(success_phones: List[str], db_path: str = DB_PATH,
                      env_name: str = ENV_NAME_KWTX) -> None:
    if not success_phones:
        logger.info("ℹ️ 没有成功提现的账户，跳过更新 kwtx")
        return
    if not os.path.isfile(db_path):
        logger.warning(f"⚠️ 数据库文件不存在: {db_path}，跳过更新 kwtx")
        return

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        target_table = None
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [col[1] for col in cursor.fetchall()]
            if 'name' in cols and 'value' in cols:
                target_table = table
                break
        if target_table is None:
            logger.warning("⚠️ 未找到包含 name 和 value 列的表，跳过更新 kwtx")
            return

        cursor.execute(f"SELECT value FROM {target_table} WHERE name=?", (env_name,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"⚠️ 环境变量 '{env_name}' 不存在，跳过更新")
            return
        old_value = row[0]

        lines = old_value.splitlines()
        new_lines = []
        updated = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('#')
            if len(parts) < 2:
                new_lines.append(line)
                continue
            phone = parts[0].strip()
            if phone in success_phones:
                if len(parts) >= 3 and parts[2].strip().isdigit():
                    limit = int(parts[2].strip())
                    if limit > 0:
                        limit -= 1
                        parts[2] = str(limit)
                        updated = True
                        logger.info(f"✅ 更新 {phone} 授权次数: 剩余 {limit} 次")
                    else:
                        logger.info(f"ℹ️ {phone} 授权次数已为 0，不再减少")
                else:
                    logger.info(f"ℹ️ {phone} 未配置授权次数，不修改")
            new_lines.append('#'.join(parts))

        if not updated:
            logger.info("ℹ️ 无需更新 kwtx")
            return

        new_value = "\n".join(new_lines)
        cursor.execute(f"UPDATE {target_table} SET value=? WHERE name=?", (new_value, env_name))
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        logger.info("✅ 数据库 kwtx 更新成功")
    except Exception as e:
        logger.warning(f"⚠️ 更新 kwtx 出错: {e}")
    finally:
        conn.close()


# ============================================================
# 等待到下一个整点（毫秒级精确）
# ============================================================
def wait_until_next_hour() -> None:
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    wait_seconds = (next_hour - now).total_seconds()
    logger.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    logger.info(f"目标整点: {next_hour.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    logger.info(f"等待 {wait_seconds:.6f} 秒")
    if wait_seconds > 0.005:
        time.sleep(wait_seconds - 0.005)
    while datetime.now() < next_hour:
        pass


# ============================================================
# AstrBot 插件类
# ============================================================
class KuwoWithdrawPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self._code_map: Dict[str, str] = {}          # 手机号 -> 验证码（仅内存，零IO）
        self._credential_cache: Dict[str, dict] = {}  # 手机号 -> 登录凭证
        self._session_cache: Dict[str, requests.Session] = {}  # 手机号 -> 独立Session
        self._lock = threading.Lock()
        self._withdraw_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False

        logger.info(f"酷我提现插件 v{VERSION} 初始化完成")

    # ---------- 验证码提交：仅更新字典，零网络 IO ----------
    @filter.command("kwtx_code")
    async def submit_code(self, event: AstrMessageEvent):
        """提交验证码，格式：/kwtx_code 手机号#验证码"""
        text = event.message_str.strip()
        if '#' not in text:
            yield event.plain_result("格式错误，请使用：/kwtx_code 手机号#验证码")
            return
        phone, code = text.split('#', 1)
        phone, code = phone.strip(), code.strip()
        if not phone or not code:
            yield event.plain_result("手机号或验证码为空")
            return
        with self._lock:
            self._code_map[phone] = code
        logger.info(f"📱{phone} 验证码已记录，将在整点发射时使用")
        yield event.plain_result(f"验证码已记录（{phone}），将在整点发射时使用。")

    # ---------- 启动提现循环 ----------
    @filter.command("kwtx_start")
    async def start_withdraw_loop(self, event: AstrMessageEvent):
        """启动后台提现循环（只需调用一次）"""
        if self._started:
            yield event.plain_result("提现循环已在运行中。")
            return
        self._started = True
        self._stop_event.clear()
        self._withdraw_thread = threading.Thread(
            target=self._withdraw_loop, daemon=True, name="kuwo-withdraw-loop"
        )
        self._withdraw_thread.start()
        yield event.plain_result("✅ 提现循环已启动，将在每个整点前自动登录、预连接并发射。")

    # ---------- 停止 ----------
    @filter.command("kwtx_stop")
    async def stop_withdraw_loop(self, event: AstrMessageEvent):
        """停止后台提现循环"""
        self._stop_event.set()
        if self._withdraw_thread and self._withdraw_thread.is_alive():
            self._withdraw_thread.join(timeout=5)
        self._started = False
        self._close_all_sessions()
        yield event.plain_result("🛑 提现循环已停止。")

    # ---------- 生命周期 ----------
    async def terminate(self):
        self._stop_event.set()
        if self._withdraw_thread and self._withdraw_thread.is_alive():
            self._withdraw_thread.join(timeout=5)
        self._close_all_sessions()
        logger.info("酷我提现插件已终止")

    def _close_all_sessions(self):
        with self._lock:
            for session in self._session_cache.values():
                try:
                    session.close()
                except Exception:
                    pass
            self._session_cache.clear()
            self._credential_cache.clear()

    # ============================================================
    # 后台提现主循环
    # ============================================================
    def _withdraw_loop(self):
        """后台线程：每个整点前 3 分钟登录+预连接，整点并发发射。"""
        while not self._stop_event.is_set():
            try:
                # 1. 等待到整点前 PREWARM_AHEAD_SECONDS
                now = datetime.now()
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                prewarm_at = next_hour - timedelta(seconds=PREWARM_AHEAD_SECONDS)
                wait = (prewarm_at - now).total_seconds()
                if wait > 0:
                    logger.info(f"⏳ 等待至预连接时刻（{prewarm_at.strftime('%H:%M:%S')}）")
                    if self._stop_event.wait(timeout=wait):
                        break

                # 2. 读取账户，后台登录 + 预连接（不依赖验证码）
                accounts = get_accounts_from_env()
                if not accounts:
                    logger.warning("⚠️ 未读取到有效账号，跳过本整点")
                    self._wait_until_next_hour_safe()
                    continue

                logger.info(f"🔐 开始为 {len(accounts)} 个账号登录并预连接...")
                self._prepare_accounts(accounts)

                if not self._credential_cache:
                    logger.warning("⚠️ 没有账号登录成功，跳过本整点")
                    self._wait_until_next_hour_safe()
                    continue

                # 3. 整点前 KEEPALIVE_AHEAD_SECONDS 保活
                now2 = datetime.now()
                keepalive_at = next_hour - timedelta(seconds=KEEPALIVE_AHEAD_SECONDS)
                wait2 = (keepalive_at - now2).total_seconds()
                if wait2 > 0:
                    if self._stop_event.wait(timeout=wait2):
                        break
                self._keepalive_all()

                # 4. 等待到整点（毫秒级精确）
                wait_until_next_hour()

                if self._stop_event.is_set():
                    break

                # 5. 整点并发发射
                self._fire_withdraw(accounts)

            except Exception as e:
                logger.exception(f"❌ 提现循环异常: {e}")
                self._wait_until_next_hour_safe()

    def _wait_until_next_hour_safe(self):
        """异常后安全等待到下一个整点前，避免忙循环。"""
        try:
            wait_until_next_hour()
        except Exception:
            self._stop_event.wait(timeout=3600)

    # ============================================================
    # 登录 + 预连接（并发，每账号独立 Session）
    # ============================================================
    def _prepare_accounts(self, accounts: List[dict]):
        with self._lock:
            self._credential_cache.clear()
            self._session_cache.clear()

        def prepare_one(acc: dict) -> Optional[Tuple[str, dict, requests.Session]]:
            phone = acc['phone']
            password = acc['password']
            # 登录（不依赖验证码）
            cred = login(phone, password)
            if not cred:
                return None
            # 每个账号独立 Session，连接池足够容纳整点请求+重试
            session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=2,
                pool_maxsize=3,
                max_retries=0,
            )
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            # 强制与提现域名建立 TCP/TLS 连接
            if not prewarm_session(session):
                logger.warning(f"⚠️ {phone} 预连接失败，整点将使用冷连接")
            return phone, cred, session

        with ThreadPoolExecutor(max_workers=min(len(accounts), 8)) as executor:
            futures = {executor.submit(prepare_one, acc): acc for acc in accounts}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                except Exception as e:
                    logger.warning(f"⚠️ 账号准备异常: {e}")
                    continue
                if result is None:
                    continue
                phone, cred, session = result
                with self._lock:
                    self._credential_cache[phone] = cred
                    self._session_cache[phone] = session
                logger.info(f"✅ {phone} 登录并预连接完成")

    def _keepalive_all(self):
        with self._lock:
            sessions = dict(self._session_cache)
        if not sessions:
            return
        logger.info(f"🔄 整点前保活 {len(sessions)} 个连接...")
        with ThreadPoolExecutor(max_workers=len(sessions)) as executor:
            list(executor.map(lambda s: keepalive_session(s), sessions.values()))

    # ============================================================
    # 整点并发发射
    # ============================================================
    def _fire_withdraw(self, accounts: List[dict]):
        kwtxid = os.getenv('kwtxid', '').strip() or "30002"
        verification_id = os.getenv('VERIFICATION_ID', '').strip() or DEFAULT_VERIFICATION_ID
        q36 = os.getenv('Q36', '').strip() or DEFAULT_Q36

        # 从环境变量重新读取 limit（以最新 kwtx 为准）
        limit_map = {acc['phone']: acc.get('limit') for acc in accounts}

        # 过滤：有凭证 + 有验证码 + 未达上限
        success_data = load_success_data()
        ready = []
        skipped = []
        for phone, cred in self._credential_cache.items():
            code = self._code_map.get(phone)
            if not code:
                logger.warning(f"⚠️ {phone} 整点前未提交验证码，跳过")
                skipped.append(phone)
                continue
            limit = limit_map.get(phone)
            stored = success_data.get(phone, {})
            stored_limit = stored.get('limit')
            stored_count = stored.get('count', 0)
            if stored_limit != limit:
                stored_count = 0
                success_data[phone] = {"limit": limit, "count": 0}
            if limit is not None and stored_count >= limit:
                logger.info(f"⏭️ {phone} 已达授权上限（{stored_count}/{limit}），跳过")
                skipped.append(phone)
                continue
            ready.append((phone, cred, code))
        save_success_data(success_data)

        if not ready:
            logger.warning("⚠️ 整点没有可发射的账户（缺少验证码或已达上限）")
            return

        logger.info(f"🚀 整点发射：{len(ready)} 个账户并发提现（另有 {len(skipped)} 个跳过）")

        results = {}
        with ThreadPoolExecutor(max_workers=len(ready)) as executor:
            future_to_phone = {}
            for idx, (phone, cred, code) in enumerate(ready, 1):
                session = self._session_cache.get(phone)
                if session is None:
                    logger.warning(f"⚠️ {phone} 无预连接 Session，使用普通请求")
                    session = requests.Session()
                future = executor.submit(
                    withdraw_confirm_once,
                    session, phone, cred['loginUid'], cred['loginSid'],
                    cred['appUid'], cred['encrypted_phone'], code,
                    kwtxid, verification_id, q36, idx,
                )
                future_to_phone[future] = phone

            for future in as_completed(future_to_phone):
                phone = future_to_phone[future]
                try:
                    log_lines, final_result, is_success = future.result(timeout=60)
                    results[phone] = (log_lines, final_result, is_success)
                except Exception as e:
                    results[phone] = ([f"❌ 账号处理异常: {e}"], f"异常: {e}", False)

        # 输出日志
        success_phones = []
        summaries = []
        for phone, (log_lines, final_result, is_success) in results.items():
            for line in log_lines:
                logger.info(line)
            logger.info(f"📱{phone} 最终结果: {final_result[:200]}")
            if is_success:
                success_phones.append(phone)
            summaries.append(f"📱{phone}: {final_result[:80]}")

        # 更新计数
        success_data = load_success_data()
        for phone in success_phones:
            entry = success_data.setdefault(phone, {"limit": limit_map.get(phone), "count": 0})
            entry["count"] = entry.get("count", 0) + 1
        save_success_data(success_data)

        # 更新数据库 kwtx
        update_kwtx_in_db(success_phones)

        # 推送
        if summaries:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content = f"共 {len(summaries)} 项结果:\n" + "\n".join(summaries) + f"\n脚本版本: {VERSION}"
            send_xtuis_notification(f"酷我提现 {now_str}", content)

        logger.info("🏁 本整点提现发射完毕")
