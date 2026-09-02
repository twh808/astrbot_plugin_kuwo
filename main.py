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
from datetime import datetime, timedelta
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from urllib.parse import quote

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger

# ======================================================================
# 1. 加密常量（完整）
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
# 2. 加密与 API 函数（完整，与之前完全相同）
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
    data = f"username={quote(username)}&password={quote(base64.b64encode(password.encode()).decode())}&dev_id={dev_id}&user={str(uuid.uuid4()).replace('-', '')}&dev_name={quote(dev_name)}&urlencode=0&src=kwplayer_ar11.1.4.1_40.apk&devResolution=720*1080&&from=android&devType={devType}&sx={create_sx()}&version=11.1.4.1"
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
    ciphertext_base64 = base64.b64encode(ciphertext).decode('utf-8')
    return ciphertext_base64

def login_kuwo(username, password):
    try:
        q, encrypted_dev_id = get_q(username, password)
        url = 'http://ar.i.kuwo.cn/US_NEW/kuwo/login_kw'
        headers = {
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; MI 8 MIUI/V12.5.2.0.QEACNXM)',
            'Accept': '*/*',
            'Host': 'ar.i.kuwo.cn',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
        }
        params = {'f': 'ar', 'q': q}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        set_cookie = response.headers.get('Set-Cookie', '')
        username_match = re.search(r'uname3=([^;]+)', set_cookie)
        sid_match = re.search(r'websid=([^;]+)', set_cookie)
        uid_match = re.search(r'userid=([^;]+)', set_cookie)
        account_match = re.search(r't3kwid=([^;]+)', set_cookie)
        if all([username_match, sid_match, uid_match, account_match]):
            loginUid = uid_match.group(1)
            loginSid = sid_match.group(1)
            appUid = account_match.group(1)
            return loginUid, loginSid, appUid, encrypted_dev_id
        return None
    except Exception as e:
        logger.error(f"酷我登录异常: {e}")
        return None

def check_withdraw_today(loginUid, loginSid):
    url = 'https://integralapi.kuwo.cn/api/v1/online/sign/v1/withdrawDetails'
    params = {
        'loginUid': loginUid,
        'loginSid': loginSid,
        'pn': 1,
        'rn': 10,
    }
    headers = {
        'Host': 'integralapi.kuwo.cn',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://h5app.kuwo.cn',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KWMusic/12.1.2.0 DeviceModel/iPhone18,3 NetType/WIFI kuwopage',
        'Referer': 'https://h5app.kuwo.cn/apps/earning-sign/bill.html?random=1783815372333&kwflag=2758068154_1783815205',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Connection': 'keep-alive',
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5, verify=False)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if data.get('code') != 200:
            return False
        records = data.get('data', {}).get('list', [])
        today_str = datetime.now().strftime('%Y-%m-%d')
        for item in records:
            create_time = item.get('createTime', '')
            if create_time.startswith(today_str):
                if item.get('status') == 1 or '提现成功' in item.get('description', ''):
                    return True
        return False
    except Exception:
        return False

def send_code_once(loginUid, loginSid, appUid, encrypted_phone, quota_id='60004'):
    url = 'https://integralapi.kuwo.cn/api/v1/online/sign/v1/withdraw/sendCode'
    params = {
        'loginUid': loginUid,
        'loginSid': loginSid,
        'mobile': encrypted_phone,
        'appuid': appUid,
        'apiv': '9',
        'terminal': '1',
        'quotaId': quota_id,
        'type': 'blindBox',
    }
    headers = {
        'Host': 'integralapi.kuwo.cn',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; MEIZU 18 Pro Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046295 Mobile Safari/537.36/ kuwopage',
        'Origin': 'https://h5app.kuwo.cn',
        'X-Requested-With': 'cn.kuwo.player',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://h5app.kuwo.cn/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5, verify=False)
        text = resp.text
        try:
            data = resp.json()
            msg = data.get('msg', '')
            desc = data.get('data', {}).get('description', '')
            combined = f"{msg}|{desc}"
        except:
            combined = text
        lower_text = (text + str(data.get('msg', '')) + str(data.get('data', {}).get('description', ''))).lower()
        success = '发送成功' in lower_text
        return success, combined
    except Exception as e:
        return False, str(e)

FREQUENT_ERROR_KEYWORD = "频繁"

def withdraw_confirm_once(phone, loginUid, loginSid, appUid, encrypted_phone, code, kwtxid, verification_id, q36, seq=1, max_extra_retries=3, retry_delay_ms=4000):
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
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; MEIZU 18 Pro Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/148.0.7778.120 Mobile Safari/537.36/ kuwopage',
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
            resp = requests.get(url, headers=headers, params=params, timeout=5, verify=False)
            elapsed_ms = (time.time() - start) * 1000
            result = resp.json() if resp.status_code == 200 else {}
            msg = result.get('msg', '')
            data = result.get('data', {})
            text = data.get('text', '')
            description = data.get('description', '')
            combined = f"{msg}|{text}|{description}"
            last_combined = combined

            if attempt == 1:
                line = f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (第1次请求) | {resp.status_code} | {elapsed_ms:.1f}ms | {combined[:200]}"
            else:
                retry_num = attempt - 1
                line = f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 📱{phone} #{seq} (重试第{retry_num}次) | {resp.status_code} | {elapsed_ms:.1f}ms | {combined[:200]}"
            log_lines.append(line)

            if FREQUENT_ERROR_KEYWORD in combined and attempt <= max_extra_retries:
                log_lines.append(f"⚠️ {phone} 遭遇频繁错误（包含'{FREQUENT_ERROR_KEYWORD}'），{retry_delay_ms}ms 后重试...")
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

# ======================================================================
# 3. AstrBot 插件主类（优化所有管理面板列表显示）
# ======================================================================
class KuwoPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.default_auth_limit = self.config.get('default_auth_limit', 3)
        self.verification_cron = self.config.get('verification_cron', "12 55 8,12,16,19 * * *")
        self.default_withdraw_cron = self.config.get('default_withdraw_cron', "0 0 9,13,17,20 * * *")
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

    # ---------- 数据持久化 ----------
    async def _load_all_data(self) -> dict:
        return await self.get_kv_data("kuwo_data", {})

    async def _save_all_data(self, data: dict):
        await self.put_kv_data("kuwo_data", data)

    async def _load_data(self, user_id: str) -> dict:
        all_data = await self._load_all_data()
        if user_id not in all_data:
            all_data[user_id] = {
                "accounts": [],
                "auth_limit": self.default_auth_limit,
                "daily_withdraw": {},
                "verification_codes": {},
                "cron": self.verification_cron,
                "scheduled_job": {
                    "cron": None,
                    "enabled": False,
                    "last_executed": None
                },
                "withdraw_scheduled_job": {
                    "cron": self.default_withdraw_cron,
                    "enabled": True,
                    "last_executed": None
                },
                "last_withdraw_log": None
            }
        else:
            if "withdraw_scheduled_job" not in all_data[user_id]:
                all_data[user_id]["withdraw_scheduled_job"] = {
                    "cron": self.default_withdraw_cron,
                    "enabled": True,
                    "last_executed": None
                }
            else:
                if "enabled" not in all_data[user_id]["withdraw_scheduled_job"]:
                    all_data[user_id]["withdraw_scheduled_job"]["enabled"] = True
                if not all_data[user_id]["withdraw_scheduled_job"].get("cron"):
                    all_data[user_id]["withdraw_scheduled_job"]["cron"] = self.default_withdraw_cron
            if "last_withdraw_log" not in all_data[user_id]:
                all_data[user_id]["last_withdraw_log"] = None
        await self._save_all_data(all_data)
        return all_data[user_id]

    async def _save_data(self, user_id: str, user_data: dict):
        all_data = await self._load_all_data()
        all_data[user_id] = user_data
        await self._save_all_data(all_data)

    async def _delete_user_data(self, user_id: str) -> bool:
        all_data = await self._load_all_data()
        if user_id in all_data:
            del all_data[user_id]
            await self._save_all_data(all_data)
            return True
        return False

    # ---------- 状态管理 ----------
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

    # ---------- 超时管理 ----------
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
    async def _get_main_menu_text(self, user_id: str) -> str:
        user_data = await self._load_data(user_id)
        auth_limit = user_data.get('auth_limit', 0)
        auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
        return (
            f"🎵 酷我菜单 (剩余授权: {auth_display})\n"
            "1️⃣ 账号管理\n"
            "2️⃣ 获取验证码\n"
            "3️⃣ 提交验证码\n"
            "4️⃣ 提现\n"
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
            "2️⃣ 定时获取\n"
            "0️⃣ 返回主菜单"
        )

    def _verify_timer_menu(self) -> str:
        return (
            "⏰ 定时获取验证码\n"
            "1️⃣ 查看定时任务\n"
            "2️⃣ 设置定时规则\n"
            "3️⃣ 删除定时规则\n"
            "4️⃣ 立即执行一次\n"
            "0️⃣ 返回"
        )

    def _withdraw_menu(self) -> str:
        return (
            "💳 提现\n"
            "1️⃣ 立即提现\n"
            "2️⃣ 开启/停用整点提现\n"
            "0️⃣ 返回主菜单"
        )

    def _admin_menu(self) -> str:
        return (
            "🔧 酷我提现管理面板\n"
            "1️⃣ 查看所有账号\n"
            "2️⃣ 删除账号\n"
            "3️⃣ 修改授权次数（设置具体值或无限制）\n"
            "4️⃣ 发送验证码（可指定用户和账号）\n"
            "5️⃣ 为指定用户绑定账号\n"
            "6️⃣ 重置用户所有数据\n"
            "7️⃣ 查看最近提现记录\n"
            "0️⃣ 退出"
        )

    # ---------- 命令入口 ----------
    @filter.command("酷我")
    async def kuwo_menu(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        self._clear_state(user_id)
        self._update_state(user_id, menu='main', step=None, umo=event.unified_msg_origin)
        self._schedule_timeout(user_id)
        menu_text = await self._get_main_menu_text(user_id)
        self._schedule_timeout(user_id)
        yield event.plain_result(menu_text)

    @filter.command("酷我管理")
    async def admin_panel_main(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if user_id not in self.admin_qq:
            yield event.plain_result("⛔ 您没有权限使用此命令。")
            return
        self._clear_state(user_id)
        self._update_state(user_id, menu='admin', step=None, umo=event.unified_msg_origin)
        self._schedule_timeout(user_id)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.command("管理面板")
    async def admin_panel_alias(self, event: AstrMessageEvent):
        await self.admin_panel_main(event)

    # ---------- 普通用户主菜单处理器 ----------
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
            return
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
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 您还没有绑定账号")
                main_menu = await self._get_main_menu_text(user_id)
                self._schedule_timeout(user_id)
                yield event.plain_result(main_menu)
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

    # ---------- 普通用户子菜单 ----------
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
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        elif text == "1":
            self._update_state(user_id, step='binding')
            self._schedule_timeout(user_id)
            yield event.plain_result("📱 请输入手机号#密码（可多个用 & 分隔），输入 0 取消")
        elif text == "2":
            user_data = await self._load_data(user_id)
            if not user_data["accounts"]:
                self._schedule_timeout(user_id)
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
                self._schedule_timeout(user_id)
                yield event.plain_result("📋 您绑定的账号：\n" + "\n".join(lines))
            else:
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 您还没有绑定任何账号")
            self._update_state(user_id, menu='account', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._account_menu())

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
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        elif text == "1":
            setattr(event, '_verify_choice_processed', True)
            logger.info(f"用户 {user_id} 选择立即获取验证码")
            result_msg = await self._do_send_code(user_id)
            if result_msg:
                self._schedule_timeout(user_id)
                yield event.plain_result(result_msg)
            else:
                self._schedule_timeout(user_id)
                yield event.plain_result("⚠️ 内部错误，未能获取验证码菜单，请重试或重新绑定账号。")
            return
        elif text == "2":
            self._update_state(user_id, menu='verify_timer', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_timer_menu())

    # ========== 定时获取验证码子菜单 ==========
    @filter.regex(r'^[0-4]$')
    async def handle_verify_timer_choice(self, event: AstrMessageEvent):
        if getattr(event, '_main_choice_processed', False) or getattr(event, '_verify_choice_processed', False):
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
        elif text == "1":
            user_data = await self._load_data(user_id)
            job = user_data.get('scheduled_job', {})
            if not job.get('cron') or not job.get('enabled'):
                self._schedule_timeout(user_id)
                yield event.plain_result("⏰ 当前没有启用的定时任务。")
                self._schedule_timeout(user_id)
                yield event.plain_result(self._verify_timer_menu())
                return
            last_exec = job.get('last_executed', '从未执行')
            self._schedule_timeout(user_id)
            yield event.plain_result(
                f"⏰ 定时任务信息\n"
                f"📅 Cron: {job.get('cron')}\n"
                f"✅ 状态: 已启用\n"
                f"🕐 上次执行: {last_exec}"
            )
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_timer_menu())
        elif text == "2":
            setattr(event, '_timer_choice_processed', True)
            self._update_state(user_id, step='set_timer_cron')
            self._schedule_timeout(user_id)
            yield event.plain_result(
                "📝 请输入cron表达式（格式：秒 分 时 日 月 周）\n"
                "支持：*（任意）、数字、逗号分隔、范围(1-5)、步长(*/5)\n"
                "例如：12 55 8,12,16,19 * * *\n"
                "输入 0 取消"
            )
        elif text == "3":
            user_data = await self._load_data(user_id)
            job = user_data.get('scheduled_job', {})
            if not job.get('cron'):
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 当前没有定时规则。")
                self._schedule_timeout(user_id)
                yield event.plain_result(self._verify_timer_menu())
                return
            user_data['scheduled_job'] = {"cron": None, "enabled": False, "last_executed": None}
            await self._save_data(user_id, user_data)
            self._schedule_timeout(user_id)
            yield event.plain_result("✅ 定时规则已删除。")
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_timer_menu())
        elif text == "4":
            self._schedule_timeout(user_id)
            yield event.plain_result("⏳ 正在执行定时任务，请稍候...")
            asyncio.create_task(self._execute_scheduled_job(user_id, is_manual=True))

    # ========== 定时任务设置：输入 cron 表达式 ==========
    @filter.regex(r'^.+$')
    async def handle_set_timer_cron(self, event: AstrMessageEvent):
        if getattr(event, '_timer_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'set_timer_cron':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='verify_timer', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_timer_menu())
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
        user_data['scheduled_job'] = {
            "cron": text,
            "enabled": True,
            "last_executed": None
        }
        await self._save_data(user_id, user_data)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"✅ 定时规则已设置：{text}\n定时任务将在匹配时间自动执行。")
        self._update_state(user_id, menu='verify_timer', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._verify_timer_menu())

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
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        elif text == "1":  # 立即提现
            result = await self._do_withdraw(user_id, event)
            self._schedule_timeout(user_id)
            yield event.plain_result(result)
            self._update_state(user_id, menu='main', step=None)
        elif text == "2":  # 切换整点提现状态
            user_data = await self._load_data(user_id)
            job = user_data.get('withdraw_scheduled_job', {})
            if job.get('enabled', False):
                user_data['withdraw_scheduled_job']['enabled'] = False
                await self._save_data(user_id, user_data)
                self._schedule_timeout(user_id)
                yield event.plain_result("✅ 已停用整点提现")
            else:
                user_data['withdraw_scheduled_job']['enabled'] = True
                if not user_data['withdraw_scheduled_job'].get('cron'):
                    user_data['withdraw_scheduled_job']['cron'] = self.default_withdraw_cron
                await self._save_data(user_id, user_data)
                self._schedule_timeout(user_id)
                cron = user_data['withdraw_scheduled_job']['cron']
                yield event.plain_result(
                    f"✅ 已启用整点提现\n"
                    f"📅 定时规则：{cron}\n"
                    f"🕐 将在匹配时间自动发送提现请求"
                )
            self._update_state(user_id, menu='withdraw', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._withdraw_menu())

    # ---------- 普通用户辅助 ----------
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
            self._schedule_timeout(user_id)
            yield event.plain_result(self._verify_menu())
            return

        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        accounts = state.get('tmp_data', {}).get('accounts', [])
        user_data = await self._load_data(user_id)
        auth_limit = user_data.get('auth_limit', 0)

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
                        self._schedule_timeout(user_id)
                        yield event.plain_result(f"❌ 序号 {idx_str} 无效，请重新输入")
                        return
            except ValueError:
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 输入格式错误，请输入数字序号（用逗号分隔）或 all")
                return

        if auth_limit != -1 and len(phones_to_send) > auth_limit:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 您选择了 {len(phones_to_send)} 个账号，但剩余授权次数为 {auth_limit}，请减少选择数量。")
            return

        if not phones_to_send:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 未选择任何账号")
            self._update_state(user_id, menu='verify', step=None)
            self._schedule_timeout(user_id)
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
        self._schedule_timeout(user_id)
        yield event.plain_result("📨 验证码发送结果：\n" + "\n".join(results))
        self._update_state(user_id, menu='main', step=None)
        main_menu = await self._get_main_menu_text(user_id)
        self._schedule_timeout(user_id)
        yield event.plain_result(main_menu)

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
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        try:
            idx = int(text)
        except:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字")
            return
        accounts = state.get('tmp_data', {}).get('accounts', [])
        if idx < 1 or idx > len(accounts):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(accounts)} 之间的数字")
            return
        phone = accounts[idx-1]["phone"]
        self._update_state(user_id, step='waiting_code_input', tmp_data={'phone': phone})
        setattr(event, '_code_phone_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"已选择账号 {phone}，请输入验证码（发送 q 取消）：")

    @filter.regex(r'^.+$')
    async def handle_code_input(self, event: AstrMessageEvent):
        if getattr(event, '_code_phone_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'waiting_code_input':
            return
        text = event.message_str.strip()
        if text in ("0", "q", "Q"):
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)
        code = text
        if not code:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 验证码不能为空")
            return
        phone = state.get('tmp_data', {}).get('phone')
        if not phone:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 会话错误，请重新操作")
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        user_data = await self._load_data(user_id)
        user_data["verification_codes"][phone] = {"code": code, "expire": time.time() + 300}
        await self._save_data(user_id, user_data)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"✅ 验证码 {code} 已缓存（5分钟有效）")
        self._update_state(user_id, menu='main', step=None)
        main_menu = await self._get_main_menu_text(user_id)
        self._schedule_timeout(user_id)
        yield event.plain_result(main_menu)

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
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 绑定失败：\n" + "\n".join(errors) + "\n请重新输入")
            return
        if new_accounts:
            user_data["accounts"].extend(new_accounts)
            await self._save_data(user_id, user_data)
            self._schedule_timeout(user_id)
            yield event.plain_result(f"✅ 成功绑定 {len(new_accounts)} 个账号，当前共 {len(user_data['accounts'])} 个账号")
        else:
            self._schedule_timeout(user_id)
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
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字")
            self._update_state(user_id, menu='account', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._account_menu())
            return
        accounts = state.get('tmp_data', {}).get('accounts', [])
        if idx < 1 or idx > len(accounts):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(accounts)} 之间的数字")
            return
        user_data = await self._load_data(user_id)
        phone_to_del = accounts[idx-1]["phone"]
        user_data["accounts"] = [acc for acc in user_data["accounts"] if acc["phone"] != phone_to_del]
        await self._save_data(user_id, user_data)
        self._schedule_timeout(user_id)
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
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        if text == "off":
            user_data = await self._load_data(user_id)
            user_data["cron"] = ""
            await self._save_data(user_id, user_data)
            self._schedule_timeout(user_id)
            yield event.plain_result("✅ 已关闭定时获取验证码")
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
            return
        parts = text.split()
        if len(parts) not in (5, 6):
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ cron表达式格式错误，应为5或6个字段，请重新输入")
            return
        user_data = await self._load_data(user_id)
        user_data["cron"] = text
        await self._save_data(user_id, user_data)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"✅ 定时规则已更新：{text}\n⚠️ 注意：当前环境不支持调度器，定时自动获取功能不可用，请使用立即获取。")
        self._update_state(user_id, menu='main', step=None)
        main_menu = await self._get_main_menu_text(user_id)
        self._schedule_timeout(user_id)
        yield event.plain_result(main_menu)

    @filter.regex(r'^[qQ]$')
    async def handle_global_q(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') or state.get('menu'):
            self._clear_state(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result("👋 已取消当前操作，返回主菜单")
            main_menu = await self._get_main_menu_text(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result(main_menu)
        else:
            self._schedule_timeout(user_id)
            yield event.plain_result("👋 已退出")

    # ---------- 核心提现逻辑（并发版，记录日志） ----------
    async def _process_withdraw(self, user_id: str, event: AstrMessageEvent = None) -> str:
        """
        执行提现，并发处理多个账号，返回结果字符串并记录日志
        """
        user_data = await self._load_data(user_id)
        if not user_data["accounts"]:
            return "❌ 请先绑定账号"
        auth_limit = user_data.get('auth_limit', 0)
        if auth_limit == 0:
            return "❌ 授权次数已用完，无法提现"
        if auth_limit < 0 and auth_limit != -1:
            return "❌ 授权次数无效"

        all_accounts = user_data["accounts"]
        if auth_limit != -1:
            accounts = all_accounts[:auth_limit]
        else:
            accounts = all_accounts

        if not accounts:
            return "❌ 没有可用的账号"

        codes = user_data.get("verification_codes", {})
        valid_accounts = []
        for acc in accounts:
            phone = acc["phone"]
            code_info = codes.get(phone)
            if code_info and time.time() <= code_info.get("expire", 0):
                valid_accounts.append(acc)

        if not valid_accounts:
            return "❌ 所有账号均未配置有效验证码，请先获取验证码"

        async def withdraw_single(acc):
            phone = acc["phone"]
            password = acc["password"]
            code_info = codes.get(phone)
            if not code_info:
                return (phone, None, "跳过（无验证码）", False)

            login_result = login_kuwo(phone, password)
            if not login_result:
                return (phone, None, "登录失败", False)
            uid, sid, appuid, _ = login_result

            if check_withdraw_today(uid, sid):
                return (phone, None, "今日已提现，跳过", False)

            encrypted_phone = encrypt_phone(phone)
            code = code_info["code"]
            log_lines, final_msg, is_success = await asyncio.to_thread(
                withdraw_confirm_once,
                phone, uid, sid, appuid, encrypted_phone, code,
                self.kwtxid, self.verification_id, self.q36,
                seq=1, max_extra_retries=self.max_retries, retry_delay_ms=self.retry_delay_ms
            )
            return (phone, final_msg, final_msg, is_success)

        tasks = [withdraw_single(acc) for acc in valid_accounts]
        results = await asyncio.gather(*tasks)

        success_count = 0
        result_lines = []
        for phone, final_msg, desc, is_success in results:
            if is_success:
                success_count += 1
                result_lines.append(f"✅ 提现成功 {phone}: {desc}")
            else:
                result_lines.append(f"❌ 提现失败 {phone}: {desc}")

        skipped_phones = [acc["phone"] for acc in accounts if acc["phone"] not in [r[0] for r in results]]
        for phone in skipped_phones:
            result_lines.append(f"⏭️ {phone}: 无有效验证码，已跳过")

        if success_count > 0 and auth_limit != -1:
            user_data["auth_limit"] -= success_count
            if user_data["auth_limit"] < 0:
                user_data["auth_limit"] = 0

        for phone in [r[0] for r in results if r[3]]:
            if phone in user_data["verification_codes"]:
                del user_data["verification_codes"][phone]

        today = datetime.now().strftime("%Y-%m-%d")
        if today not in user_data["daily_withdraw"]:
            user_data["daily_withdraw"][today] = {}
        for phone, _, _, is_success in results:
            if is_success:
                user_data["daily_withdraw"][today][phone] = True

        total = len(accounts)
        summary = (
            f"📊 【提现完成】\n"
            f"✅ 成功: {success_count}\n"
            f"❌ 失败: {len(results) - success_count}\n"
            f"⏭️ 跳过: {total - len(valid_accounts) + (len(valid_accounts) - len(results))}\n"
            f"📈 剩余可用次数: {'无限制' if user_data['auth_limit'] == -1 else user_data['auth_limit']}\n"
            f"━━━━━━━━━━━━\n"
        )
        full_result = summary + "\n".join(result_lines)

        # 存储最近提现日志
        user_data["last_withdraw_log"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": full_result
        }
        await self._save_data(user_id, user_data)

        return full_result

    # ---------- 立即提现 ----------
    async def _do_withdraw(self, user_id: str, event: AstrMessageEvent) -> str:
        """立即提现，发送结果并附带主菜单"""
        result = await self._process_withdraw(user_id, event)
        main_menu = await self._get_main_menu_text(user_id)
        return result + "\n" + main_menu

    # ---------- 定时提现任务 ----------
    async def _execute_withdraw_scheduled_job(self, user_id: str):
        """定时提现任务，发送结果通知给用户"""
        try:
            user_data = await self._load_data(user_id)
            job = user_data.get('withdraw_scheduled_job', {})
            if not job.get('cron') or not job.get('enabled'):
                logger.info(f"用户 {user_id} 提现定时任务未启用或无规则")
                return

            last_exec = job.get('last_executed')
            if last_exec:
                try:
                    last_dt = datetime.strptime(last_exec, '%Y-%m-%d %H:%M:%S')
                    if (datetime.now() - last_dt).total_seconds() < 1:
                        return
                except:
                    pass

            # 执行提现
            result = await self._process_withdraw(user_id, None)
            user_data['withdraw_scheduled_job']['last_executed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await self._save_data(user_id, user_data)

            # 主动发送给用户
            state = self._get_state(user_id)
            umo = state.get('umo')
            if umo:
                try:
                    await self.context.send_message(umo, MessageChain().message(f"⏰ 整点提现完成\n{result}"))
                except Exception as e:
                    logger.error(f"发送提现定时结果失败: {e}")
            else:
                logger.info(f"提现定时任务结果（用户 {user_id}）：\n{result}")
        except Exception as e:
            logger.error(f"提现定时任务执行失败: {e}")

    # ---------- 获取验证码核心 ----------
    async def _do_send_code(self, user_id: str) -> str:
        logger.info(f"🟢 _do_send_code 被调用，用户 {user_id}")
        user_data = await self._load_data(user_id)
        auth_limit = user_data.get('auth_limit', 0)
        if auth_limit == 0:
            logger.warning(f"用户 {user_id} 授权次数为0，无法获取验证码")
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            return "❌ 授权次数已用完，无法获取验证码\n" + main_menu

        accounts = user_data.get("accounts", [])
        logger.info(f"用户 {user_id} 当前账号数量: {len(accounts)}")
        if not accounts:
            logger.warning("账号列表为空")
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            return "❌ 您还没有绑定任何账号\n" + main_menu
        try:
            lines = [f"{idx+1}. {acc['phone']}" for idx, acc in enumerate(accounts)]
        except Exception as e:
            logger.error(f"构建账号列表时出错: {e}", exc_info=True)
            self._update_state(user_id, menu='main', step=None)
            main_menu = await self._get_main_menu_text(user_id)
            return "❌ 账号数据格式异常，请重新绑定\n" + main_menu
        prompt = "📨 请输入要发送验证码的账号序号（多个用逗号分隔），输入 all 发送全部，输入 0 返回：\n" + "\n".join(lines)
        self._update_state(user_id, step='waiting_send_select', tmp_data={'accounts': accounts})
        logger.info(f"返回提示: {prompt[:50]}...")
        return prompt

    # ---------- 定时获取验证码执行 ----------
    async def _execute_scheduled_job(self, user_id: str, is_manual: bool = False):
        try:
            user_data = await self._load_data(user_id)
            job = user_data.get('scheduled_job', {})
            if not job.get('cron') or not job.get('enabled'):
                logger.info(f"用户 {user_id} 定时任务未启用或无规则")
                return

            accounts = user_data.get('accounts', [])
            if not accounts:
                logger.info(f"用户 {user_id} 无绑定账号，跳过定时任务")
                return

            auth_limit = user_data.get('auth_limit', 0)
            if auth_limit == 0:
                logger.warning(f"用户 {user_id} 授权次数为0，定时任务跳过")
                return

            state = self._get_state(user_id)
            umo = state.get('umo')
            if not umo:
                logger.warning(f"用户 {user_id} 没有可用会话，无法发送定时通知，但任务仍会执行")

            target_accounts = accounts[:auth_limit] if auth_limit != -1 else accounts
            results = []
            for acc in target_accounts:
                phone = acc['phone']
                password = acc['password']
                login = login_kuwo(phone, password)
                if not login:
                    results.append(f"❌ {phone}: 登录失败")
                    continue
                uid, sid, appuid, _ = login
                encrypted_phone = encrypt_phone(phone)
                success, msg = send_code_once(uid, sid, appuid, encrypted_phone, self.quota_id)
                results.append(f"{'✅' if success else '❌'} {phone}: {msg}")
                await asyncio.sleep(0.5)

            user_data['scheduled_job']['last_executed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await self._save_data(user_id, user_data)

            result_msg = f"⏰ 定时获取验证码完成\n" + "\n".join(results)
            if is_manual:
                result_msg = "🔹 手动执行结果：\n" + result_msg
            if umo:
                try:
                    await self.context.send_message(umo, MessageChain().message(result_msg))
                except Exception as e:
                    logger.error(f"发送定时结果失败: {e}")
            else:
                logger.info(f"定时任务执行结果（用户 {user_id}）：\n{result_msg}")

        except Exception as e:
            logger.error(f"执行定时任务失败: {e}")

    # ---------- 调度器循环（每秒检查） ----------
    async def _scheduler_loop(self):
        logger.info("🕐 定时调度器开始运行，每秒检查一次")
        while self.scheduler_running:
            try:
                now = datetime.now()
                all_data = await self._load_all_data()
                for user_id, user_data in all_data.items():
                    # 检查验证码定时任务
                    job = user_data.get('scheduled_job', {})
                    if job.get('cron') and job.get('enabled'):
                        last_exec = job.get('last_executed')
                        if last_exec:
                            try:
                                last_dt = datetime.strptime(last_exec, '%Y-%m-%d %H:%M:%S')
                                if (now - last_dt).total_seconds() < 1:
                                    continue
                            except:
                                pass
                        cron_dict = self._parse_cron(job['cron'])
                        if self._match_cron(cron_dict, now):
                            logger.info(f"⏰ 验证码定时任务触发: 用户 {user_id}, cron: {job['cron']}")
                            asyncio.create_task(self._execute_scheduled_job(user_id))

                    # 检查提现定时任务
                    wjob = user_data.get('withdraw_scheduled_job', {})
                    if wjob.get('cron') and wjob.get('enabled'):
                        last_exec = wjob.get('last_executed')
                        if last_exec:
                            try:
                                last_dt = datetime.strptime(last_exec, '%Y-%m-%d %H:%M:%S')
                                if (now - last_dt).total_seconds() < 1:
                                    continue
                            except:
                                pass
                        cron_dict = self._parse_cron(wjob['cron'])
                        if self._match_cron(cron_dict, now):
                            logger.info(f"⏰ 提现定时任务触发: 用户 {user_id}, cron: {wjob['cron']}")
                            asyncio.create_task(self._execute_withdraw_scheduled_job(user_id))
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
            await asyncio.sleep(1)

    def _parse_cron(self, cron_expr: str) -> dict:
        parts = cron_expr.split()
        if len(parts) == 5:
            parts = ['*'] + parts
        fields = ['second', 'minute', 'hour', 'day', 'month', 'weekday']
        result = {}
        for i, part in enumerate(parts):
            if part == '*':
                result[fields[i]] = None
            else:
                values = set()
                if '/' in part:
                    base, step = part.split('/')
                    step = int(step)
                    if base == '*':
                        max_val = {'second': 59, 'minute': 59, 'hour': 23, 'day': 31, 'month': 12, 'weekday': 7}[fields[i]]
                        values = set(range(0, max_val+1, step))
                    else:
                        if '-' in base:
                            start, end = base.split('-')
                            start, end = int(start), int(end)
                            values = set(range(start, end+1, step))
                        else:
                            values = {int(base)}
                elif '-' in part:
                    start, end = part.split('-')
                    start, end = int(start), int(end)
                    values = set(range(start, end+1))
                elif ',' in part:
                    values = set(int(x) for x in part.split(','))
                else:
                    values = {int(part)}
                result[fields[i]] = sorted(values) if values else None
        return result

    def _match_cron(self, cron_dict: dict, dt: datetime) -> bool:
        for field, values in cron_dict.items():
            if values is None:
                continue
            if field == 'second':
                current = dt.second
            elif field == 'minute':
                current = dt.minute
            elif field == 'hour':
                current = dt.hour
            elif field == 'day':
                current = dt.day
            elif field == 'month':
                current = dt.month
            elif field == 'weekday':
                current = dt.weekday() + 1
            if current not in values:
                return False
        return True

    # ---------- 管理员查看最近提现记录 ----------
    async def _view_last_withdraw_logs(self) -> str:
        all_data = await self._load_all_data()
        if not all_data:
            return "📭 暂无用户数据。"
        lines = []
        for uid, udata in all_data.items():
            log = udata.get('last_withdraw_log')
            if log:
                time_str = log.get('time', '未知时间')
                result = log.get('result', '')
                lines.append(f"👤 {uid}\n   🕐 {time_str}\n   📝 {result[:200]}{'...' if len(result)>200 else ''}")
            else:
                lines.append(f"👤 {uid} -> 暂无提现记录")
        return "📋 最近提现记录：\n" + "\n\n".join(lines)

    # ---------- 管理员菜单主处理器（优化所有列表显示） ----------
    @filter.regex(r'^[0-7]$')
    async def handle_admin_choice(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('menu') != 'admin' or state.get('step'):
            return
        if user_id not in self.admin_qq:
            self._clear_state(user_id)
            yield event.plain_result("⛔ 权限已变更，请重新操作。")
            return

        setattr(event, '_admin_choice_processed', True)
        self._cancel_timeout(user_id)
        self._schedule_timeout(user_id)

        text = event.message_str.strip()
        if text == "0":
            self._clear_state(user_id)
            self._schedule_timeout(user_id)
            yield event.plain_result("👋 已退出管理面板")
            return
        elif text == "1":  # 查看所有账号
            all_data = await self._load_all_data()
            if not all_data:
                self._schedule_timeout(user_id)
                yield event.plain_result("📭 暂无用户数据。")
                self._update_state(user_id, menu='admin', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._admin_menu())
                return
            lines = []
            for uid, udata in all_data.items():
                accounts = udata.get('accounts', [])
                if accounts:
                    phones = ', '.join([a['phone'] for a in accounts])
                    lines.append(f"👤 {uid} -> {phones}")
                else:
                    lines.append(f"👤 {uid} -> (无账号)")
            result = "📋 所有用户账号信息：\n" + "\n".join(lines)
            self._schedule_timeout(user_id)
            yield event.plain_result(result)
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
        elif text == "2":  # 删除账号 - 优化列表
            all_data = await self._load_all_data()
            if not all_data:
                self._schedule_timeout(user_id)
                yield event.plain_result("📭 暂无用户数据。")
                self._update_state(user_id, menu='admin', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._admin_menu())
                return
            user_list = []
            for idx, (uid, udata) in enumerate(all_data.items(), 1):
                accounts = udata.get('accounts', [])
                auth_limit = udata.get('auth_limit', 0)
                auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
                if accounts:
                    phones_lines = "\n   ".join([f"📱 {p}" for p in [a['phone'] for a in accounts]])
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   {phones_lines}")
                else:
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   (无账号)")
            prompt = "请选择要删除账号的用户序号：\n" + "\n".join(user_list) + "\n请输入序号，输入 0 取消："
            self._update_state(user_id, step='admin_del_select', tmp_data={'all_users': list(all_data.keys())})
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
        elif text == "3":  # 修改授权 - 已优化
            all_data = await self._load_all_data()
            if not all_data:
                self._schedule_timeout(user_id)
                yield event.plain_result("📭 暂无用户数据。")
                self._update_state(user_id, menu='admin', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._admin_menu())
                return
            user_list = []
            for idx, (uid, udata) in enumerate(all_data.items(), 1):
                accounts = udata.get('accounts', [])
                auth_limit = udata.get('auth_limit', 0)
                auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
                if accounts:
                    phones_lines = "\n   ".join([f"📱 {p}" for p in [a['phone'] for a in accounts]])
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   {phones_lines}")
                else:
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   (无账号)")
            prompt = "请选择要修改授权次数的用户序号：\n" + "\n".join(user_list) + "\n请输入序号，输入 0 取消："
            self._update_state(user_id, step='admin_mod_limit_select', tmp_data={'all_users': list(all_data.keys())})
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
        elif text == "4":  # 发送验证码 - 优化列表
            all_data = await self._load_all_data()
            if not all_data:
                self._schedule_timeout(user_id)
                yield event.plain_result("📭 暂无用户数据。")
                self._update_state(user_id, menu='admin', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._admin_menu())
                return
            user_list = []
            for idx, (uid, udata) in enumerate(all_data.items(), 1):
                accounts = udata.get('accounts', [])
                auth_limit = udata.get('auth_limit', 0)
                auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
                if accounts:
                    phones_lines = "\n   ".join([f"📱 {p}" for p in [a['phone'] for a in accounts]])
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   {phones_lines}")
                else:
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   (无账号)")
            prompt = "请选择要发送验证码的用户序号：\n" + "\n".join(user_list) + "\n请输入序号，输入 0 取消："
            self._update_state(user_id, step='admin_send_code_select_user', tmp_data={'all_users': list(all_data.keys())})
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
        elif text == "5":  # 绑定账号
            self._update_state(user_id, step='admin_bind_user')
            self._schedule_timeout(user_id)
            yield event.plain_result("请输入要绑定账号的目标用户QQ号：")
        elif text == "6":  # 重置数据 - 优化列表
            all_data = await self._load_all_data()
            if not all_data:
                self._schedule_timeout(user_id)
                yield event.plain_result("📭 暂无用户数据。")
                self._update_state(user_id, menu='admin', step=None)
                self._schedule_timeout(user_id)
                yield event.plain_result(self._admin_menu())
                return
            user_list = []
            for idx, (uid, udata) in enumerate(all_data.items(), 1):
                accounts = udata.get('accounts', [])
                auth_limit = udata.get('auth_limit', 0)
                auth_display = "无限制" if auth_limit == -1 else f"{auth_limit}次"
                if accounts:
                    phones_lines = "\n   ".join([f"📱 {p}" for p in [a['phone'] for a in accounts]])
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   {phones_lines}")
                else:
                    user_list.append(f"{idx}. QQ {uid}（剩余授权：{auth_display}）\n   (无账号)")
            prompt = "请选择要重置数据的用户序号：\n" + "\n".join(user_list) + "\n请输入序号，输入 0 取消："
            self._update_state(user_id, step='admin_reset_select', tmp_data={'all_users': list(all_data.keys())})
            self._schedule_timeout(user_id)
            yield event.plain_result(prompt)
        elif text == "7":  # 查看最近提现记录
            result = await self._view_last_withdraw_logs()
            self._schedule_timeout(user_id)
            yield event.plain_result(result)
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())

    # ---------- 管理员子步骤 ----------
    @filter.regex(r'^\d+$')
    async def handle_admin_del_select(self, event: AstrMessageEvent):
        if getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_del_select':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        try:
            idx = int(text) - 1
        except:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字序号。")
            return

        all_users = state.get('tmp_data', {}).get('all_users', [])
        if idx < 0 or idx >= len(all_users):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(all_users)} 之间的数字。")
            return

        target_uid = all_users[idx]
        all_data = await self._load_all_data()
        accounts = all_data[target_uid].get('accounts', [])
        if not accounts:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"📭 用户 {target_uid} 没有绑定账号。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        lines = [f"{idx+1}. {a['phone']}" for idx, a in enumerate(accounts)]
        prompt = f"用户 {target_uid} 的账号列表：\n" + "\n".join(lines) + "\n请输入要删除的序号（多个用逗号分隔），输入 0 取消："
        self._update_state(user_id, step='admin_del_choose', tmp_data={'target_uid': target_uid, 'accounts': accounts})
        setattr(event, '_admin_sub_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(prompt)

    @filter.regex(r'^[\d,]+$')
    async def handle_admin_del_choose(self, event: AstrMessageEvent):
        if getattr(event, '_admin_sub_processed', False) or getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_del_choose':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        indices = text.split(',')
        tmp = state.get('tmp_data', {})
        target_uid = tmp.get('target_uid')
        accounts = tmp.get('accounts', [])
        to_delete = []
        for idx_str in indices:
            try:
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(accounts):
                    to_delete.append(accounts[idx]['phone'])
                else:
                    self._schedule_timeout(user_id)
                    yield event.plain_result(f"❌ 序号 {idx_str} 无效，请重新输入")
                    return
            except ValueError:
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 请输入有效的数字序号，用逗号分隔。")
                return

        if not to_delete:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 未选择任何账号。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        all_data = await self._load_all_data()
        if target_uid in all_data:
            user_data = all_data[target_uid]
            user_data['accounts'] = [a for a in user_data['accounts'] if a['phone'] not in to_delete]
            await self._save_data(target_uid, user_data)
            self._schedule_timeout(user_id)
            yield event.plain_result(f"✅ 已删除用户 {target_uid} 的账号：{', '.join(to_delete)}")
        else:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 用户 {target_uid} 数据不存在。")

        self._update_state(user_id, menu='admin', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.regex(r'^\d+$')
    async def handle_admin_mod_limit_select(self, event: AstrMessageEvent):
        if getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_mod_limit_select':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        try:
            idx = int(text) - 1
        except:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字序号。")
            return

        all_users = state.get('tmp_data', {}).get('all_users', [])
        if idx < 0 or idx >= len(all_users):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(all_users)} 之间的数字。")
            return

        target_uid = all_users[idx]
        self._update_state(user_id, step='admin_mod_limit_value', tmp_data={'target_uid': target_uid})
        setattr(event, '_admin_sub_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"已选择用户 {target_uid}，请输入新的授权次数（输入 -1 表示无限制）：")

    @filter.regex(r'^-?\d+$')
    async def handle_admin_mod_limit_value(self, event: AstrMessageEvent):
        if getattr(event, '_admin_sub_processed', False) or getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_mod_limit_value':
            return

        new_limit = int(event.message_str.strip())
        tmp = state.get('tmp_data', {})
        target_uid = tmp.get('target_uid')

        all_data = await self._load_all_data()
        if target_uid not in all_data:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 用户 {target_uid} 不存在。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        user_data = all_data[target_uid]
        user_data['auth_limit'] = new_limit
        await self._save_data(target_uid, user_data)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"✅ 用户 {target_uid} 的授权次数已设为 {new_limit if new_limit != -1 else '无限制'} 。")

        self._update_state(user_id, menu='admin', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.regex(r'^\d+$')
    async def handle_admin_send_code_select_user(self, event: AstrMessageEvent):
        if getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_send_code_select_user':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        try:
            idx = int(text) - 1
        except:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字序号。")
            return

        all_users = state.get('tmp_data', {}).get('all_users', [])
        if idx < 0 or idx >= len(all_users):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(all_users)} 之间的数字。")
            return

        target_uid = all_users[idx]
        all_data = await self._load_all_data()
        accounts = all_data[target_uid].get('accounts', [])
        if not accounts:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"📭 用户 {target_uid} 没有绑定账号。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        lines = [f"{idx+1}. {a['phone']}" for idx, a in enumerate(accounts)]
        prompt = f"用户 {target_uid} 的账号列表：\n" + "\n".join(lines) + "\n请输入要发送验证码的账号序号（多个用逗号分隔），输入 all 发送全部，输入 0 取消："
        self._update_state(user_id, step='admin_send_code_select_account', tmp_data={'target_uid': target_uid, 'accounts': accounts})
        setattr(event, '_admin_sub_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(prompt)

    @filter.regex(r'^(all|[\d,]+|0|q|Q)$')
    async def handle_admin_send_code_select_account(self, event: AstrMessageEvent):
        if getattr(event, '_admin_sub_processed', False) or getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_send_code_select_account':
            return

        text = event.message_str.strip().lower()
        if text in ("0", "q"):
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        tmp = state.get('tmp_data', {})
        target_uid = tmp.get('target_uid')
        accounts = tmp.get('accounts', [])
        if not target_uid or not accounts:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 会话错误，请重新操作。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

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
                        self._schedule_timeout(user_id)
                        yield event.plain_result(f"❌ 序号 {idx_str} 无效，请重新输入")
                        return
            except ValueError:
                self._schedule_timeout(user_id)
                yield event.plain_result("❌ 输入格式错误，请输入数字序号（用逗号分隔）或 all")
                return

        user_data = await self._load_data(target_uid)
        auth_limit = user_data.get('auth_limit', 0)
        if auth_limit == 0:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 用户 {target_uid} 的授权次数为0，无法发送验证码。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return
        if auth_limit != -1 and len(phones_to_send) > auth_limit:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 选择的账号数量 {len(phones_to_send)} 超出用户 {target_uid} 的授权次数 {auth_limit}，请减少。")
            return

        if not phones_to_send:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 未选择任何账号")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
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
            uid_kuwo, sid, appuid, _ = login
            encrypted_phone = encrypt_phone(phone)
            success, msg = send_code_once(uid_kuwo, sid, appuid, encrypted_phone, self.quota_id)
            results.append(f"{'✅' if success else '❌'} {phone}: {msg}")
            await asyncio.sleep(0.5)

        self._schedule_timeout(user_id)
        yield event.plain_result("📨 验证码发送结果：\n" + "\n".join(results))
        self._update_state(user_id, menu='admin', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.regex(r'^\d+$')
    async def handle_admin_reset_select(self, event: AstrMessageEvent):
        if getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_reset_select':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        try:
            idx = int(text) - 1
        except:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 请输入有效的数字序号。")
            return

        all_users = state.get('tmp_data', {}).get('all_users', [])
        if idx < 0 or idx >= len(all_users):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 序号无效，请输入 1 到 {len(all_users)} 之间的数字。")
            return

        target_uid = all_users[idx]
        self._update_state(user_id, step='admin_reset_confirm', tmp_data={'target_uid': target_uid})
        setattr(event, '_admin_sub_processed', True)
        self._schedule_timeout(user_id)
        yield event.plain_result(f"⚠️ 即将重置用户 {target_uid} 的所有数据（包括账号、授权次数、验证码缓存等），确定继续？(y/n)")

    @filter.regex(r'^[yYnN]$')
    async def handle_admin_confirm(self, event: AstrMessageEvent):
        if getattr(event, '_admin_sub_processed', False) or getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        step = state.get('step')
        if step != 'admin_reset_confirm':
            return

        choice = event.message_str.strip().lower()
        if choice != 'y':
            self._schedule_timeout(user_id)
            yield event.plain_result("操作已取消。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        tmp = state.get('tmp_data', {})
        target_uid = tmp.get('target_uid')
        if await self._delete_user_data(target_uid):
            self._schedule_timeout(user_id)
            yield event.plain_result(f"✅ 已重置用户 {target_uid} 的所有数据。")
        else:
            self._schedule_timeout(user_id)
            yield event.plain_result(f"❌ 用户 {target_uid} 数据不存在。")
        self._update_state(user_id, menu='admin', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    @filter.regex(r'^\d+$')
    async def handle_admin_bind_user(self, event: AstrMessageEvent):
        if getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_bind_user':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        target_uid = text
        self._update_state(user_id, step='admin_bind_account', tmp_data={'target_uid': target_uid})
        self._schedule_timeout(user_id)
        yield event.plain_result(f"目标用户 {target_uid}，请输入要绑定的手机号#密码（可多个用 & 分隔），输入 0 取消：")

    @filter.regex(r'^(0|\d{11}#.+)$')
    async def handle_admin_bind_account(self, event: AstrMessageEvent):
        if getattr(event, '_admin_sub_processed', False) or getattr(event, '_admin_choice_processed', False):
            return
        user_id = event.get_sender_id()
        state = self._get_state(user_id)
        if state.get('step') != 'admin_bind_account':
            return

        text = event.message_str.strip()
        if text == "0":
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        tmp = state.get('tmp_data', {})
        target_uid = tmp.get('target_uid')
        if not target_uid:
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 会话错误，请重新操作。")
            self._update_state(user_id, menu='admin', step=None)
            self._schedule_timeout(user_id)
            yield event.plain_result(self._admin_menu())
            return

        parts = text.split('&')
        user_data = await self._load_data(target_uid)
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
            self._schedule_timeout(user_id)
            yield event.plain_result("❌ 绑定失败：\n" + "\n".join(errors) + "\n请重新输入")
            return

        if new_accounts:
            user_data["accounts"].extend(new_accounts)
            await self._save_data(target_uid, user_data)
            self._schedule_timeout(user_id)
            yield event.plain_result(f"✅ 成功为 {target_uid} 绑定 {len(new_accounts)} 个账号，当前共 {len(user_data['accounts'])} 个账号")
        else:
            self._schedule_timeout(user_id)
            yield event.plain_result("✅ 账号信息已更新（无新增）")

        self._update_state(user_id, menu='admin', step=None)
        self._schedule_timeout(user_id)
        yield event.plain_result(self._admin_menu())

    # ---------- 生命周期 ----------
    async def initialize(self):
        logger.info("✅ 酷我插件 2.10.3 统一管理面板列表显示版已加载")
        self.scheduler_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ 定时调度器已启动（每秒检查）")

    async def terminate(self):
        logger.info("✅ 酷我插件已卸载")
        self.scheduler_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ 定时调度器已停止")
