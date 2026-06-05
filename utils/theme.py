"""
主题管理模块 — 现代化主题
"""

import tkinter as tk
from tkinter import ttk


class ThemeManager:
    """现代主题管理器"""

    # ── 亮色主题 ──────────────────────────────────
    LIGHT = {
        # 基础
        'bg':                '#f1f5f9',   # slate-100
        'surface':           '#ffffff',
        'sidebar_bg':        '#0f172a',   # slate-900 (dark sidebar)
        'sidebar_fg':        '#cbd5e1',   # slate-300
        'sidebar_active':    '#1e293b',   # slate-800
        'sidebar_hover':     '#1e293b',
        'sidebar_accent':    '#3b82f6',   # blue-500

        # 文字
        'fg':                '#0f172a',   # slate-900
        'fg_secondary':      '#64748b',   # slate-500
        'fg_muted':          '#94a3b8',   # slate-400

        # 强调 & 功能色
        'accent':            '#3b82f6',
        'accent_hover':      '#2563eb',
        'accent_text':       '#ffffff',
        'danger':            '#ef4444',
        'danger_hover':      '#dc2626',
        'success':           '#10b981',
        'warning':           '#f59e0b',

        # 卡片 & 面板
        'card_bg':           '#ffffff',
        'card_border':       '#e2e8f0',
        'card_hover':        '#f8fafc',

        # 输入控件
        'input_bg':          '#ffffff',
        'input_border':      '#cbd5e1',
        'input_focus':       '#3b82f6',

        # 阅读区
        'reader_bg':         '#fefcf8',
        'reader_fg':         '#1e293b',
        'reader_accent':     '#3b82f6',

        # 选择 / 高亮
        'select_bg':         '#3b82f6',
        'select_fg':         '#ffffff',
        'highlight_bg':      '#fef3c7',
        'highlight_fg':      '#92400e',

        # 分割 & 边界
        'divider':           '#e2e8f0',
        'shadow':            '#e2e8f0',

        # 进度条
        'progress_bg':       '#e2e8f0',
        'progress_fg':       '#3b82f6',

        # 菜单
        'menu_bg':           '#ffffff',
        'menu_fg':           '#0f172a',
    }

    # ── 暗色主题 ──────────────────────────────────
    DARK = {
        'bg':                '#0f172a',
        'surface':           '#1e293b',
        'sidebar_bg':        '#020617',   # darkest
        'sidebar_fg':        '#94a3b8',
        'sidebar_active':    '#1e293b',
        'sidebar_hover':     '#1e293b',
        'sidebar_accent':    '#60a5fa',

        'fg':                '#e2e8f0',
        'fg_secondary':      '#94a3b8',
        'fg_muted':          '#64748b',

        'accent':            '#3b82f6',
        'accent_hover':      '#60a5fa',
        'accent_text':       '#ffffff',
        'danger':            '#f87171',
        'danger_hover':      '#ef4444',
        'success':           '#34d399',
        'warning':           '#fbbf24',

        'card_bg':           '#1e293b',
        'card_border':       '#334155',
        'card_hover':        '#1a2332',

        'input_bg':          '#0f172a',
        'input_border':      '#334155',
        'input_focus':       '#3b82f6',

        'reader_bg':         '#0f172a',
        'reader_fg':         '#e2e8f0',
        'reader_accent':     '#60a5fa',

        'select_bg':         '#3b82f6',
        'select_fg':         '#ffffff',
        'highlight_bg':      '#422006',
        'highlight_fg':      '#fde68a',

        'divider':           '#1e293b',
        'shadow':            '#0f172a',

        'progress_bg':       '#334155',
        'progress_fg':       '#3b82f6',

        'menu_bg':           '#1e293b',
        'menu_fg':           '#e2e8f0',
    }

    # ── 字体配置 ──────────────────────────────────
    FONT_FAMILY = 'Microsoft YaHei'
    FONT_MONO   = 'Cascadia Code'

    def __init__(self):
        self._current_theme = 'light'
        self._colors = self.LIGHT.copy()

    # ── 属性 ──────────────────────────────────────

    @property
    def colors(self):
        return self._colors

    @property
    def c(self):
        """简写"""
        return self._colors

    @property
    def current_theme(self):
        return self._current_theme

    # ── 切换 ──────────────────────────────────────

    def toggle(self):
        if self._current_theme == 'light':
            self.set_dark()
        else:
            self.set_light()

    def set_light(self):
        self._current_theme = 'light'
        self._colors = self.LIGHT.copy()

    def set_dark(self):
        self._current_theme = 'dark'
        self._colors = self.DARK.copy()

    # ── 应用 ──────────────────────────────────────

    def apply_to_root(self, root):
        root.configure(bg=self.c['bg'])

    def style_ttk(self):
        """配置 ttk 全局样式"""
        style = ttk.Style()
        c = self.c
        try:
            style.theme_use('clam')
        except Exception:
            pass

        style.configure('.',
            background=c['bg'],
            foreground=c['fg'],
            font=(self.FONT_FAMILY, 10),
        )
        style.configure('TFrame', background=c['bg'])
        style.configure('Surface.TFrame', background=c['surface'])
        style.configure('Card.TFrame', background=c['card_bg'], relief=tk.FLAT)
        style.configure('Sidebar.TFrame', background=c['sidebar_bg'])

        style.configure('TLabel',
            background=c['bg'],
            foreground=c['fg'],
            font=(self.FONT_FAMILY, 10),
        )
        style.configure('Muted.TLabel',
            foreground=c['fg_secondary'],
            background=c['bg'],
            font=(self.FONT_FAMILY, 9),
        )
        style.configure('Title.TLabel',
            font=(self.FONT_FAMILY, 18, 'bold'),
            foreground=c['fg'],
            background=c['bg'],
        )
        style.configure('Heading.TLabel',
            font=(self.FONT_FAMILY, 13, 'bold'),
            foreground=c['fg'],
            background=c['bg'],
        )

        style.configure('TButton',
            background=c['card_bg'],
            foreground=c['fg'],
            borderwidth=1,
            relief=tk.FLAT,
            padding=(14, 7),
            font=(self.FONT_FAMILY, 10),
        )
        style.map('TButton',
            background=[('active', c['accent']), ('pressed', c['accent_hover'])],
            foreground=[('active', c['accent_text']), ('pressed', c['accent_text'])],
        )
        style.configure('Accent.TButton',
            background=c['accent'],
            foreground=c['accent_text'],
            borderwidth=0,
            relief=tk.FLAT,
            padding=(16, 8),
            font=(self.FONT_FAMILY, 10),
        )
        style.map('Accent.TButton',
            background=[('active', c['accent_hover']), ('pressed', c['accent_hover'])],
        )

        style.configure('TEntry',
            fieldbackground=c['input_bg'],
            foreground=c['fg'],
            borderwidth=1,
            relief=tk.FLAT,
            padding=(10, 6),
        )
        style.configure('Treeview',
            background=c['card_bg'],
            foreground=c['fg'],
            fieldbackground=c['card_bg'],
            borderwidth=0,
            rowheight=32,
        )
        style.map('Treeview',
            background=[('selected', c['select_bg'])],
            foreground=[('selected', c['select_fg'])],
        )
        style.configure('TProgressbar',
            background=c['accent'],
            troughcolor=c['progress_bg'],
            borderwidth=0,
        )
        style.configure('TScale',
            background=c['bg'],
            troughcolor=c['progress_bg'],
        )
        style.configure('TNotebook',
            background=c['bg'],
            borderwidth=0,
        )
        style.configure('TNotebook.Tab',
            background=c['card_bg'],
            foreground=c['fg'],
            padding=(18, 10),
            font=(self.FONT_FAMILY, 10),
            borderwidth=0,
        )
        style.map('TNotebook.Tab',
            background=[('selected', c['accent'])],
            foreground=[('selected', c['accent_text'])],
        )
        style.configure('TLabelframe',
            background=c['bg'],
            foreground=c['fg'],
            borderwidth=1,
        )
        style.configure('TLabelframe.Label',
            background=c['bg'],
            foreground=c['fg'],
        )
        return style

    # ── 工厂方法：现代卡片 ─────────────────────────

    def make_card(self, parent, **pack_opts):
        """创建一个带阴影效果的卡片 Frame"""
        c = self.c
        # 阴影层
        shadow = tk.Frame(parent, bg=c['bg'], highlightthickness=0)
        # 边框层
        card = tk.Frame(shadow, bg=c['card_bg'],
                        highlightbackground=c['card_border'],
                        highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        shadow.pack(fill=tk.X, **pack_opts)
        return card, shadow

    # ── 阅读背景色预设 (9 色) ─────────────────────

    READER_BG_PRESETS = [
        # (名称,   背景色,     前景色)
        ('米白',   '#fefcf8',  '#1e293b'),   # 默认
        ('纯白',   '#ffffff',  '#1e293b'),
        ('暖黄',   '#fbf0d9',  '#3d2b1f'),   # 护眼羊皮纸
        ('浅绿',   '#eef5ec',  '#1e293b'),   # 豆沙绿
        ('浅蓝',   '#eef2f8',  '#1e293b'),
        ('浅粉',   '#fdf2f2',  '#3d1f1f'),
        ('浅灰',   '#e8ecf0',  '#1e293b'),
        ('深灰',   '#1e1e1e',  '#d4d4d4'),   # 暗色背景
        ('纯黑',   '#0a0a0a',  '#cccccc'),
    ]

    @classmethod
    def get_reader_bg(cls, idx):
        """根据索引获取阅读背景色"""
        idx = max(0, min(idx, len(cls.READER_BG_PRESETS) - 1))
        return cls.READER_BG_PRESETS[idx]

    def make_sidebar_button(self, parent, text, command, icon=''):
        """创建侧边栏导航按钮"""
        c = self.c
        disp = f'  {icon}  {text}' if icon else f'  {text}'

        btn = tk.Button(parent, text=disp, command=command,
                        bg=c['sidebar_bg'], fg=c['sidebar_fg'],
                        activebackground=c['sidebar_hover'],
                        activeforeground='#ffffff',
                        font=(self.FONT_FAMILY, 11),
                        relief=tk.FLAT, anchor=tk.W,
                        padx=16, pady=10,
                        borderwidth=0, highlightthickness=0,
                        cursor='hand2')
        return btn

    def make_icon_button(self, parent, text, command, accent=False, size='normal'):
        """创建现代扁平按钮"""
        c = self.c
        bg = c['accent'] if accent else c['card_bg']
        fg = c['accent_text'] if accent else c['fg']
        hover_bg = c['accent_hover'] if accent else c['accent']
        hover_fg = c['accent_text']

        if size == 'small':
            padx, pady, font = 10, 4, (self.FONT_FAMILY, 9)
        elif size == 'large':
            padx, pady, font = 20, 10, (self.FONT_FAMILY, 12, 'bold')
        else:
            padx, pady, font = 14, 7, (self.FONT_FAMILY, 10)

        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=fg,
                        activebackground=hover_bg,
                        activeforeground=hover_fg,
                        font=font, relief=tk.FLAT,
                        padx=padx, pady=pady,
                        borderwidth=0, highlightthickness=0,
                        cursor='hand2')
        return btn

    def make_input(self, parent, textvariable=None, placeholder='', **pack_opts):
        """创建现代输入框"""
        c = self.c
        frame = tk.Frame(parent, bg=c['input_border'], padx=1, pady=1)
        entry = tk.Entry(frame, textvariable=textvariable,
                         bg=c['input_bg'], fg=c['fg'],
                         font=(self.FONT_FAMILY, 10),
                         relief=tk.FLAT, borderwidth=0,
                         insertbackground=c['fg'],
                         insertwidth=1)
        entry.pack(fill=tk.X, ipady=6, padx=10)
        frame.pack(fill=tk.X, **pack_opts)

        # focus 时高亮边框
        def on_focus(e):
            frame.configure(bg=c['input_focus'])
        def on_blur(e):
            frame.configure(bg=c['input_border'])
        entry.bind('<FocusIn>', on_focus)
        entry.bind('<FocusOut>', on_blur)
        return entry, frame


def create_progress_bar(parent, colors, width=200, height=6):
    """用 Canvas 绘制一个现代进度条（填充需外部控制）"""
    c = colors
    cv = tk.Canvas(parent, width=width, height=height,
                   bg=c['progress_bg'], highlightthickness=0, bd=0)
    cv.pack()
    return cv
