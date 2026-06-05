"""
小说播放器 — 主程序
"""

import ctypes, sys, os

# 高 DPI
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DatabaseManager
from tts_engine import TTSEngine
from utils.theme import ThemeManager
from views.library_view import LibraryView
from views.reader_view import ReaderView
from views.settings_view import SettingsView


class NovelPlayerApp:
    SIDEBAR_W = 200

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('小说播放器')

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        ww, wh = int(sw * 0.85), int(sh * 0.85)
        self.root.geometry(f'{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}')
        self.root.minsize(900, 550)

        self.db = DatabaseManager()
        self.tts = TTSEngine()
        self.theme = ThemeManager()

        st = self.db.get_setting('theme', 'light')
        if st == 'dark':
            self.theme.set_dark()
        self.theme.apply_to_root(self.root)
        self.theme.style_ttk()

        # 持久化视图
        self.library_view = None
        self.reader_view = None
        self.settings_view = None
        self._current_view_name = None  # 'library' | 'reader' | 'settings'
        self._sidebar_btns = []

        self._setup_ui()
        self._setup_keys()
        self._show_library()

        # 关闭协议 — 双保险
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    # ═══════════════════════════════════════════════
    #  UI 框架 — 侧边栏 + 内容区
    # ═══════════════════════════════════════════════

    def _setup_ui(self):
        c = self.theme.c

        # 根布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # ── 左侧边栏 ──
        self.sidebar = tk.Frame(self.root, bg=c['sidebar_bg'], width=self.SIDEBAR_W)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        self.sidebar.grid_propagate(False)

        # 品牌区
        brand = tk.Frame(self.sidebar, bg=c['sidebar_bg'])
        brand.pack(fill=tk.X, padx=12, pady=(18, 10))
        tk.Label(brand, text='📚', bg=c['sidebar_bg'],
                 font=('Segoe UI', 22)).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(brand, text='小说播放器', bg=c['sidebar_bg'], fg='#ffffff',
                 font=('Microsoft YaHei', 13, 'bold')).pack(side=tk.LEFT)

        # 分隔线
        tk.Frame(self.sidebar, bg='#334155', height=1).pack(fill=tk.X, padx=12, pady=(0, 8))

        # 导航按钮
        self._sidebar_btns = []
        self.nav_library = self._make_nav_btn('📖  我的书架', self._show_library)
        self.nav_reader  = self._make_nav_btn('📑  阅读',     self._show_reader)
        self.nav_settings= self._make_nav_btn('⚙️  设置',     self._show_settings)

        # 底部
        self.sidebar_bottom = tk.Frame(self.sidebar, bg=c['sidebar_bg'])
        self.sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=12)

        tk.Frame(self.sidebar, bg='#334155', height=1).pack(
            side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 4))

        t = '🌙  夜间' if self.theme.current_theme == 'light' else '☀️  日间'
        self.theme_btn = tk.Button(
            self.sidebar_bottom, text=t, command=self._toggle_theme,
            bg=c['sidebar_bg'], fg=c['sidebar_fg'],
            activebackground=c['sidebar_hover'], activeforeground='#ffffff',
            font=('Microsoft YaHei', 10), relief=tk.FLAT,
            padx=12, pady=7, cursor='hand2')
        self.theme_btn.pack(fill=tk.X)

        # ── 右侧内容区 ──
        self.content_frame = tk.Frame(self.root, bg=c['bg'])
        self.content_frame.grid(row=0, column=1, sticky='nsew')

    def _make_nav_btn(self, text, cmd):
        c = self.theme.c
        btn = tk.Button(
            self.sidebar, text=text, command=cmd,
            bg=c['sidebar_bg'], fg=c['sidebar_fg'],
            activebackground=c['sidebar_hover'], activeforeground='#ffffff',
            font=('Microsoft YaHei', 11), relief=tk.FLAT,
            anchor=tk.W, padx=16, pady=10,
            borderwidth=0, highlightthickness=0,
            cursor='hand2')
        btn.pack(fill=tk.X, padx=6, pady=1)
        self._sidebar_btns.append(btn)
        return btn

    def _highlight_nav(self, active_btn):
        c = self.theme.c
        for b in self._sidebar_btns:
            b.configure(bg=c['sidebar_bg'], fg=c['sidebar_fg'])
        active_btn.configure(bg=c['sidebar_active'], fg='#ffffff')

    # ═══════════════════════════════════════════════
    #  快捷键
    # ═══════════════════════════════════════════════

    def _setup_keys(self):
        self.root.bind('<Control-i>', lambda e: self._key_import())
        self.root.bind('<Control-b>', lambda e: self._key_bookmark())
        self.root.bind('<space>', lambda e: self._key_play())
        self.root.bind('<Right>', lambda e: self._key_next())
        self.root.bind('<Left>', lambda e: self._key_prev())
        self.root.bind('<Escape>', lambda e: self._show_library())

    def _key_import(self):
        if self.library_view:
            self._show_library()
            self.library_view._import_novels()

    def _key_bookmark(self):
        if self.reader_view and self.reader_view.current_novel:
            self.reader_view._add_bm()

    def _key_play(self):
        if self._current_view_name == 'reader' and self.reader_view and self.reader_view.current_novel:
            self.reader_view._toggle()

    def _key_next(self):
        if self._current_view_name == 'reader' and self.reader_view and self.reader_view.current_novel:
            self.reader_view._next_s()

    def _key_prev(self):
        if self._current_view_name == 'reader' and self.reader_view and self.reader_view.current_novel:
            self.reader_view._prev_s()

    # ═══════════════════════════════════════════════
    #  视图切换（不销毁视图）
    # ═══════════════════════════════════════════════

    def _hide_all_views(self):
        for v in [self.library_view, self.reader_view, self.settings_view]:
            if v is not None:
                try:
                    v.pack_forget()
                except:
                    pass

    def _show_library(self):
        self._save_reader_progress()
        self._hide_all_views()
        self._highlight_nav(self.nav_library)

        if self.library_view is None:
            self.library_view = LibraryView(
                self.content_frame, self.db, self.theme,
                on_open_novel=self._open_novel)
        self.library_view.pack(fill=tk.BOTH, expand=True)
        self.library_view.refresh_list()
        self._current_view_name = 'library'

    def _show_reader(self):
        if self.reader_view is None or not self.reader_view.current_novel:
            novels = self.db.get_all_novels()
            if novels:
                self._open_novel(novels[0]['id'])
            else:
                messagebox.showinfo('提示', '请先导入小说')
                self._show_library()
            return

        self._hide_all_views()
        self._highlight_nav(self.nav_reader)
        self.reader_view.pack(fill=tk.BOTH, expand=True)
        self._current_view_name = 'reader'

    def _show_settings(self):
        self._save_reader_progress()
        self._hide_all_views()
        self._highlight_nav(self.nav_settings)

        if self.settings_view is None:
            self.settings_view = SettingsView(
                self.content_frame, self.db, self.tts, self.theme,
                on_theme_toggle=self._on_theme_changed)
        self.settings_view.pack(fill=tk.BOTH, expand=True)
        self.settings_view._load_voices()
        self._current_view_name = 'settings'

    def _open_novel(self, novel_id):
        self._save_reader_progress()
        self._hide_all_views()
        self._highlight_nav(self.nav_reader)

        if self.reader_view is None:
            self.reader_view = ReaderView(
                self.content_frame, self.db, self.tts, self.theme,
                on_back=self._show_library)
        self.reader_view.pack(fill=tk.BOTH, expand=True)
        self.reader_view.open_novel(novel_id)
        self._current_view_name = 'reader'

    def _save_reader_progress(self):
        if self.reader_view and self.reader_view.current_novel:
            try:
                self.reader_view._save()
            except Exception:
                pass

    # ═══════════════════════════════════════════════
    #  主题切换
    # ═══════════════════════════════════════════════

    def _toggle_theme(self):
        self.theme.toggle()
        self._on_theme_changed()

    def _on_theme_changed(self):
        t = '🌙  夜间' if self.theme.current_theme == 'light' else '☀️  日间'
        self.theme_btn.configure(text=t)
        self.db.set_setting('theme', self.theme.current_theme)
        self._rebuild_ui()

    def _rebuild_ui(self):
        cur = self._current_view_name
        nid = None
        if cur == 'reader' and self.reader_view and self.reader_view.current_novel:
            nid = self.reader_view.novel_id
            try:
                self.reader_view._save()
            except Exception:
                pass

        # 销毁所有子控件
        for w in self.root.winfo_children():
            w.destroy()

        self.library_view = None
        self.reader_view = None
        self.settings_view = None
        self._sidebar_btns = []

        self.theme.apply_to_root(self.root)
        self.theme.style_ttk()
        self._setup_ui()

        if cur == 'reader' and nid:
            self._open_novel(nid)
        elif cur == 'settings':
            self._show_settings()
        else:
            self._show_library()

    # ═══════════════════════════════════════════════
    #  关闭
    # ═══════════════════════════════════════════════

    def _on_close(self):
        """点击关闭按钮 — 必须有异常保护确保能关闭"""
        try:
            self._save_reader_progress()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass
        finally:
            # 确保一定会关闭窗口
            try:
                self.root.quit()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass
            self._closed = True

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    NovelPlayerApp().run()
