#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import time
import re
import base64
import random
import string
import uuid
import email.utils
import threading
from datetime import datetime, timedelta
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from urllib.parse import quote

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger

# ======================================================================
# 1. 加密常量
# ======================================================================
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

# ======================================================================
# 2. 加密与 API 函数
# ======================================================================
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
    return (str(int(time.time() * 1000)) + '12345678')[:8]

def encrypt_devid(dev_id):
    return base64.b64encode(dev_id.ljust(16, '0')[:16].encode()).decode()

def get_q(username, password):
    dev_id = ''.join([random.choice(string.digits) for _ in range(10)])
    data = f"username={quote(username)}&password={quote(base64.b64encode(password.encode()).decode())}&dev_id={dev_id}&user={str(uuid.uuid4()).replace('-', '')}&dev_name={quote('安卓设备')}&urlencode=0&src=kwplayer_ar11.1.4.1_40.apk&devResolution=720*1080&&from=android&devType=arr&sx={create_sx()}&version=11.1.4.1"
    return generate_q(data.encode('UTF-8'), 'kwks&@69'.encode('UTF-8')), encrypt_devid(dev_id)

def encrypt_phone(phone):
    if isinstance(phone, str):
        phone = phone.encode('utf-8')
    cipher = AES.new(b'ysiVkLJHHnvMWCHq', AES.MODE_CBC, b'ichYooX+Mb1gRetP')
    return base64.b64encode(cipher.encrypt(pad(phone, AES.block_size))).decode('utf-8')

def login_kuwo(username, password):
    try:
        q, encrypted_dev_id = get_q(username, password)
        response = requests.get(
            'http://ar.i.kuwo.cn/US_NEW/kuwo/login_kw',
            headers={'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; MI 8 MIUI/V12.5.2.0.QEACNXM)',
                     'Accept': '*/*', 'Host': 'ar.i.kuwo.cn', 'Connection': 'Keep-Alive', 'Accept-Encoding': 'gzip'},
            params={'f': 'ar', 'q': q}, timeout=10)
        set_cookie = response.headers.get('Set-Cookie', '')
        m = {k: re.search(rf'{k}=([^;]+)', set_cookie) for k in ['uname3', 'websid', 'userid', 't3kwid']}
        if all(m.values()):
            return m['userid'].group(1), m['websid'].group(1), m['t3kwid'].group(1), encrypted_dev_id
        return None
    except Exception as e:
        logger.error(f"酷我登录异常: {e}")
        return None

def check_withdraw_today(loginUid, loginSid, target_date_str=None):
    try:
        resp = requests.get(
            'https://integralapi.kuwo.cn/api/v1/online/sign/v1/withdrawDetails',
            params={'loginUid': loginUid, 'loginSid': loginSid, 'pn': 1, 'rn': 10},
            headers={'Host': 'integralapi.kuwo.cn', 'Accept': 'application/json, text/plain, */*',
                     'Origin': 'https://h5app.kuwo.cn',
                     'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KWMusic/12.1.2.0 DeviceModel/iPhone18,3 NetType/WIFI kuwopage',
                     'Referer': 'https://h5app.kuwo.cn/apps/earning-sign/bill.html',
                     'Accept-Language': 'zh-CN,zh-Hans;q=0.9', 'Connection': 'keep-alive'},
            timeout=5, verify=False)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if data.get('code') != 200:
            return False
        if target_date_str is None:
            target_date_str = datetime.now().strftime('%Y-%m-%d')
        for item in data.get('data', {}).get('list', []):
            if item.get('createTime', '').startswith(target_date_str):
                if item.get('status') == 1 or '提现成功' in item.get('description', ''):
                    return True
        return False
    except Exception:
        return False

def send_code_once(loginUid, loginSid, appUid, encrypted_phone, quota_id='60004'):
    try:
        resp = requests.get(
            'https://integralapi.kuwo.cn/api/v1/online/sign/v1/withdraw/sendCode',
            params={'loginUid': loginUid, 'loginSid': loginSid, 'mobile': encrypted_phone, 'appuid': appUid,
                    'apiv': '9', 'terminal': '1', 'quotaId': quota_id, 'type': 'blindBox'},
            headers={'Host': 'integralapi.kuwo.cn', 'Connection': 'keep-alive',
                     'Accept': 'application/json, text/plain, */*',
                     'User-Agent': 'Mozilla/5.0 (Linux; Android 13; MEIZU 18 Pro; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Mobile Safari/537.36 kuwopage',
                     'Origin': 'https://h5app.kuwo.cn', 'X-Requested-With': 'cn.kuwo.player',
                     'Referer': 'https://h5app.kuwo.cn/',
                     'Accept-Encoding': 'gzip, deflate, br',
                     'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'},
            timeout=5, verify=False)
        text = resp.text
        try:
            data = resp.json()
            combined = f"{data.get('msg', '')}|{data.get('data', {}).get('description', '')}"
        except:
            data = {}
            combined = text
        lower_text = (text + str(data.get('msg', '')) + str(data.get('data', {}).get('description', ''))).lower()
        return '发送成功' in lower_text, combined
    except Exception as e:
        return False, str(e)

FREQUENT_ERROR_KEYWORD = "频繁"

def withdraw_confirm_once(session, phone, loginUid, loginSid, appUid, encrypted_phone, code, kwtxid, verification_id, q36, seq=1, max_extra_retries=3, retry_delay_ms=4000):
    url = 'https://integralapi.kuwo.cn/api/v1/online/sign/v1/getWithdraw'
    params = {'encry': '', 'type': 'highValue', 'quotaId': kwtxid, 'loginUid': loginUid, 'loginSid': loginSid,
              'appuid': appUid, 'source': 'kwplayer_ar_12.1.4.0_meizu.apk', 'version': '1', 'phone': encrypted_phone,
              'verificationId': verification_id, 'apiv': '9', 'code': code, 'platform': 'android',
              'cliVersion': '12.1.4.0', 'q36': q36}
    headers = {'Host': 'integralapi.kuwo.cn', 'Connection': 'keep-alive', 'sec-ch-ua-platform': '"Android"',
               'User-Agent': 'Mozilla/5.0 (Linux; Android 13; MEIZU 18 Pro; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.120 Mobile Safari/537.36 kuwopage',
               'Accept': 'application/json, text/plain, */*',
               'sec-ch-ua': '"Chromium";v="148", "Android WebView";v="148", "Not/A)Brand";v="99"',
               'sec-ch-ua-mobile': '?1', 'Origin': 'https://h5app.kuwo.cn', 'X-Requested-With': 'cn.kuwo.player',
               'Referer': 'https://h5app.kuwo.cn/', 'Accept-Encoding': 'gzip, deflate, br, zstd',
               'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'}
    log_lines, last_combined = [], ""
    for attempt in range(1, max_extra_retries + 2):
        try:
            start = time.time()
            resp = session.get(url, headers=headers, params=params, timeout=5, verify=False)
            elapsed_ms = (time.time() - start) * 1000
            result = resp.json() if resp.status_code == 200 else {}
            data = result.get('data', {})
            combined = f"{result.get('msg', '')}|{data.get('text', '')}|{data.get('description', '')}"
            last_combined = combined
            tag = "(第1次请求)" if attempt == 1 else f"(重试第{attempt-1}次)"
            log_lines.append(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} {tag} | {resp.status_code} | {elapsed_ms:.1f}ms | {combined[:200]}")
            if FREQUENT_ERROR_KEYWORD in combined and attempt <= max_extra_retries:
                log_lines.append(f"⚠️ {phone} 遭遇频繁错误，{retry_delay_ms}ms 后重试...")
                time.sleep(retry_delay_ms / 1000.0)
                continue
            return log_lines, combined, "提现申请发起成功" in combined
        except Exception as e:
            error_msg = f"异常: {e}"
            tag = "(第1次请求)" if attempt == 1 else f"(重试第{attempt-1}次)"
            log_lines.append(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} {tag} | {error_msg}")
            if attempt <= max_extra_retries:
                log_lines.append(f"⚠️ {phone} 发生异常，{retry_delay_ms}ms 后重试...")
                time.sleep(retry_delay_ms / 1000.0)
                continue
            return log_lines, error_msg, False
    log_lines.append(f"重试{max_extra_retries}次后仍失败")
    return log_lines, last_combined or "未知错误", False

# ======================================================================
# 3. AstrBot 插件主类
# ======================================================================
class KuwoPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.default_auth_limit = self.config.get('default_auth_limit', 3)
        self.verification_cron = self.config.get('verification_cron', "15 55 8,12,16,19 * * *")
        self.default_withdraw_cron = self.config.get('default_withdraw_cron', "0 0 0,9,13,17,20 * * *")
        self.verification_id = self.config.get('verification_id', "BVB5cctRxT%252FifPHwGzM9q2c%252BG53szUY8iDipOhkIAb%252FmSy64bK1Od%252FTftF%252F1NrBdTYm7hqnmCc3go8IWpPs80nQ%253D%253D")
        self.q36 = self.config.get('q36', "a9441d902f38da7d2d25bf1f10001a319907")
        self.kwtxid = self.config.get('kwtxid', "30002")
        self.timeout = self.config.get('timeout', 300)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay_ms = self.config.get('retry_delay_ms', 4000)
        self.quota_id = self.config.get('quota_id', "60004")
        self.admin_qq = self.config.get('admin_qq', [])

        self.states = {}
        self.TIMEOUT = self.timeout
        self.timeout_tasks = {}
        self.scheduler_task = None
        self.scheduler_running = False
        self.num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        self._last_trigger_time = {}
        self._db_lock = asyncio.Lock()
        self._code_cache_mem = {}
        self._login_cache_mem = {}
        self._time_offset = 0.0
        self._time_offset_updated_at = 0.0
        self._all_data_cache = None
        self._cron_cache = {}
        self._pre_login_tasks = {}
        self._session_local = threading.local()
        self._withdraw_warmed_at = 0.0

    # ---------- 线程本地 Session ----------
    def _get_thread_session(self) -> requests.Session:
        if not hasattr(self._session_local, 'session'):
            self._session_local.session = requests.Session()
        return self._session_local.session

    # ---------- 数据持久化 ----------
    async def _retry_db_call(self, coro_func, *args, max_retries=5, base_delay=0.5, **kwargs):
        last_exc = None
        for attempt in range(max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait = base_delay * (attempt + 1)
                    logger.warning(f"⚠️ 数据库锁定，{wait:.1f}秒后重试（{attempt+1}/{max_retries}）")
                    await asyncio.sleep(wait)
                    continue
                raise
        if last_exc:
            raise last_exc

    async def _load_all_data_unlocked(self) -> dict:
        if self._all_data_cache is not None:
            return self._all_data_cache
        self._all_data_cache = await self._retry_db_call(self.get_kv_data, "kuwo_data", {})
        return self._all_data_cache

    async def _save_all_data_unlocked(self, data: dict):
        await self._retry_db_call(self.put_kv_data, "kuwo_data", data)
        self._all_data_cache = data

    async def _load_all_data(self) -> dict:
        async with self._db_lock:
            return await self._load_all_data_unlocked()

    async def _save_all_data(self, data: dict):
        async with self._db_lock:
            await self._save_all_data_unlocked(data)

    def _get_default_user_data(self) -> dict:
        return {
            "accounts": [],
            "auth_limit": self.default_auth_limit,
            "daily_withdraw": {},
            "verification_codes": {},
            "cron": self.verification_cron,
            "scheduled_job": {"cron": self.verification_cron, "enabled": True, "last_executed": None},
            "withdraw_scheduled_job": {"cron": self.default_withdraw_cron, "enabled": True, "last_executed": None},
            "last_withdraw_log": None,
        }

    async def _load_data(self, user_id: str) -> dict:
        async with self._db_lock:
            all_data = await self._load_all_data_unlocked()
            if user_id not in all_data:
                all_data[user_id] = self._get_default_user_data()
                await self._save_all_data_unlocked(all_data)
            return all_data[user_id]

    async def _save_data(self, user_id: str, user_data: dict):
        async with self._db_lock:
            if "accounts" in user_data:
                unique_dict = {}
                for acc in user_data["accounts"]:
                    phone = acc.get("phone")
                    if phone:
                        unique_dict[phone] = acc
                user_data["accounts"] = list(unique_dict.values())
            all_data = await self._load_all_data_unlocked()
            all_data[user_id] = user_data
            await self._save_all_data_unlocked(all_data)

    async def _delete_user_data(self, user_id: str) -> bool:
        async with self._db_lock:
            all_data = await self._load_all_data_unlocked()
            if user_id in all_data:
                del all_data[user_id]
                await self._save_all_data_unlocked(all_data)
                return True
            return False

    # ---------- 状态管理 ----------
    def _get_state(self, user_id: str) -> dict:
        if user_id not in self.states:
            self.states[user_id] = {'menu': None, 'step': None, 'last_active': time.time(), 'tmp_data': {}, 'umo': None}
        return self.states[user_id]

    def _update_state(self, user_id: str, **kwargs):
        state = self._get_state(user_id)
        state.update(kwargs)
        state['last_active'] = time.time()

    def _clear_state(self, user_id: str):
        self.states.pop(user_id, None)
        if user_id in self.timeout_tasks:
            self.timeout_tasks[user_id].cancel()
            del self.timeout_tasks[user_id]

    def _cancel_timeout(self, user_id: str):
        if user_id in self.timeout_tasks:
            self.timeout_tasks[user_id].cancel()
            del self.timeout_tasks[user_id]

    async def _timeout_callback(self, user_id: str):
        if user_id not in self.states:
            return
        state = self.states[user_id]
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
        self.timeout_tasks[user_id] = asyncio.create_task(self._timeout_after_delay(user_id))

    async def _timeout_after_delay(self, user_id: str):
        try:
            await asyncio.sleep(self.TIMEOUT)
            await self._timeout_callback(user_id)
        except asyncio.CancelledError:
            pass

    def _get_effective_today_str(self) -> str:
        now = datetime.now()
        if now.hour >= 23:
            return (now + timedelta(days=1)).strftime('%Y-%m-%d')
        return now.strftime('%Y-%m-%d')

    # ---------- 菜单文本 ----------
    async def _get_main_menu_text(self, user_id: str) -> str:
        user_data = await self._load_data(user_id)
        auth_limit = user_data.get('auth_limit', 0)
        auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
        return (f"🎵 酷我菜单 (剩余授权: {auth_display})\n1️⃣ 账号管理\n2️⃣ 获取验证码\n3️⃣ 提交验证码\n4️⃣ 提现\n0️⃣ 退出")

    def _account_menu(self) -> str:
        return "📂 账号管理\n1️⃣ 绑定账号\n2️⃣ 解绑账号\n3️⃣ 查看账号\n0️⃣ 返回主菜单"

    def _verify_menu(self) -> str:
        return "📨 获取验证码\n1️⃣ 立即获取\n2️⃣ 定时获取\n0️⃣ 返回主菜单"

    async def _get_verify_timer_menu(self, user_id: str) -> str:
        user_data = await self._load_data(user_id)
        job = user_data.get('scheduled_job', {})
        if bool(job.get('cron')) and job.get('enabled', False):
            return (f"⏰ 定时获取验证码\n当前规则：{job.get('cron')} (已启用)\n"
                    "1️⃣ 修改定时规则\n2️⃣ 删除定时规则\n3️⃣ 立即执行一次\n0️⃣ 返回")
        return "⏰ 定时获取验证码\n当前未设置定时规则\n1️⃣ 设置定时规则\n0️⃣ 返回"

    def _withdraw_menu(self) -> str:
        return "💳 提现\n1️⃣ 立即提现\n2️⃣ 开启/停用整点提现\n0️⃣ 返回主菜单"

    def _admin_menu(self) -> str:
        return ("🔧 酷我提现管理面板\n1️⃣ 查看所有账号\n2️⃣ 删除账号\n3️⃣ 修改授权次数（设置具体值或无限制）\n"
                "4️⃣ 发送验证码（可指定用户和账号，输入 all 发送全部）\n5️⃣ 为指定用户绑定账号\n"
                "6️⃣ 重置用户所有数据\n7️⃣ 查看最近提现记录\n0️⃣ 退出")

    # ---------- 辅助方法 ----------
    def _format_admin_user_list(self, all_data: dict) -> str:
        lines = []
        for idx, (uid, udata) in enumerate(all_data.items(), 1):
            accounts = udata.get('accounts', [])
            auth_limit = udata.get('auth_limit', 0)
            auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
            emoji = self.num_emojis[idx-1] if idx <= len(self.num_emojis) else f"{idx}."
            if accounts:
                phones_lines = "\n   ".join([f"📱 {a['phone']}" for a in accounts])
                lines.append(f"{emoji} QQ {uid}（剩余授权：{auth_display}）\n   {phones_lines}")
            else:
                lines.append(f"{emoji} QQ {uid}（剩余授权：{auth_display}）\n   (无账号)")
        return "\n".join(lines)

    def _format_accounts_list(self, accounts: list, emoji_start: int = 1) -> str:
        lines = []
        for i, acc in enumerate(accounts, emoji_start):
            emoji = self.num_emojis[i-1] if i <= len(self.num_emojis) else f"{i}."
            lines.append(f"{emoji} {acc['phone']}")
        return "\n".join(lines)

    def _send_code_for_phone_sync(self, phone: str, password: str, check_today: bool = False) -> tuple:
        try:
            login = login_kuwo(phone, password)
            if not login:
                return (phone, "登录失败", False)
            uid, sid, appuid, _ = login
            if check_today and check_withdraw_today(uid, sid, self._get_effective_today_str()):
                return (phone, "今日已提现，跳过", False)
            success, msg = send_code_once(uid, sid, appuid, encrypt_phone(phone), self.quota_id)
            return (phone, msg, success)
        except Exception as e:
            return (phone, f"异常: {e}", False)

    def _parse_phone_selection(self, text: str, accounts: list) -> tuple:
        if text == "all":
            return [acc["phone"] for acc in accounts], None
        phones = []
        try:
            for idx_str in text.split(','):
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(accounts):
                    phones.append(accounts[idx]["phone"])
                else:
                    return None, f"❌ 序号 {idx_str} 无效，请重新输入"
        except ValueError:
            return None, "❌ 输入格式错误，请输入数字序号（用逗号分隔）或 all"
        return phones, None

    async def _send_codes_concurrently(self, phones: list, account_map: dict, check_today: bool = False) -> list:
        task_phones = [p for p in phones if p in account_map]
        missing = [p for p in phones if p not in account_map]
        result_by_phone = {}
        if task_phones:
            task_results = await asyncio.gather(*[
                asyncio.to_thread(self._send_code_for_phone_sync, p, account_map[p], check_today) for p in task_phones
            ])
            for p, m, ok in task_results:
                result_by_phone[p] = f"{'✅' if ok else '❌'} {p}: {m}"
        for p in missing:
            result_by_phone[p] = f"❌ {p}: 未找到密码"
        return [result_by_phone[p] for p in phones if p in result_by_phone]

    # ---------- 命令入口 ----------
    @filter.command("酷我")
    async def kuwo_menu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        self._clear_state(user_id)
        self._update_state(user_id, menu='main', step=None, umo=event.unified_msg_origin)
        self._schedule_timeout(user_id)
        yield event.plain_result(await self._get_main_menu_text(user_id))

    @filter.command("酷我管理")
    async def admin_panel_main(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.admin_qq:
            yield event.plain_result("⛔ 您没有权限使用此命令。")
            return
        self._clear_state(user_id)
        self._update_state(user_id, menu='admin', step=None, umo=event.unified_msg_origin)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.command("管理面板")
    async def admin_panel_alias(self, event: AstrMessageEvent):
        await self.admin_panel_main(event)

    # ---------- 普通用户主菜单 ----------
    @filter.regex(r'^[0-4]$')
    async def handle_main_choice(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'main' or state.get('step'):
            return
        setattr(event, '_main_choice_processed', True)
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        text = event.message_str.strip()
        if text == "0":
            self._clear_state(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result("👋 已退出菜单")
        elif text == "1":
            self._update_state(user_id, menu='account', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._account_menu())
        elif text == "2":
            self._update_state(user_id, menu='verify', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_menu())
        elif text == "3":
            user_data = await self._load_data(user_id)
            if not user_data["accounts"]:
                yield event.plain_result("❌ 您还没有绑定账号")
                yield event.plain_result(await self._get_main_menu_text(user_id))
                return
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(user_data["accounts"])]
            prompt = "请选择要提交验证码的账号序号：\n" + "\n".join(lines) + "\n请输入序号，输入 0 取消："
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
            self._update_state(user_id, step='waiting_code_phone', tmp_data={'accounts': user_data["accounts"], 'trigger_msg': text})
        elif text == "4":
            self._update_state(user_id, menu='withdraw', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._withdraw_menu())

    # ---------- 账号管理子菜单 ----------
    @filter.regex(r'^[0-3]$')
    async def handle_account_choice(self, event: AstrMessageEvent):
        if getattr(event, '_main_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'account' or state.get('step'):
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_main_menu_text(user_id))
        elif text == "1":
            self._update_state(user_id, step='binding')
            self._schedule_timeout(user_id)
            yield event.plain_result("📱 请输入手机号#密码（可多个用 & 分隔），输入 0 取消")
        elif text == "2":
            user_data = await self._load_data(user_id)
            if not user_data["accounts"]:
                yield event.plain_result("❌ 您还没有绑定任何账号")
                self._update_state(user_id, menu='account', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._account_menu())
                return
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(user_data["accounts"])]
            prompt = "您的账号：\n" + "\n".join(lines) + "\n请输入要删除的序号（如 1），输入 0 取消："
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
            self._update_state(user_id, step='waiting_delete', tmp_data={'accounts': user_data["accounts"], 'trigger_msg': text})
        elif text == "3":
            user_data = await self._load_data(user_id)
            if user_data["accounts"]:
                lines = [f"📱 {a['phone']}" for a in user_data["accounts"]]
                auth_limit = user_data.get('auth_limit', 0)
                auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
                lines.append(f"📊 剩余授权次数：{auth_display}")
                yield event.plain_result("📋 您绑定的账号：\n" + "\n".join(lines))
            else:
                yield event.plain_result("❌ 您还没有绑定任何账号")
            self._update_state(user_id, menu='account', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._account_menu())

    # ---------- 验证码子菜单 ----------
    @filter.regex(r'^[0-2]$')
    async def handle_verify_choice(self, event: AstrMessageEvent):
        if getattr(event, '_main_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'verify' or state.get('step'):
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_main_menu_text(user_id))
        elif text == "1":
            setattr(event, '_verify_choice_processed', True)
            logger.info(f"用户 {user_id} 选择立即获取验证码")
            yield event.plain_result(await self._do_send_code(user_id))
        elif text == "2":
            setattr(event, '_timer_choice_processed', True)
            self._update_state(user_id, menu='verify_timer', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_verify_timer_menu(user_id))

    # ---------- 定时获取验证码子菜单 ----------
    @filter.regex(r'^[0-4]$')
    async def handle_verify_timer_choice(self, event: AstrMessageEvent):
        if any(getattr(event, f, False) for f in ['_main_choice_processed', '_verify_choice_processed', '_timer_choice_processed']):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'verify_timer' or state.get('step'):
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='verify', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_menu())
            return
        user_data = await self._load_data(user_id)
        job = user_data.get('scheduled_job', {})
        has_rule = bool(job.get('cron')) and job.get('enabled', False)
        if text == "1":
            setattr(event, '_timer_choice_processed', True)
            self._update_state(user_id, step='set_timer_cron')
            self._schedule_timeout(user_id)
            yield event.plain_result(
                "📝 请输入cron表达式（格式：秒 分 时 日 月 周）\n"
                "支持：*（任意）、数字、逗号分隔、范围(1-5)、步长(*/5)\n"
                "例如：15 55 8,12,16,19 * * *\n输入 0 取消")
        elif has_rule and text == "2":
            setattr(event, '_timer_choice_processed', True)
            self._update_state(user_id, step='confirm_delete_timer')
            self._schedule_timeout(user_id)
            yield event.plain_result("⚠️ 确定要删除定时规则吗？(y/n)")
        elif has_rule and text == "3":
            setattr(event, '_timer_choice_processed', True)
            yield event.plain_result("⏳ 正在执行定时任务，请稍候...")
            asyncio.create_task(self._execute_scheduled_job(user_id, is_manual=True))
            self._update_state(user_id, menu='verify_timer', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_verify_timer_menu(user_id))
        else:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 无效选项，请重新选择。")
            yield event.plain_result(await self._get_verify_timer_menu(user_id))

    @filter.regex(r'^[yYnN]$')
    async def handle_confirm_delete_timer(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'confirm_delete_timer':
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        if event.message_str.strip().lower() == 'y':
            user_data = await self._load_data(user_id)
            user_data['scheduled_job'] = {"cron": None, "enabled": False, "last_executed": None}
            await self._save_data(user_id, user_data)
            yield event.plain_result("✅ 定时规则已删除。")
        else:
            yield event.plain_result("操作已取消。")
        self._update_state(user_id, menu='verify_timer', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(await self._get_verify_timer_menu(user_id))

    @filter.regex(r'^.+$')
    async def handle_set_timer_cron(self, event: AstrMessageEvent):
        if getattr(event, '_timer_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'set_timer_cron':
            return
        text = event.message_str.strip()
        if text in ("q", "Q"):
            return
        if text == "0":
            self._update_state(user_id, menu='verify_timer', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_verify_timer_menu(user_id))
            return
        parts = text.split()
        if len(parts) not in (5, 6):
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ cron表达式格式错误，应为5或6个字段，请重新输入")
            return
        valid_pattern = re.compile(r'^(\*|\d+|[,\d-]+|(\*|\d+)/\d+|\d+-\d+)$')
        for part in parts:
            if not valid_pattern.match(part):
                self._schedule_timeout(user_id)
                yield event.plain_result(f"❌ 字段 '{part}' 格式无效，请重新输入")
                return
        user_data = await self._load_data(user_id)
        user_data['scheduled_job'] = {"cron": text, "enabled": True, "last_executed": None}
        await self._save_data(user_id, user_data)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"✅ 定时规则已设置：{text}\n定时任务将在匹配时间自动执行。")
        self._update_state(user_id, menu='verify_timer', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(await self._get_verify_timer_menu(user_id))

    # ---------- 提现子菜单 ----------
    @filter.regex(r'^[0-2]$')
    async def handle_withdraw_choice(self, event: AstrMessageEvent):
        if getattr(event, '_main_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'withdraw' or state.get('step'):
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_main_menu_text(user_id))
        elif text == "1":
            yield event.plain_result(await self._do_withdraw(user_id, event))
            self._update_state(user_id, menu='main', step=None)
        elif text == "2":
            user_data = await self._load_data(user_id)
            job = user_data.get('withdraw_scheduled_job', {})
            if job.get('enabled', False):
                job['enabled'] = False
                await self._save_data(user_id, user_data)
                yield event.plain_result("✅ 已停用整点提现")
            else:
                job['enabled'] = True
                if not job.get('cron'):
                    job['cron'] = self.default_withdraw_cron
                await self._save_data(user_id, user_data)
                yield event.plain_result(f"✅ 已启用整点提现\n📅 定时规则：{job['cron']}\n🕐 将在匹配时间自动发送提现请求")
            self._update_state(user_id, menu='withdraw', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._withdraw_menu())

    # ---------- 验证码发送选择（手动） ----------
    @filter.regex(r'^(all|[\d,]+|0)$')
    async def handle_send_select(self, event: AstrMessageEvent):
        if getattr(event, '_verify_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_send_select':
            return
        text = event.message_str.strip().lower()
        if text == "0":
            self._update_state(user_id, menu='verify', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_menu())
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        accounts = state.get('tmp_data', {}).get('accounts', [])
        user_data = await self._load_data(user_id)
        auth_limit = user_data.get('auth_limit', 0)
        phones_to_send, err = self._parse_phone_selection(text, accounts)
        if err:
            yield event.plain_result(err)
            return
        if auth_limit != -1 and len(phones_to_send) > auth_limit:
            yield event.plain_result(f"❌ 您选择了 {len(phones_to_send)} 个账号，但剩余授权次数为 {auth_limit}，请减少选择数量。")
            return
        if not phones_to_send:
            yield event.plain_result("❌ 未选择任何账号")
            self._update_state(user_id, menu='verify', step=None)
            yield event.plain_result(self._verify_menu())
            return
        account_map = {acc["phone"]: acc["password"] for acc in accounts}
        ordered = await self._send_codes_concurrently(phones_to_send, account_map, check_today=False)
        yield event.plain_result("📨 验证码发送结果：\n" + "\n".join(ordered))
        self._update_state(user_id, menu='main', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(await self._get_main_menu_text(user_id))

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
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_main_menu_text(user_id))
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
        setattr(event, '_code_phone_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"已选择账号 {phone}，请输入验证码（发送 q 取消）：")

    # ---------- 验证码输入（记录预登录任务） ----------
    @filter.regex(r'^.+$')
    async def handle_code_input(self, event: AstrMessageEvent):
        if getattr(event, '_code_phone_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_code_input':
            return
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='main', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(await self._get_main_menu_text(user_id))
            return
        if text in ("q", "Q"):
            return
        if not text:
            yield event.plain_result("❌ 验证码不能为空，请重新输入（发送 q 取消）")
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        phone = state.get('tmp_data', {}).get('phone')
        if not phone:
            yield event.plain_result("❌ 会话错误，请重新操作")
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(await self._get_main_menu_text(user_id))
            return
        if user_id not in self._code_cache_mem:
            self._code_cache_mem[user_id] = {}
        self._code_cache_mem[user_id][phone] = {"code": text, "expire": time.time() + 300}
        task = asyncio.create_task(self._pre_login(user_id, phone))
        self._pre_login_tasks[(user_id, phone)] = task
        yield event.plain_result(f"✅ 验证码 {text} 已缓存（5分钟有效）")
        self._update_state(user_id, menu='main', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(await self._get_main_menu_text(user_id))

    # ---------- 账号绑定/解绑 ----------
    @filter.regex(r'^(0|\d{11}#.+)$')
    async def handle_binding_input(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'binding':
            return
        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='account', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._account_menu())
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        user_data = await self._load_data(user_id)
        new_accounts, errors = [], []
        for part in text.split('&'):
            part = part.strip()
            if not part:
                continue
            try:
                phone, password = part.split('#', 1)
                phone, password = phone.strip(), password.strip()
                if not phone or not password:
                    errors.append(f"格式错误: {part}")
                    continue
                existing = next((a for a in user_data["accounts"] if a["phone"] == phone), None)
                if existing:
                    existing["password"] = password
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
            await self._save_data(user_id, user_data)
            yield event.plain_result("✅ 账号信息已更新（无新增）")
        self._update_state(user_id, menu='account', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._account_menu())

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
            self._schedule_timeout(user_id)
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
        user_data["accounts"] = [a for a in user_data["accounts"] if a["phone"] != phone_to_del]
        await self._save_data(user_id, user_data)
        yield event.plain_result(f"✅ 已删除账号 {phone_to_del}")
        self._update_state(user_id, menu='account', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._account_menu())

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
            yield event.plain_result(await self._get_main_menu_text(user_id))
            return
        if text == "off":
            user_data = await self._load_data(user_id)
            user_data["cron"] = ""
            await self._save_data(user_id, user_data)
            yield event.plain_result("✅ 已关闭定时获取验证码")
            self._update_state(user_id, menu='main', step=None)
            yield event.plain_result(await self._get_main_menu_text(user_id))
            return
        if len(text.split()) not in (5, 6):
            yield event.plain_result("❌ cron表达式格式错误，应为5或6个字段，请重新输入")
            return
        user_data = await self._load_data(user_id)
        user_data["cron"] = text
        await self._save_data(user_id, user_data)
        yield event.plain_result(f"✅ 定时规则已更新：{text}\n⚠️ 注意：当前环境不支持调度器，定时自动获取功能不可用，请使用立即获取。")
        self._update_state(user_id, menu='main', step=None)
        yield event.plain_result(await self._get_main_menu_text(user_id))

    # ---------- 全局 q/Q ----------
    @filter.regex(r'^[qQ]$')
    async def handle_global_q(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') or state.get('menu'):
            self._clear_state(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result("👋 已取消当前操作，返回主菜单")
            yield event.plain_result(await self._get_main_menu_text(user_id))
        else:
            yield event.plain_result("👋 已退出")

    # ---------- 预登录 ----------
    async def _pre_login(self, user_id: str, phone: str):
        try:
            user_data = await self._load_data(user_id)
            password = next((a.get("password") for a in user_data.get("accounts", []) if a.get("phone") == phone), None)
            if not password:
                logger.warning(f"预登录跳过：{phone} 无密码")
                return
            logger.info(f"🔄 开始预登录 {phone} ...")
            login_result = await asyncio.to_thread(login_kuwo, phone, password)
            if not login_result:
                logger.warning(f"⚠️ 预登录失败: {phone}")
                return
            uid, sid, appuid, _ = login_result
            self._login_cache_mem.setdefault(user_id, {})[phone] = {
                "uid": uid, "sid": sid, "appuid": appuid, "expire": time.time() + 600}
            logger.info(f"✅ 预登录成功并缓存: {phone}")
        except Exception as e:
            logger.error(f"预登录异常: {e}")
