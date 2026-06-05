"""
TTS 引擎 - edge-tts (在线) + pyttsx3 (离线备份)
纯文本模式（不用 SSML，避免 edge-tts 兼容性导致的乱码）
"""

import asyncio, ctypes, os, re, threading, tempfile, time
import pyttsx3

winmm = ctypes.windll.winmm


def _mci_exec(cmd):
    buf = ctypes.create_unicode_buffer(256)
    winmm.mciSendStringW(cmd, buf, 255, 0)


# ==================== SAPI 离线引擎 ====================

class SAPIEngine:
    def __init__(self):
        self._e = None
        self._init()

    def _init(self):
        try:
            self._e = pyttsx3.init()
            self._e.setProperty('rate', 180)
            self._e.setProperty('volume', 1.0)
            self._e.startLoop(False)
        except Exception as e:
            print(f'sapi init: {e}')
            self._e = None

    def get_voices(self):
        if not self._e:
            return []
        try:
            return [{'id': v.id, 'name': v.name, 'source': 'sapi'}
                    for v in self._e.getProperty('voices')]
        except Exception:
            return []

    def set_voice(self, vid):
        if self._e:
            try:
                self._e.setProperty('voice', vid)
            except Exception:
                pass

    def set_rate(self, r):
        if self._e:
            try:
                self._e.setProperty('rate', int(r))
            except Exception:
                pass

    def set_volume(self, v):
        if self._e:
            try:
                self._e.setProperty('volume', max(0.0, min(1.0, float(v))))
            except Exception:
                pass

    def speak(self, text, callback=None):
        clean = re.sub(r'\s+', ' ', text).strip()
        if not self._e or not clean:
            if callback:
                callback()
            return

        def _run():
            try:
                self._e.say(clean)
                self._e.runAndWait()
            except Exception:
                pass
            finally:
                if callback:
                    callback()
        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        if self._e:
            try:
                self._e.stop()
            except Exception:
                pass

    def is_busy(self):
        if self._e:
            try:
                return self._e.isBusy()
            except Exception:
                pass
        return False


# ==================== edge-tts 在线引擎 ====================

class EdgeEngine:
    VOICES = [
        {'id': 'zh-CN-XiaoxiaoNeural',  'name': '晓晓 (温柔女)', 'source': 'edge'},
        {'id': 'zh-CN-XiaoyiNeural',    'name': '晓伊 (活泼女)', 'source': 'edge'},
        {'id': 'zh-CN-YunxiaNeural',    'name': '云霞 (甜美女)', 'source': 'edge'},
        {'id': 'zh-CN-YunxiNeural',     'name': '云希 (磁性男)', 'source': 'edge'},
        {'id': 'zh-CN-YunyangNeural',   'name': '云扬 (新闻男)', 'source': 'edge'},
        {'id': 'zh-CN-YunjianNeural',   'name': '云健 (活力男)', 'source': 'edge'},
        {'id': 'zh-CN-liaoning-XiaobeiNeural', 'name': '晓北 (东北话)', 'source': 'edge'},
        {'id': 'zh-CN-shaanxi-XiaoniNeural',   'name': '晓妮 (陕西话)', 'source': 'edge'},
        {'id': 'zh-HK-HiuGaaiNeural',   'name': '曉佳 (粤语)',   'source': 'edge'},
        {'id': 'zh-HK-HiuMaanNeural',   'name': '曉曼 (粤语)',   'source': 'edge'},
        {'id': 'zh-TW-HsiaoChenNeural', 'name': '曉臻 (台语)',   'source': 'edge'},
        {'id': 'zh-TW-HsiaoYuNeural',   'name': '曉雨 (台语)',   'source': 'edge'},
    ]

    def __init__(self):
        self._voice = 'zh-CN-XiaoxiaoNeural'
        self._rate = '+0%'
        self._vol = '+0%'
        self._abort = threading.Event()
        self._playing = False

    def get_voices(self):
        return [{'id': v['id'], 'name': v['name'], 'source': v['source']}
                for v in self.VOICES]

    def set_voice(self, vid):
        for v in self.VOICES:
            if v['id'] == vid:
                self._voice = vid
                return

    def set_rate(self, r):
        pct = (int(r) - 180) * 150 / 170
        pct = max(-50, min(100, int(pct)))
        self._rate = f'{pct:+d}%'

    def set_volume(self, v):
        pct = int((float(v) - 1.0) * 50)
        self._vol = f'{pct:+d}%'

    # ── 内部：事件循环生成 ──

    def _gen(self, text, path):
        """纯文本生成 MP3"""
        async def g():
            import edge_tts
            await edge_tts.Communicate(
                text, self._voice, rate=self._rate, volume=self._vol
            ).save(path)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(g())
        finally:
            loop.close()

    # ── 文本预处理 ──

    @staticmethod
    def _clean_text(text):
        """清理文本：压缩空白、去首尾"""
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _join_sentences(sentences):
        """将句子列表拼接为纯文本。
        句子来自 split_sentences 已保留标点（。！？；…），
        TTS 引擎会自动在标点处停顿。
        每个句子都保留，不过滤 — 保证与 reader 端的 sentence 计数一致。
        """
        return ''.join(sentences)

    # ── 同步生成 ──

    def generate(self, text):
        """生成单段文本 MP3，返回临时文件路径"""
        clean = self._clean_text(text)
        if not clean:
            return None
        try:
            fd, path = tempfile.mkstemp(suffix='.mp3')
            os.close(fd)
            self._gen(clean, path)
            return path if os.path.getsize(path) > 0 else None
        except Exception:
            return None

    def generate_sentences(self, sentences):
        """将句子列表拼接后生成 MP3"""
        return self.generate(self._join_sentences(sentences))

    # ── 异步生成（不阻塞 UI） ──

    def generate_async(self, text, callback):
        """后台线程生成 MP3 → callback(mp3_path 或 None)"""
        def _run():
            result = None
            try:
                result = self.generate(text)
            except Exception as e:
                print(f'generate_async error: {e}')
            finally:
                if callback:
                    callback(result)
        threading.Thread(target=_run, daemon=True).start()

    def generate_sentences_async(self, sentences, callback):
        """后台线程生成句子批次 MP3"""
        text = self._join_sentences(sentences)
        self.generate_async(text, callback)

    # ── 播放 ──

    def _play_mp3(self, mp3_path):
        self._abort.clear()
        self._playing = True
        try:
            escaped = mp3_path.replace('\\', '\\\\')
            _mci_exec(f'open "{escaped}" type mpegvideo alias edgeplay')
            _mci_exec(f'play edgeplay')

            buf = ctypes.create_unicode_buffer(256)
            while self._playing and not self._abort.is_set():
                winmm.mciSendStringW('status edgeplay mode', buf, 255, 0)
                if buf.value.strip() != 'playing':
                    break
                time.sleep(0.1)

            _mci_exec('close edgeplay')
        except Exception as e:
            print(f'play error: {e}')
        finally:
            self._playing = False
            try:
                _mci_exec('close edgeplay')
            except Exception:
                pass

    def play(self, mp3_path, callback=None):
        """播放 MP3，播完自动删除 + 回调"""
        if not mp3_path:
            if callback:
                callback()
            return
        self._playing = True

        def _run():
            try:
                self._play_mp3(mp3_path)
            finally:
                try:
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                except Exception:
                    pass
                if callback:
                    callback()
        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        self._abort.set()
        self._playing = False
        try:
            _mci_exec('stop edgeplay')
            _mci_exec('close edgeplay')
        except Exception:
            pass

    @property
    def is_playing(self):
        return self._playing


# ==================== 统一引擎 ====================

class TTSEngine:
    def __init__(self):
        self.edge = EdgeEngine()
        self.sapi = SAPIEngine()
        self._use_edge = True

    def list_voices(self):
        voices = self.edge.get_voices()
        voices.append({'id': '---', 'name': '── 系统语音 ──', 'source': 'sep'})
        voices.extend(self.sapi.get_voices())
        return voices

    def set_voice(self, vid):
        if any(v['id'] == vid for v in EdgeEngine.VOICES):
            self.edge.set_voice(vid)
            self._use_edge = True
        else:
            self.sapi.set_voice(vid)
            self._use_edge = False

    def set_rate(self, r):
        self.edge.set_rate(r)
        self.sapi.set_rate(r)

    def set_volume(self, v):
        self.edge.set_volume(v)
        self.sapi.set_volume(v)

    # ── 同步 ──

    def generate(self, text):
        return self.edge.generate(text) if self._use_edge else None

    def generate_sentences(self, sentences):
        """句子批次 → MP3"""
        text = self.edge._join_sentences(sentences)
        return self.generate(text)

    # ── 异步 ──

    def generate_async(self, text, callback):
        if self._use_edge:
            self.edge.generate_async(text, callback)
        elif callback:
            callback(None)

    def generate_sentences_async(self, sentences, callback):
        """异步生成句子批次 MP3"""
        if self._use_edge:
            self.edge.generate_sentences_async(sentences, callback)
        elif callback:
            callback(None)

    # ── 播放 ──

    def play(self, mp3_path, callback=None):
        if self._use_edge and mp3_path:
            self.edge.play(mp3_path, callback=callback)
        elif callback:
            callback()

    def speak(self, text, callback=None):
        """单段文本：生成 + 播放"""
        if self._use_edge:
            mp3 = self.edge.generate(text)
            if mp3:
                self.edge.play(mp3, callback=callback)
            else:
                self.sapi.speak(text, callback=callback)
        else:
            self.sapi.speak(text, callback=callback)

    def speak_sentences(self, sentences, callback=None):
        """句子批次：拼接 → 生成 + 播放。
        edge-tts 失败自动回退 SAPI。"""
        if self._use_edge and sentences:
            text = self.edge._join_sentences(sentences)
            mp3 = self.edge.generate(text)
            if mp3:
                self.edge.play(mp3, callback=callback)
            else:
                self.sapi.speak(text, callback=callback)
        elif sentences:
            text = self.edge._join_sentences(sentences)
            self.sapi.speak(text, callback=callback)
        elif callback:
            callback()

    # ── 控制 ──

    def stop(self):
        self.edge.stop()
        self.sapi.stop()

    def is_playing(self):
        if self._use_edge:
            return self.edge.is_playing
        return self.sapi.is_busy()
