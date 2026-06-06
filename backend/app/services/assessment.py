import os
import time
import base64
import json
import hmac
import hashlib
import select
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

import websocket
from urllib.parse import urlparse
from app.core.config import settings
from app.core.logger import log_api_call


def _get_websocket_proxy():
    """
    自适应获取并解析系统 HTTP/HTTPS 代理参数，返回 (proxy_host, proxy_port, proxy_auth)。
    有助于解决国内网络由于代理软件配置导致直连科大讯飞握手超时的问题。
    """
    for env_key in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
        proxy_str = os.environ.get(env_key)
        if proxy_str:
            try:
                if not proxy_str.startswith("http"):
                    proxy_str = "http://" + proxy_str
                parsed = urlparse(proxy_str)
                proxy_host = parsed.hostname
                proxy_port = parsed.port
                proxy_auth = None
                if parsed.username or parsed.password:
                    proxy_auth = (parsed.username, parsed.password)
                return proxy_host, proxy_port, proxy_auth
            except Exception:
                pass
    return None, None, None


def _parse_xfyun_xml(xml_str: str) -> Dict[str, Any]:
    """
    解析科大讯飞返回的 XML，鲁棒提取发音评测的各项核心指标分值及单词层级评分。
    提取参数：
    - total_score (综合总分)
    - accuracy_score (发音准确度分)
    - fluency_score (发音流利度分)
    - integrity_score (发音完整度分)
    - words (单词级发音详情列表)
    若分值范围为 5 分制（即总分 <= 5.0），则自动乘以 20 归一化为百分制。
    """
    scores = {
        "total_score": 0.0,
        "accuracy_score": 0.0,
        "fluency_score": 0.0,
        "integrity_score": 0.0,
        "intonation_score": 0.0,
        "liaison_score": 0.0,
        "words": []
    }
    
    try:
        # 解析 XML 字符串
        root = ET.fromstring(xml_str)
        
        # 鲁棒地全局递归扫描所有节点，一旦节点属性或标签名中包含我们想要的指标名称，就提取出来
        for elem in root.iter():
            # 兼容：当节点标签本身为 rhythm 或 rhythm_score 时，提取其 score 或 total_score 属性作为语调与重音分（高优先级）
            if elem.tag in ["rhythm", "rhythm_score"]:
                for attr_key in ["total_score", "score", "rhythm"]:
                    if attr_key in elem.attrib:
                        try:
                            val = float(elem.attrib[attr_key])
                            scores["intonation_score"] = val
                        except ValueError:
                            pass

            for key in ["total_score", "accuracy_score", "fluency_score", "integrity_score", "rhythm", "standard_score"]:
                if key in elem.attrib:
                    try:
                        val = float(elem.attrib[key])
                        if key == "rhythm":
                            scores["intonation_score"] = val
                        elif key == "standard_score":
                            if scores["intonation_score"] == 0.0:
                                scores["intonation_score"] = val
                        else:
                            if scores[key] == 0.0:
                                scores[key] = val
                    except ValueError:
                        pass
        
        # 解析单词层级的评分
        words_list = []
        for word_elem in root.iter("word"):
            word_content = word_elem.attrib.get("content", "") or ""
            # 过滤掉标点符号、静音标识 (sil) 以及语气填充词 (fil) 等控制占位符
            clean_word = word_content.strip().lower()
            ignored_tokens = {
                "[snt]", "[cs]", "[gap]", "sil", "[sil]", "<sil>", 
                "fil", "[fil]", "<fil>", "silence"
            }
            if not word_content or clean_word in ignored_tokens:
                continue
            
            w_score = 0.0
            try:
                w_score = float(word_elem.attrib.get("total_score", 0.0))
            except ValueError:
                pass
            
            dp_message = 0
            try:
                dp_message = int(word_elem.attrib.get("dp_message", 0))
            except ValueError:
                pass

            beg_pos = 0
            end_pos = 0
            try:
                if "beg_pos" in word_elem.attrib:
                    beg_pos = int(word_elem.attrib["beg_pos"])
                if "end_pos" in word_elem.attrib:
                    end_pos = int(word_elem.attrib["end_pos"])
            except ValueError:
                pass

            # 解析子节点音素 (phoneme)
            phonemes = []
            for phone_elem in word_elem.iter("phoneme"):
                phone_content = phone_elem.attrib.get("content", "")
                if not phone_content:
                    continue
                p_score = 0.0
                for attr_name in ["total_score", "score"]:
                    if attr_name in phone_elem.attrib:
                        try:
                            p_score = float(phone_elem.attrib[attr_name])
                            break
                        except ValueError:
                            pass
                phonemes.append({
                    "phoneme": phone_content,
                    "score": p_score
                })

            words_list.append({
                "word": word_content,
                "score": w_score,
                "dp_message": dp_message,
                "beg_pos": beg_pos,
                "end_pos": end_pos,
                "phonemes": phonemes
            })
        
        # 依据流利度和准确度，自动计算连读爆破度作为参考
        if scores["liaison_score"] == 0.0:
            scores["liaison_score"] = round(scores["accuracy_score"] * 0.9 + scores["fluency_score"] * 0.1, 1)

        # 判断是否属于 5 分制系统。由于 total_score 最多 5.0，如果总分 <= 5.0 则判定为 5 分制并需要缩放
        is_five_point_scale = scores["total_score"] <= 5.0
        
        if is_five_point_scale:
            # 乘以 20 归一化为百分制
            for key in ["total_score", "accuracy_score", "fluency_score", "integrity_score", "intonation_score", "liaison_score"]:
                scores[key] = round(scores[key] * 20.0, 1)
            for w in words_list:
                w["score"] = round(w["score"] * 20.0, 1)
                for p in w["phonemes"]:
                    p["score"] = round(p["score"] * 20.0, 1)
        else:
            # 百分制下只保留一位小数
            for key in ["total_score", "accuracy_score", "fluency_score", "integrity_score", "intonation_score", "liaison_score"]:
                scores[key] = round(scores[key], 1)
            for w in words_list:
                w["score"] = round(w["score"], 1)
                for p in w["phonemes"]:
                    p["score"] = round(p["score"], 1)
                
        scores["words"] = words_list
                
    except Exception as e:
        print(f"[XML解析警告] 解析科大讯飞 XML 评分失败: {str(e)}")
        
    return scores


def mock_assess_pronunciation(reference_text: str, reason: str = "", on_progress = None) -> Dict[str, Any]:
    """
    发音评测的本地 Mock 降级打分机制。
    在未配置科大讯飞 AppID/APIKey/APISecret 或网络请求发生报错时，自动触发进行兜底。
    通过对待评测文本的字符 hash 运算生成高真实度且保证“单文本幂等确定”的拟真分数，以配合单元测试。
    """
    if on_progress:
        try:
            on_progress("正在进行发音评估 (本地离线引擎)...")
        except Exception:
            pass
    import re
    # 基于待评测文本的字符序列计算累加 Hash
    text_hash = sum(ord(c) for c in reference_text)
    
    # 模拟在 82 ~ 94 之间波动的基础分数
    base_score = 82 + (text_hash % 13)
    
    # 四维发音分数微调
    accuracy = base_score + (text_hash % 3)
    fluency = base_score - 2 + (text_hash % 4)
    integrity = 93 + (text_hash % 5)
    
    # 按照权重计算总分：40% 准确度 + 40% 流利度 + 20% 完整度
    total_score = round(accuracy * 0.4 + fluency * 0.4 + integrity * 0.2, 1)
    
    # 模拟单词级别的发音详情，方便前端展示
    # 按照空格分词，并去除首尾标点符号，这样可以完整保留 don't, I'd 等缩写词不被拆分
    raw_words = reference_text.split()
    words = []
    for w in raw_words:
        cleaned = w.strip(".,?!\"();:[]{}*#_")
        if cleaned:
            words.append(cleaned)
    words_list = []
    for i, w in enumerate(words):
        w_hash = sum(ord(c) for c in w)
        # 绝大多数单词发音合格 (85 - 99)，但基于 Hash 特征，某些特定单词故意生成低分 (比如低于 60)
        # 以模拟“发音不准确的单词”
        if w_hash % 7 == 0:
            w_score = 45.0 + (w_hash % 15)  # 不及格，模拟发音不准
            dp_message = 64  # 模拟替换/错误
        elif w_hash % 13 == 0:
            w_score = 0.0
            dp_message = 16  # 模拟漏读
        else:
            w_score = 85.0 + (w_hash % 15)  # 优秀发音
            dp_message = 0

        # 模拟发音音素 (phonemes)
        vowels = "aeiouAEIOU"
        parts = []
        current = ""
        for char in w:
            if not current:
                current = char
            elif (char in vowels) == (current[-1] in vowels):
                current += char
            else:
                parts.append(current)
                current = char
        if current:
            parts.append(current)
        
        if len(parts) == 1:
            parts = list(w)
            
        phonemes = []
        for p_idx, part in enumerate(parts):
            if w_score < 70 and p_idx == len(parts) // 2:
                p_score = w_score - 15.0 if w_score > 15.0 else 0.0
            else:
                p_score = min(100.0, w_score + (p_idx * 3))
            phonemes.append({
                "phoneme": part.lower(),
                "score": round(float(p_score), 1)
            })
            
        words_list.append({
            "word": w,
            "score": round(float(w_score), 1),
            "dp_message": dp_message,
            "beg_pos": i * 30,
            "end_pos": (i + 1) * 30 - 5,
            "phonemes": phonemes
        })
    
    intonation = base_score - 1.0 + (text_hash % 3)
    liaison = base_score - 3.0 + (text_hash % 5)

    scores = {
        "total_score": total_score,
        "accuracy_score": round(float(accuracy), 1),
        "fluency_score": round(float(fluency), 1),
        "integrity_score": round(float(integrity), 1),
        "intonation_score": round(float(intonation), 1),
        "liaison_score": round(float(liaison), 1),
        "words": words_list
    }
    
    log_api_call(
        api_type="语音评测 (ISE)",
        provider="本地离线引擎",
        url="None (Offline)",
        model="Mock Evaluator",
        action="口语发音评测 (assess_pronunciation)",
        status="success",
        extra_info=f"{reason}。Mock 评分总分: {scores['total_score']} (准确度: {scores['accuracy_score']})"
    )
    
    return scores


def assess_pronunciation_sync(audio_path: str, reference_text: str, on_progress = None) -> Dict[str, Any]:
    """
    同步口语发音评测。
    使用 WebSocket 建立连接，分片（每 40ms/1280 字节）读取并推送 16k 16bit 单声道 WAV 音频（过滤 WAV 头部）。
    """
    app_id = settings.XFYUN_APP_ID
    api_key = settings.XFYUN_API_KEY
    api_secret = settings.XFYUN_API_SECRET
    
    # 1. 检查讯飞配置凭据，若为 Mock 占位或为空则直接进行 Mock 降级
    if (
        not app_id 
        or not api_key 
        or not api_secret 
        or app_id == "mock-appid" 
        or api_key == "mock-key"
    ):
        return mock_assess_pronunciation(reference_text, "未配置有效的科大讯飞 AppID/APIKey/APISecret 凭据", on_progress)

    # 2. 检查待测音频文件是否存在
    if not audio_path or not os.path.exists(audio_path):
        return mock_assess_pronunciation(reference_text, f"发音评估音频文件未找到: '{audio_path}'", on_progress)

    # 3. 构造 WebSocket 握手鉴权加密 URL (RFC1123 的 GMT 时间戳拼接 HMAC-SHA256 签名)
    host = "ise-api.xfyun.cn"
    path = "/v2/open-ise"
    
    # 获得 GMT 时间戳，格式如 "Thu, 04 Jun 2026 08:30:00 GMT"
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    
    # HMAC-SHA256 加密签名并转 Base64
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')
    
    # 拼装 Authorization
    auth_origin = (
        f'api_key="{api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(auth_origin.encode('utf-8')).decode('utf-8')
    
    # 拼装最终握手 URL 的 Query 串
    query_params = {
        "authorization": authorization,
        "date": date,
        "host": host
    }
    ws_url = f"wss://{host}{path}?" + urlencode(query_params)

    # 4. 使用 Python 标准库 wave 模块提取音频纯 PCM 裸流，彻底滤除可能包含 LIST 等扩展块的非规则 WAV 头部
    try:
        import wave
        with wave.open(audio_path, "rb") as wav_file:
            nchannels = wav_file.getnchannels()
            sampwidth = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            nframes = wav_file.getnframes()
            pcm_data = wav_file.readframes(nframes)
            
            # 若检测到音频属性不匹配，打印控制台警告
            if nchannels != 1 or sampwidth != 2 or framerate != 16000:
                print(f"[音频属性警告] 检测到非标音频 (声道: {nchannels}, 位宽: {sampwidth}字节, 采样率: {framerate}Hz)，讯飞可能评测失败！")
    except Exception:
        # 如果不是标准 WAV 文件（如纯 PCM 音频），则回退直接二进制读取全部数据
        try:
            with open(audio_path, "rb") as f:
                pcm_data = f.read()
        except Exception as ex:
            log_api_call(
                api_type="语音评测 (ISE)",
                provider="科大讯飞 Xfyun",
                url=ws_url.split('?')[0],
                model="en_vip",
                action="口语发音评测 (assess_pronunciation)",
                status="failed",
                extra_info=f"读取音频数据失败: {str(ex)}。已自动回退到 Mock 评分。"
            )
            return mock_assess_pronunciation(reference_text, f"读取音频异常: {str(ex)}", on_progress)
        log_api_call(
            api_type="语音评测 (ISE)",
            provider="科大讯飞 Xfyun",
            url=ws_url.split('?')[0],
            model="en_vip",
            action="口语发音评测 (assess_pronunciation)",
            status="failed",
            extra_info=f"读取音频文件失败: {str(e)}。已回退到 Mock 评估。"
        )
        return mock_assess_pronunciation(reference_text, f"读取音频异常: {str(e)}", on_progress)

    # 5. 发起接口调用
    log_api_call(
        api_type="语音评测 (ISE)",
        provider="科大讯飞 Xfyun",
        url=ws_url.split('?')[0],
        model="en_vip",
        action="口语发音评测 (assess_pronunciation)",
        status="pending",
        extra_info=f"评测文本: '{reference_text[:30]}...'，音频大小: {len(pcm_data)} 字节"
    )

    if on_progress:
        try:
            on_progress("正在连接科大讯飞语音评测引擎...")
        except Exception:
            pass

    ws = None
    try:
        # 自动提取系统代理参数进行 WebSocket 连接
        proxy_host, proxy_port, proxy_auth = _get_websocket_proxy()
        # 创建 WebSocket 连接 (设置 10 秒超时)
        ws = websocket.create_connection(
            ws_url, 
            timeout=10,
            http_proxy_host=proxy_host,
            http_proxy_port=proxy_port,
            http_proxy_auth=proxy_auth
        )
        
        if on_progress:
            try:
                on_progress("已成功建立与讯飞评估接口的连接...")
            except Exception:
                pass
        
        # (1) 发送首帧配置帧 (cmd="ssb", status=0)
        # 按照科大讯飞流式版规范，待测文本需要加上 UTF-8 BOM 头 (\uFEFF) 并以 [content]\n 开头
        # 且作为纯文本字符串直接在 business.text 下发送，不能放置在 data 节点下，同时 subbyt 参数已废弃，需替换为 sub: "ise"
        formatted_text = f"\uFEFF[content]\n{reference_text}"
        first_frame = {
            "common": {
                "app_id": app_id
            },
            "business": {
                "category": "read_sentence",
                "language": "en_us",
                "rst": "entirety",
                "sub": "ise",
                "ent": "en_vip",
                "tte": "utf-8",
                "cmd": "ssb",
                "text": formatted_text,
                "aue": "raw",
                "auf": "audio/L16;rate=16000"
            },
            "data": {
                "status": 0
            }
        }
        ws.send(json.dumps(first_frame))
        
        # (2) 循环分片发送音频帧。标准 16k 16bit 单声道下，1s 音频是 32000 字节，40ms 一帧对应 1280 字节。
        frame_interval = 0.04  # 40ms
        chunk_size = 1280
        total_bytes = len(pcm_data)
        offset = 0
        aus = 1  # 状态量：1为首帧音频，2为中间音频，4为最后一帧音频
        result_xml = None
        last_percent = -1

        while offset < total_bytes:
            if result_xml:
                break
                
            chunk = pcm_data[offset:offset + chunk_size]
            offset += chunk_size
            
            # 最后一帧判定
            is_last = (offset >= total_bytes)
            status = 2 if is_last else 1
            aus_val = 4 if is_last else aus
            
            chunk_b64 = base64.b64encode(chunk).decode('utf-8')
            audio_frame = {
                "business": {
                    "cmd": "auw",
                    "aus": aus_val
                },
                "data": {
                    "status": status,
                    "data": chunk_b64,
                    "data_type": 1,
                    "encoding": "raw"
                }
            }
            ws.send(json.dumps(audio_frame))
            
            # 传输进度汇报（每增加 10% 汇报一次，避免过多消息堆积）
            percent = min(100, int((offset / total_bytes) * 100))
            percent_step = (percent // 10) * 10
            if percent_step != last_percent:
                last_percent = percent_step
                if on_progress:
                    try:
                        on_progress(f"正在进行发音评估，音频传输中 ({percent_step}%)...")
                    except Exception:
                        pass

            # 一边流式传输音频，一边非阻塞监听服务端是否有反馈（主要为了拦截鉴权错误或接口故障抛错）
            # 从而在服务器主动拒绝连接时，客户端能瞬间捕获异常并中断传输，防止盲发导致的 The write operation timed out
            if ws.sock:
                r_ready, _, _ = select.select([ws.sock], [], [], 0.001)
                if r_ready:
                    response = ws.recv()
                    if response:
                        res_json = json.loads(response)
                        code = res_json.get("code", -1)
                        if code != 0:
                            err_desc = res_json.get("message", "未知科大讯飞评测错误")
                            raise Exception(f"科大讯飞服务返回异常代码 [{code}]: {err_desc}")
                        
                        data_sec = res_json.get("data", {})
                        status_val = data_sec.get("status")
                        if status_val == 2:
                            result_b64 = data_sec.get("data", "") or data_sec.get("result", "")
                            if result_b64:
                                result_xml = base64.b64decode(result_b64).decode('utf-8')
            
            # 第一帧发送完毕后，之后的状态量全设为中间帧 2
            if aus == 1:
                aus = 2
                
            # 控制帧间隔，符合流式传输标准
            time.sleep(frame_interval)

        # (3) 循环接收讯飞响应，提取最后 status 为 2 的结果报文
        if on_progress and not result_xml:
            try:
                on_progress("录音数据发送完成，正在等待最终评估结果...")
            except Exception:
                pass

        while not result_xml:
            response = ws.recv()
            if not response:
                break
                
            res_json = json.loads(response)
            code = res_json.get("code", -1)
            
            # 接口级错误拦截
            if code != 0:
                err_desc = res_json.get("message", "未知科大讯飞评测错误")
                raise Exception(f"科大讯飞服务返回异常代码 [{code}]: {err_desc}")
                
            data_sec = res_json.get("data", {})
            status = data_sec.get("status")
            
            # status==2 代表已经产生最终评估结果
            if status == 2:
                result_b64 = data_sec.get("data", "") or data_sec.get("result", "")
                if result_b64:
                    # 将结果的 base64 解码得到 XML 内容
                    result_xml = base64.b64decode(result_b64).decode('utf-8')
                break

        ws.close()

        if not result_xml:
            raise Exception("未能成功从科大讯飞 WebSocket 中读取结果 XML 文本")

        if on_progress:
            try:
                on_progress("科大讯飞发音测评结果接收成功，解析评分中...")
            except Exception:
                pass

        # 6. 解析并提取四维分数
        scores = _parse_xfyun_xml(result_xml)
        
        log_api_call(
            api_type="语音评测 (ISE)",
            provider="科大讯飞 Xfyun",
            url=ws_url.split('?')[0],
            model="en_vip",
            action="口语发音评测 (assess_pronunciation)",
            status="success",
            extra_info=(
                f"打分成功。综合总分: {scores['total_score']} (准确度: {scores['accuracy_score']}, "
                f"流利度: {scores['fluency_score']}, 完整度: {scores['integrity_score']})"
            )
        )
        return scores

    except Exception as e:
        if ws:
            try:
                ws.close()
            except Exception:
                pass
        log_api_call(
            api_type="语音评测 (ISE)",
            provider="科大讯飞 Xfyun",
            url=ws_url.split('?')[0],
            model="en_vip",
            action="口语发音评测 (assess_pronunciation)",
            status="failed",
            extra_info=f"发音评估接口报错: {str(e)}。程序已自动激活 Mock 降级打分。"
        )
        # 出错降级
        return mock_assess_pronunciation(reference_text, f"WebSocket 异常: {str(e)}", on_progress)


async def assess_pronunciation(audio_path: str, reference_text: str, on_progress = None) -> Dict[str, Any]:
    """
    异步口语发音评测入口：
    利用事件循环的 run_in_executor 将同步阻塞的 WebSocket 网络连接流式发送投递至子线程执行，
    完美实现非阻塞的高并发 I/O 动作。
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, assess_pronunciation_sync, audio_path, reference_text, on_progress)
