# 📚 小说播放器 v2.0

一款现代化的 Windows 桌面小说朗读软件，支持导入 TXT 小说、AI 语音朗读、书签管理。

## ✨ 功能

- 📥 **导入小说** — 拖拽或选择 `.txt` 文件，自动识别编码和章节
- 🎙️ **AI 语音朗读** — 支持 Edge TTS 在线语音 + 系统 SAPI 离线语音
- 📖 **逐句跟读** — 朗读时文字自动高亮并滚动跟随
- 🔖 **书签管理** — 随时添加书签，一键跳转
- 🌙 **暗色模式** — 护眼暗色主题，适合夜间阅读
- ⚡ **快捷键** — 空格播放/暂停、方向键导航、Ctrl+B 书签

## 🚀 安装

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/novel-player.git
cd novel-player

# 2. 安装依赖
pip install -r requirements.txt
```

## 🎮 使用

```bash
python main.py
```

| 快捷键 | 功能 |
|--------|------|
| `Space` | 播放 / 暂停 |
| `→ ←` | 下一句 / 上一句 |
| `Ctrl + B` | 添加书签 |
| `Ctrl + I` | 导入小说 |
| `Esc` | 返回书架 |

## 📦 依赖

- Python 3.10+
- `edge-tts` — 在线 AI 语音（微软 Edge TTS）
- `pyttsx3` — 离线语音引擎
- `chardet` — 文本编码检测

## 📁 项目结构

```
novel-player/
├── main.py              # 主程序入口
├── db_manager.py        # SQLite 数据库管理
├── tts_engine.py        # TTS 朗读引擎
├── chapter_parser.py    # 章节识别与分句
├── utils/
│   └── theme.py         # 主题管理
├── views/
│   ├── library_view.py  # 书架视图
│   ├── reader_view.py   # 阅读器视图
│   └── settings_view.py # 设置视图
└── requirements.txt
```

## 📄 许可

MIT License
