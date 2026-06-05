"""
书架视图 — 现代卡片式布局
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import chardet


class LibraryView(ttk.Frame):
    def __init__(self, parent, db_manager, theme_manager, on_open_novel=None):
        super().__init__(parent)
        self.db = db_manager
        self.theme = theme_manager
        self.on_open_novel = on_open_novel
        self._novels = []
        self._cards = []

        self._setup_ui()
        self.refresh_list()

    # ═══════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════

    def _setup_ui(self):
        c = self.theme.c

        # ── 头部 ──
        header = tk.Frame(self, bg=c['bg'])
        header.pack(fill=tk.X, padx=24, pady=(20, 0))

        tk.Label(header, text='我的书架', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 20, 'bold')).pack(side=tk.LEFT)

        # 导入按钮
        import_btn = tk.Button(
            header, text='📥  导入小说', command=self._import_novels,
            bg=c['accent'], fg=c['accent_text'],
            activebackground=c['accent_hover'], activeforeground=c['accent_text'],
            font=('Microsoft YaHei', 10), relief=tk.FLAT,
            padx=18, pady=8, borderwidth=0, cursor='hand2')
        import_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # ── 搜索栏 ──
        search_frame = tk.Frame(self, bg=c['input_border'], padx=1, pady=1)
        search_frame.pack(fill=tk.X, padx=24, pady=(14, 8))

        inner = tk.Frame(search_frame, bg=c['input_bg'])
        inner.pack(fill=tk.X)

        tk.Label(inner, text='🔍', bg=c['input_bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 11)).pack(side=tk.LEFT, padx=(12, 4), pady=6)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._on_search())
        search_entry = tk.Entry(
            inner, textvariable=self.search_var,
            bg=c['input_bg'], fg=c['fg'],
            font=('Microsoft YaHei', 11),
            relief=tk.FLAT, borderwidth=0,
            insertbackground=c['fg'], insertwidth=1)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        search_entry.bind('<FocusIn>', lambda e: search_frame.configure(bg=c['input_focus']))
        search_entry.bind('<FocusOut>', lambda e: search_frame.configure(bg=c['input_border']))

        # ── 状态栏 ──
        self.status_var = tk.StringVar(value='共 0 本小说')
        st = tk.Label(self, textvariable=self.status_var, bg=c['bg'], fg=c['fg_secondary'],
                       font=('Microsoft YaHei', 9), anchor=tk.W)
        st.pack(fill=tk.X, padx=24, pady=(0, 4))

        # ── 卡片列表（Canvas 滚动）──
        self._create_card_list()

        # ── 空状态 ──
        self._create_empty_state()

        # ── 右键菜单 ──
        self.ctx_menu = tk.Menu(self, tearoff=0, bg=c['menu_bg'], fg=c['menu_fg'],
                                 font=('Microsoft YaHei', 10))
        self.ctx_menu.add_command(label='📖  开始阅读', command=self._ctx_open)
        self.ctx_menu.add_command(label='🗑️  删除小说', command=self._ctx_delete)
        self.ctx_menu.add_command(label='📋  复制书名', command=self._ctx_copy)

    def _create_card_list(self):
        c = self.theme.c
        # Canvas + 滚动条
        self.card_canvas = tk.Canvas(self, bg=c['bg'], highlightthickness=0, bd=0)
        self.card_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                          command=self.card_canvas.yview)

        self.card_container = tk.Frame(self.card_canvas, bg=c['bg'])

        self.card_container.bind('<Configure>',
            lambda e: self.card_canvas.configure(scrollregion=self.card_canvas.bbox('all')))

        self.card_window = self.card_canvas.create_window(
            (0, 0), window=self.card_container, anchor='nw', tags='card_window')

        self.card_canvas.configure(yscrollcommand=self.card_scroll.set)
        self.card_canvas.bind('<Configure>', self._on_canvas_resize)

        # 鼠标滚轮
        self.card_canvas.bind('<MouseWheel>',
            lambda e: self.card_canvas.yview_scroll(int(-e.delta / 120), 'units'))
        self.card_canvas.bind('<Button-4>', lambda e: self.card_canvas.yview_scroll(-1, 'units'))
        self.card_canvas.bind('<Button-5>', lambda e: self.card_canvas.yview_scroll(1, 'units'))

        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.card_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_canvas_resize(self, event):
        self.card_canvas.itemconfig(self.card_window, width=event.width)

    def _create_empty_state(self):
        c = self.theme.c
        self.empty_frame = tk.Frame(self, bg=c['bg'])

        inner = tk.Frame(self.empty_frame, bg=c['bg'])
        inner.pack(expand=True)

        tk.Label(inner, text='📂', bg=c['bg'], fg=c['fg_muted'],
                 font=('Segoe UI', 48)).pack(pady=(0, 8))
        tk.Label(inner, text='书架空空如也', bg=c['bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 15, 'bold')).pack()
        tk.Label(inner, text='点击右上角「📥 导入小说」开始你的阅读之旅',
                 bg=c['bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 10)).pack(pady=(6, 0))

    # ═══════════════════════════════════════════════
    #  数据刷新
    # ═══════════════════════════════════════════════

    def refresh_list(self):
        self._novels = self.db.get_all_novels()
        self.status_var.set(f'共 {len(self._novels)} 本小说')

        # 清空旧卡片
        for card in self._cards:
            card.destroy()
        self._cards = []

        if not self._novels:
            self.card_canvas.pack_forget()
            self.card_scroll.pack_forget()
            self.empty_frame.pack(fill=tk.BOTH, expand=True)
            return

        self.empty_frame.pack_forget()
        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.card_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for n in self._novels:
            card = self._make_card(n)
            self._cards.append(card)

    def _make_card(self, novel):
        c = self.theme.c
        nid = novel['id']

        # 卡片外层
        card = tk.Frame(self.card_container, bg=c['card_bg'],
                        highlightbackground=c['card_border'],
                        highlightthickness=1, cursor='hand2')
        card.pack(fill=tk.X, padx=24, pady=(4, 4))

        inner = tk.Frame(card, bg=c['card_bg'])
        inner.pack(fill=tk.X, padx=18, pady=14)

        # 进度
        total = novel['total_chars']
        progress_pos = novel['progress_pos'] or 0
        pct = progress_pos * 100 // total if total > 0 else 0

        # ── 左：信息 ──
        left = tk.Frame(inner, bg=c['card_bg'])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 书名行
        title_row = tk.Frame(left, bg=c['card_bg'])
        title_row.pack(fill=tk.X)

        title_lbl = tk.Label(title_row, text=novel['title'], bg=c['card_bg'], fg=c['fg'],
                              font=('Microsoft YaHei', 13, 'bold'), anchor=tk.W)
        title_lbl.pack(side=tk.LEFT)

        # 进度徽章
        badge_bg = c['success'] if pct >= 100 else c['accent']
        badge = tk.Frame(title_row, bg=badge_bg, padx=6, pady=1)
        badge.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(badge, text=f'{pct}%', bg=badge_bg, fg='#ffffff',
                 font=('Microsoft YaHei', 8, 'bold')).pack()

        # 详情行
        detail = tk.Frame(left, bg=c['card_bg'])
        detail.pack(fill=tk.X, pady=(5, 0))

        author = novel['author'] or '佚名'
        ch_count = self.db.get_chapters(nid)
        chs = f'{len(ch_count)}章' if ch_count else ''

        chars = self._fmt_chars(total)
        info_parts = [author, chars]
        if chs:
            info_parts.insert(1, chs)

        info_text = ' · '.join(info_parts)
        tk.Label(detail, text=info_text, bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9), anchor=tk.W).pack(side=tk.LEFT)

        last_read = novel['last_read_at'] or novel['created_at'] or ''
        if last_read:
            tk.Label(detail, text=f'上次: {last_read}', bg=c['card_bg'], fg=c['fg_muted'],
                     font=('Microsoft YaHei', 8), anchor=tk.W).pack(side=tk.RIGHT)

        # 进度条
        if total > 0:
            bar_frame = tk.Frame(inner, bg=c['progress_bg'], height=4)
            bar_frame.pack(fill=tk.X, pady=(8, 0))
            bar_frame.pack_propagate(False)
            bar_fill = tk.Frame(bar_frame, bg=c['progress_fg'], height=4)
            bar_fill.pack(side=tk.LEFT)
            bar_fill.place(relwidth=pct / 100, relheight=1)

        # ── 交互绑定 ──
        for w in (card, inner, left, title_lbl):
            w.bind('<Button-1>', lambda e, nid=nid: self._open_novel(nid))
            w.bind('<Button-3>', lambda e, nid=nid: self._show_ctx(e, nid))

        # hover 效果
        def on_enter(e, c_=card, bg_c=c['card_hover']):
            try:
                c_.configure(bg=bg_c)
                for child in c_.winfo_children():
                    try:
                        child.configure(bg=bg_c)
                    except:
                        pass
            except:
                pass

        def on_leave(e, c_=card, bg_c=c['card_bg']):
            try:
                c_.configure(bg=bg_c)
                for child in c_.winfo_children():
                    try:
                        child.configure(bg=bg_c)
                    except:
                        pass
            except:
                pass

        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)

        # 双击打开
        card.bind('<Double-Button-1>', lambda e, nid=nid: self._open_novel(nid))

        return card

    # ═══════════════════════════════════════════════
    #  交互
    # ═══════════════════════════════════════════════

    def _on_search(self):
        kw = self.search_var.get().strip()
        if not kw:
            self.refresh_list()
            return

        self._novels = self.db.search_novels(kw)
        self.status_var.set(f'找到 {len(self._novels)} 本')

        for card in self._cards:
            card.destroy()
        self._cards = []

        if not self._novels:
            self.card_canvas.pack_forget()
            self.card_scroll.pack_forget()
            self.empty_frame.pack(fill=tk.BOTH, expand=True)
            return

        self.empty_frame.pack_forget()
        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.card_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for n in self._novels:
            card = self._make_card(n)
            self._cards.append(card)

    def _open_novel(self, nid):
        self.db.update_last_read(nid)
        if self.on_open_novel:
            self.on_open_novel(nid)

    def _show_ctx(self, event, nid):
        self._ctx_nid = nid
        self.ctx_menu.post(event.x_root, event.y_root)

    def _ctx_open(self):
        if hasattr(self, '_ctx_nid'):
            self._open_novel(self._ctx_nid)

    def _ctx_delete(self):
        if not hasattr(self, '_ctx_nid'):
            return
        nid = self._ctx_nid
        novel = self.db.get_novel(nid)
        if not novel:
            return
        if messagebox.askyesno('确认删除', f'确定要删除《{novel["title"]}》吗？\n\n这将同时删除所有关联的阅读进度和书签。'):
            self.db.delete_novel(nid)
            self.refresh_list()

    def _ctx_copy(self):
        if not hasattr(self, '_ctx_nid'):
            return
        novel = self.db.get_novel(self._ctx_nid)
        if novel:
            self.clipboard_clear()
            self.clipboard_append(novel['title'])

    def _import_novels(self):
        files = filedialog.askopenfilenames(
            title='选择小说文件',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')])

        if not files:
            return

        imported, failed = 0, 0
        for filepath in files:
            try:
                with open(filepath, 'rb') as f:
                    raw_data = f.read()

                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)

                if confidence < 0.7:
                    for enc in ['utf-8', 'gbk', 'gb2312', 'big5']:
                        try:
                            raw_data.decode(enc)
                            encoding = enc
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue

                content = raw_data.decode(encoding, errors='replace')
                title = os.path.splitext(os.path.basename(filepath))[0]
                title = title.replace('【', '').replace('】', '').strip()

                novel_id = self.db.add_novel(
                    title=title, file_path=filepath,
                    content=content, total_chars=len(content))

                from chapter_parser import detect_chapters
                chapters = detect_chapters(content)
                if chapters:
                    batch = [(novel_id, idx, ch[1], ch[2], ch[3])
                             for idx, ch in enumerate(chapters)]
                    self.db.add_chapters_batch(batch)

                imported += 1
            except Exception as e:
                print(f'导入失败: {filepath}, 错误: {e}')
                failed += 1

        self.refresh_list()
        if imported > 0:
            msg = f'成功导入 {imported} 本小说'
            if failed > 0:
                msg += f'\n失败 {failed} 本'
            messagebox.showinfo('导入完成', msg)

    # ═══════════════════════════════════════════════
    #  工具
    # ═══════════════════════════════════════════════

    def _fmt_chars(self, count):
        if count >= 10000:
            return f'{count / 10000:.1f}万字'
        elif count >= 1000:
            return f'{count / 1000:.1f}千字'
        return f'{count}字'
