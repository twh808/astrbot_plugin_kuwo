#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酷我音乐管理插件 - AstrBot 交互式菜单
版本: 2.0.0
整合自: 酷我提现.py (v2.6.3) + 酷我提现验证码.py (v1.0.3)
实现功能:
- 账号绑定（支持手机号#密码#授权次数）
- 获取验证码（定时/立即）
- 提交验证码
- 提现（自动/立即），授权次数控制，今日提现状态检查
- 交互超时（120秒）
- 详细的提现结果反馈
"""

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

# ========================== 加密常量与函数（来自原脚本） ==========================
SIGN_BASE = 'https://integralapi.kuwo.cn/api/v1/online/sign'
URL_NEW_USER_SIGN_LIST = SIGN_BASE + '/v1/earningSignIn/newUserSignList'
URL_USER_ASSET = SIGN_BASE + '/v1/earningSignIn/earningUserSignList'
URL_NEW_DO_LISTEN = SIGN_BASE + '/v1/earningSignIn/newDoListen'
URL_EVERYDAY_DO_LISTEN = SIGN_BASE + '/v1/earningSignIn/everydaymusic/doListen'
URL_BOX_RENEW = SIGN_BASE + '/new/boxRenew'
URL_NEW_BOX_LIST = SIGN_BASE + '/new/newBoxList'
URL_NEW_BOX_FINISH = SIGN_BASE + '/new/newBoxFinish'
FREEMIUM_SWITCH_URL = 'https://wapi.kuwo.cn/openapi/v1/user/freemium/h5/switches'

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
    result = combined_string[:8]
    return result

def encrypt_devid(dev_id):
    padded_id = dev_id.ljust(16, '0')[:16]
    return base64.b64encode(padded_id.encode()).decode()

def get_q(username, password):
    dev_id = ''.join([random.choice(string.digits) for _ in range(10)])
    dev_name = '安卓设备'
    devType = 'arr'
    data = f"username={username}&password={base64.b64encode(password.encode()).decode()}&dev_id={dev_id}&user={str(uuid.uuid4()).replace('-', '')}&dev_name={dev_name}&urlencode=0&src=kwplayer_ar11.1.4.1_40.apk&devResolution=720*1080&&from=android&devType={devType}&sx={create_sx()}&version=11.1.4.1"
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

def decrypt_phone(encrypted_phone):
    key = b'ysiVkLJHHnvMWCHq'
    iv = b'ichYooX+Mb1gRetP'
    aes = AES.new(key=key, mode=AES.MODE_CBC, iv=iv)
    encrypted_data = base64.b64decode(encrypted_phone)
    decrypted_data = unpad(aes.decrypt(encrypted_data), AES.block_size, style='pkcs7')
    return decrypted_data.decode('UTF-8')

# ========================== 酷我 API 封装 ==========================
class KuwoAPI:
    @staticmethod
    def login(phone: str, password: str) -> Optional[Tuple[str, str, str, str]]:
        """登录，返回 (loginUid, loginSid, appUid, encrypted_dev_id) 或 None"""
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
            logger.error(f"登录失败 {phone}: {e}")
            return None

    @staticmethod
    def send_code(loginUid: str, loginSid: str, appUid: str, encrypted_phone: str, quota_id: str) -> Tuple[bool, str]:
        """发送验证码，返回 (成功标志, 消息)"""
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
            data = resp.json()
            msg = data.get('msg', '')
            desc = data.get('data', {}).get('description', '')
            combined = f"{msg}|{desc}"
            success = '发送成功' in combined or 'success' in combined.lower()
            return success, combined
        except Exception as e:
            return False, f"异常: {e}"

    @staticmethod
    def withdraw_confirm(loginUid: str, loginSid: str, appUid: str, encrypted_phone: str,
                         code: str, kwtxid: str, verification_id: str, q36: str) -> Tuple[bool, str]:
        """执行提现，返回 (成功标志, 消息)"""
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
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5, verify=False)
            data = resp.json() if resp.status_code == 200 else {}
            msg = data.get('msg', '')
            text = data.get('data', {}).get('text', '')
            desc = data.get('data', {}).get('description', '')
            combined = f"{msg}|{text}|{desc}"
            success = "提现申请发起成功" in combined
            return success, combined
        except Exception as e:
            return False, f"异常: {e}"

    @staticmethod
    def check_withdraw_today(loginUid: str, loginSid: str) -> bool:
        """查询今日是否已有成功提现记录"""
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

# ========================== AstrBot 插件主类 ==========================
@register("astrbot_plugin_kuwo", "YourName", "酷我音乐管理插件", "2.0.0",
          "https://github.com/YourName/astrbot_plugin_kuwo")
class KuwoPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        # 默认配置
        self.default_auth_limit = self.config.get('default_auth_limit', 3)
        self.verification_cron = self.config.get('verification_cron', "55 8,12,16,19 * * *")
        self.withdraw_cron = self.config.get('withdraw_cron', "59 8,12,16,19 * * *")
        self.verification_id = self.config.get('verification_id', "BVB5cctRxT%252FifPHwGzM9q2c%252BG53szUY8iDipOhkIAb%252FmSy64bK1Od%252FTftF%252F1NrBdTYm7hqnmCc3go8IWpPs80nQ%253D%253D")
        self.q36 = self.config.get('q36', "a9441d902f38da7d2d25bf1f10001a319907")
        self.kwtxid = self.config.get('kwtxid', "30002")

        # 用户状态管理
        self.user_menu_state = {}      # 当前菜单: 'main', 'get_code', 'withdraw'
        self.user_last_active = {}     # 最后活动时间戳
        self.user_waiting_input = {}   # 等待输入类型: 'binding', 'submitting_code'
        self.user_temp_data = {}       # 临时数据, 如绑定中的临时账号列表

        # 数据持久化 (KV存储)
        self.data = {}                 # 将在加载时从KV读取

        # 定时任务ID
        self.cron_job_ids = []

    async def _load_data(self):
        """从KV存储加载数据"""
        self.data = await self.get_kv_data("kuwo_data", {})
        # 初始化默认结构
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
        """保存数据到KV存储"""
        await self.put_kv_data("kuwo_data", self.data)

    def _get_user_data(self, user_id: str) -> dict:
        """获取用户数据，若不存在则创建"""
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
        """唤起主菜单"""
        user_id = event.get_sender_id()
        self.user_menu_state[user_id] = 'main'
        self.user_last_active[user_id] = time.time()
        await self._load_data()  # 加载数据
        yield event.plain_result(self._main_menu())

    @filter.command("酷我")
    async def kuwo_handler(self, event: AstrMessageEvent):
        """处理所有菜单输入"""
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
            return  # 不在菜单中，忽略

        text = event.message_str.strip()
        state = self.user_menu_state.get(user_id)

        # 处理等待输入（绑定账号或提交验证码）
        if self.user_waiting_input.get(user_id):
            await self._handle_waiting_input(user_id, text, event)
            return

        if state == 'main':
            await self._handle_main_menu(user_id, text, event)
        elif state == 'get_code':
            await self._handle_get_code_menu(user_id, text, event)
        elif state == 'withdraw':
            await self._handle_withdraw_menu(user_id, text, event)

    # ==================== 菜单处理函数 ====================
    async def _handle_main_menu(self, user_id: str, text: str, event: AstrMessageEvent):
        if text == "0":
            self.user_menu_state.pop(user_id, None)
            yield event.plain_result("👋 已退出菜单")
            return
        elif text == "1":
            yield event.plain_result("📱 请输入要绑定的账号，格式：手机号#密码 或 手机号#密码#授权次数（可选），多个账号请用 & 分隔")
            self.user_waiting_input[user_id] = 'binding'
            return
        elif text == "2":
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                user_data["accounts"] = []
                await self._save_data()
                yield event.plain_result("✅ 已解绑所有账号")
            else:
                yield event.plain_result("❌ 您还没有绑定任何账号")
            return
        elif text == "3":
            user_data = self._get_user_data(user_id)
            if user_data["accounts"]:
                lines = [f"📱 {acc['phone']}" for acc in user_data["accounts"]]
                auth_limit = user_data["auth_limit"]
                lines.append(f"📊 总授权次数：{auth_limit}")
                yield event.plain_result("📋 您绑定的账号：\n" + "\n".join(lines))
            else:
                yield event.plain_result("❌ 您还没有绑定任何账号")
            return
        elif text == "4":
            self.user_menu_state[user_id] = 'get_code'
            yield event.plain_result(self._get_code_menu())
            return
        elif text == "5":
            yield event.plain_result("🔢 请输入6位验证码（从手机短信获取）")
            self.user_waiting_input[user_id] = 'submitting_code'
            return
        elif text == "6":
            self.user_menu_state[user_id] = 'withdraw'
            yield event.plain_result(self._withdraw_menu())
            return
        elif text == "8":
            yield event.plain_result(self._help_text())
        else:
            yield event.plain_result("❌ 无效选项，请回复数字\n" + self._main_menu())

    async def _handle_get_code_menu(self, user_id: str, text: str, event: AstrMessageEvent):
        if text == "0":
            self.user_menu_state[user_id] = 'main'
            yield event.plain_result(self._main_menu())
            return
        elif text == "1":
            # 定时获取：只是提示，实际由cron触发
            yield event.plain_result("⏳ 定时获取已配置，将在 cron 时间自动执行。如需立即获取请选择 2。")
            return
        elif text == "2":
            # 立即获取验证码
            user_data = self._get_user_data(user_id)
            accounts = user_data["accounts"]
            if not accounts:
                yield event.plain_result("❌ 请先绑定账号")
                return
            # 检查当前时间是否在23-24点，若不在则过滤今日已提现的账户
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            daily = user_data.get("daily_withdraw", {}).get(today, {})
            if now.hour == 23:
                accounts_to_send = accounts  # 23-24点不受限
            else:
                accounts_to_send = [acc for acc in accounts if not daily.get(acc["phone"], False)]
            if not accounts_to_send:
                yield event.plain_result("ℹ️ 所有账户今日已提现，无需获取验证码")
                return

            # 并发获取验证码
            results = await self._send_codes_batch(user_id, accounts_to_send)
            msg = "📨 验证码发送结果：\n"
            for phone, success, info in results:
                msg += f"{'✅' if success else '❌'} {phone}: {info}\n"
            yield event.plain_result(msg)
            return
        else:
            yield event.plain_result("❌ 无效选项\n" + self._get_code_menu())

    async def _handle_withdraw_menu(self, user_id: str, text: str, event: AstrMessageEvent):
        if text == "0":
            self.user_menu_state[user_id] = 'main'
            yield event.plain_result(self._main_menu())
            return
        elif text == "1":
            # 自动提现：提示等待cron
            yield event.plain_result("⏳ 自动提现已配置，将在 cron 时间自动执行。如需立即提现请选择 2。")
            return
        elif text == "2":
            # 立即提现
            user_data = self._get_user_data(user_id)
            accounts = user_data["accounts"]
            if not accounts:
                yield event.plain_result("❌ 请先绑定账号")
                return
            auth_limit = user_data["auth_limit"]
            # 按顺序取前 auth_limit 个账户（如果 auth_limit 为0表示不限）
            if auth_limit > 0 and len(accounts) > auth_limit:
                accounts_to_withdraw = accounts[:auth_limit]
            else:
                accounts_to_withdraw = accounts

            # 检查每个账户今日是否已提现，已提现的跳过
            results = await self._withdraw_batch(user_id, accounts_to_withdraw)
            # 统计
            success_count = sum(1 for r in results if r[1])
            fail_count = len(results) - success_count
            remaining = auth_limit - success_count if auth_limit > 0 else "不限"
            msg = f"📊 【立即提现完成】\n✅ 成功: {success_count} | ❌ 失败: {fail_count} | ⏭️ 跳过: 0\n📈 剩余可用次数: {remaining}\n━━━━━━━━━━━━━━━━━━\n"
            for phone, success, detail in results:
                status = "✅ 提现成功" if success else "❌ 提现失败"
                msg += f"{status} - {phone}：{detail}\n"
            yield event.plain_result(msg)
            return
        else:
            yield event.plain_result("❌ 无效选项\n" + self._withdraw_menu())

    # ==================== 等待输入处理 ====================
    async def _handle_waiting_input(self, user_id: str, text: str, event: AstrMessageEvent):
        wait_type = self.user_waiting_input.get(user_id)
        if wait_type == 'binding':
            # 解析账号：支持 手机号#密码 或 手机号#密码#授权次数，多个用 & 分隔
            parts = text.split('&')
            new_accounts = []
            error_msgs = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # 解析
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
                yield event.plain_result("绑定失败：\n" + "\n".join(error_msgs) + "\n请重新发送“酷我”进入菜单重试。")
                self.user_waiting_input.pop(user_id, None)
                return
            if not new_accounts:
                yield event.plain_result("未解析到有效账号，请重新输入")
                return
            # 保存账号
            user_data = self._get_user_data(user_id)
            # 如果是用户第一次绑定，设置授权次数为第一个账号指定的limit，否则使用已有auth_limit
            if user_data["accounts"]:
                # 已有账号，保留原auth_limit，但可更新每个账号的个性化limit? 我们使用统一auth_limit
                # 但用户可以为每个账号指定不同的limit吗？需求是授权次数绑定QQ号，名下所有账户共用，所以只用一个总次数。
                # 如果用户输入了limit，我们取第一个非空的作为总授权次数。
                for acc in new_accounts:
                    if acc.get("limit") is not None:
                        user_data["auth_limit"] = acc["limit"]
                        break
                # 合并账号（去重）
                existing_phones = {acc["phone"] for acc in user_data["accounts"]}
                for acc in new_accounts:
                    if acc["phone"] not in existing_phones:
                        user_data["accounts"].append({"phone": acc["phone"], "password": acc["password"]})
                        existing_phones.add(acc["phone"])
            else:
                # 首次绑定
                for acc in new_accounts:
                    if acc.get("limit") is not None:
                        user_data["auth_limit"] = acc["limit"]
                        break
                user_data["accounts"] = [{"phone": acc["phone"], "password": acc["password"]} for acc in new_accounts]
            await self._save_data()
            self.user_waiting_input.pop(user_id, None)
            yield event.plain_result(f"✅ 绑定成功，共 {len(user_data['accounts'])} 个账号，总授权次数 {user_data['auth_limit']}\n" + self._main_menu())
        elif wait_type == 'submitting_code':
            # 提交验证码
            code = text.strip()
            if not code.isdigit() or len(code) != 6:
                yield event.plain_result("❌ 验证码格式错误，请输入6位数字")
                return
            # 缓存验证码到所有账户（或用户指定的账户？这里简单点，缓存到用户下，提现时使用）
            user_data = self._get_user_data(user_id)
            # 为每个账号缓存验证码（可指定账号，但我们只存一个验证码，取第一个账号）
            if user_data["accounts"]:
                # 为所有账号设置同样的验证码（简化）
                for acc in user_data["accounts"]:
                    user_data["verification_codes"][acc["phone"]] = {"code": code, "expire": time.time() + 300}  # 5分钟有效
                await self._save_data()
                yield event.plain_result(f"✅ 验证码 {code} 已缓存，有效5分钟。\n" + self._main_menu())
            else:
                yield event.plain_result("❌ 您还没有绑定账号，请先绑定")
            self.user_waiting_input.pop(user_id, None)

    # ==================== 核心业务函数 ====================
    async def _send_codes_batch(self, user_id: str, accounts: List[dict]) -> List[Tuple[str, bool, str]]:
        """并发发送验证码，返回 [(phone, success, info)]"""
        results = []
        # 登录每个账号
        login_infos = []
        for acc in accounts:
            login_result = await asyncio.to_thread(KuwoAPI.login, acc["phone"], acc["password"])
            if login_result:
                loginUid, loginSid, appUid, encrypted_dev_id = login_result
                login_infos.append((acc["phone"], loginUid, loginSid, appUid, encrypted_dev_id))
            else:
                results.append((acc["phone"], False, "登录失败"))
        # 发送验证码
        for phone, loginUid, loginSid, appUid, _ in login_infos:
            encrypted_phone = encrypt_phone(phone)
            success, info = await asyncio.to_thread(KuwoAPI.send_code, loginUid, loginSid, appUid, encrypted_phone, self.kwtxid)
            results.append((phone, success, info))
        return results

    async def _withdraw_batch(self, user_id: str, accounts: List[dict]) -> List[Tuple[str, bool, str]]:
        """并发提现，返回 [(phone, success, detail)]"""
        results = []
        # 获取缓存的验证码
        user_data = self._get_user_data(user_id)
        codes = user_data.get("verification_codes", {})
        # 登录并提现
        for acc in accounts:
            phone = acc["phone"]
            # 检查今日是否已提现
            login_result = await asyncio.to_thread(KuwoAPI.login, phone, acc["password"])
            if not login_result:
                results.append((phone, False, "登录失败"))
                continue
            loginUid, loginSid, appUid, _ = login_result
            # 检查今日提现
            if await asyncio.to_thread(KuwoAPI.check_withdraw_today, loginUid, loginSid):
                results.append((phone, False, "今日已提现，跳过"))
                continue
            # 获取验证码
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
                # 更新每日提现记录
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in user_data["daily_withdraw"]:
                    user_data["daily_withdraw"][today] = {}
                user_data["daily_withdraw"][today][phone] = True
                await self._save_data()
        return results

    # ==================== 定时任务 ====================
    async def _setup_cron(self):
        """注册定时任务"""
        await asyncio.sleep(3)  # 等待插件完全加载
        scheduler = getattr(self.context, 'scheduler', None)
        if scheduler is None:
            logger.warning("当前环境不支持调度器，定时任务不可用")
            return
        # 解析cron
        try:
            # 定时获取验证码
            job1 = scheduler.add_job(
                self._auto_get_verification_codes,
                'cron',
                id='kuwo_auto_get_code',
                **self._parse_cron(self.verification_cron)
            )
            self.cron_job_ids.append(job1.id)
            # 自动提现
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
        """定时任务：为所有已绑定账号发送验证码（跳过今日已提现的，23点后不限）"""
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
                # 异步执行，不阻塞
                asyncio.create_task(self._send_codes_batch(user_id, accounts_to_send))

    async def _auto_withdraw(self):
        """自动提现定时任务"""
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
        """插件初始化时调用"""
        await self._load_data()
        asyncio.create_task(self._setup_cron())

    async def terminate(self):
        """插件卸载时清理"""
        # 移除定时任务
        scheduler = getattr(self.context, 'scheduler', None)
        if scheduler:
            for job_id in self.cron_job_ids:
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
        logger.info("酷我插件已卸载")
        
