"""
阅读器视图 — 完整版
- 高亮由 TTS 回调驱动（不估时不乱跳）
- Canvas 醒目可拖拽进度条
- 顶栏 🔊 语音设置按钮
- 预生成管道、9 色背景、圆形播放按钮
"""

import os, threading, tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from chapter_parser import split_sentences

READER_BG_PRESETS = [
    ('米白', '#fefcf8', '#1e293b', '#3b82f6'),
    ('纯白', '#ffffff', '#1e293b', '#3b82f6'),
    ('暖黄', '#fbf0d9', '#3d2b1f', '#b45309'),
    ('浅绿', '#eef5ec', '#1e293b', '#16a34a'),
    ('浅蓝', '#eef2f8', '#1e293b', '#2563eb'),
    ('浅粉', '#fdf2f2', '#3d1f1f', '#dc2626'),
    ('浅灰', '#e8ecf0', '#1e293b', '#475569'),
    ('深灰', '#1e1e1e', '#d4d4d4', '#60a5fa'),
    ('纯黑', '#0a0a0a', '#cccccc', '#60a5fa'),
]


class ReaderView(ttk.Frame):
    BATCH_CHARS = 200

    def __init__(self, parent, db_manager, tts_engine, theme_manager, on_back=None):
        super().__init__(parent)
        self.db = db_manager
        self.tts = tts_engine
        self.theme = theme_manager
        self.on_back = on_back

        self.novel_id = None
        self.novel = None
        self.chapter_idx = 0
        self.sentence_idx = 0
        self.chapters = []
        self.sentences = []
        self.playing = False
        self._stags = []
        self._batch_n = 0
        self.current_novel = None
        self.current_novel_id = None

        self._bg_idx = 0
        self._reader_bg = READER_BG_PRESETS[0][1]
        self._reader_fg = READER_BG_PRESETS[0][2]
        self._reader_accent = READER_BG_PRESETS[0][3]

        self._pre_gen_mp3 = None
        self._pre_gen_start_idx = -1
        self._pre_gen_token = 0

        self._progress_value = 0.0
        self._bar_w = 0
        self._bar_h = 0

        self._setup_ui()

    # ═══════════════════════════════════════════════
    #  UI 框架
    # ═══════════════════════════════════════════════

    def _setup_ui(self):
        c = self.theme.c

        # ── 顶栏 ──
        topbar = tk.Frame(self, bg=c['bg'])
        topbar.pack(fill=tk.X, padx=20, pady=(14, 0))

        # 左侧：返回 + 书名
        tk.Button(topbar, text='←  返回书架', command=self._go_back,
                  bg=c['card_bg'], fg=c['fg'],
                  activebackground=c['accent'], activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 10), relief=tk.FLAT,
                  padx=12, pady=5, borderwidth=0, cursor='hand2',
                  highlightbackground=c['card_border'], highlightthickness=1
                  ).pack(side=tk.LEFT)

        self.title_var = tk.StringVar(value='未打开书籍')
        tk.Label(topbar, textvariable=self.title_var, bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 14, 'bold')).pack(side=tk.LEFT, padx=14)

        # 右侧按钮组（从右往左 pack）
        tk.Button(topbar, text='🔊  语音设置', command=self._show_voice_dlg,
                  bg=c['accent'], fg=c['accent_text'],
                  activebackground=c['accent_hover'], activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 9, 'bold'), relief=tk.FLAT,
                  padx=14, pady=6, borderwidth=0, cursor='hand2'
                  ).pack(side=tk.RIGHT, padx=2)

        tk.Button(topbar, text='📋  书签列表', command=self._show_bms,
                  bg=c['card_bg'], fg=c['fg'],
                  activebackground=c['accent'], activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 9), relief=tk.FLAT,
                  padx=12, pady=5, borderwidth=0, cursor='hand2',
                  highlightbackground=c['card_border'], highlightthickness=1
                  ).pack(side=tk.RIGHT, padx=3)

        tk.Button(topbar, text='🔖  添加书签', command=self._add_bm,
                  bg=c['card_bg'], fg=c['fg'],
                  activebackground=c['accent'], activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 9), relief=tk.FLAT,
                  padx=12, pady=5, borderwidth=0, cursor='hand2',
                  highlightbackground=c['card_border'], highlightthickness=1
                  ).pack(side=tk.RIGHT, padx=3)

        # ── 主体 ──
        body = tk.Frame(self, bg=c['bg'])
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 0))
        self._make_sidebar(body, c)
        tk.Frame(body, bg=c['divider'], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self._make_reader(body, c)

        # ── 进度条 ──
        self._make_progress_bar(c)

        # ── 控制栏 ──
        self._make_control_bar(c)

        # ── 状态 ──
        self.prog_var = tk.StringVar(value='')
        tk.Label(self, textvariable=self.prog_var, bg=c['bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 9), anchor=tk.W).pack(
            fill=tk.X, padx=20, pady=(2, 8))

    def _make_sidebar(self, parent, c):
        sb = tk.Frame(parent, bg=c['bg'], width=185)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        hdr = tk.Frame(sb, bg=c['bg'])
        hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(hdr, text='📑  目录', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=tk.LEFT, padx=2)

        self.ch_search_var = tk.StringVar()
        ch_search_frame = tk.Frame(sb, bg=c['input_border'], padx=1, pady=1)
        ch_search_frame.pack(fill=tk.X, pady=(0, 6))
        ch_entry = tk.Entry(ch_search_frame, textvariable=self.ch_search_var,
                            bg=c['input_bg'], fg=c['fg'],
                            font=('Microsoft YaHei', 9),
                            relief=tk.FLAT, borderwidth=0,
                            insertbackground=c['fg'])
        ch_entry.pack(fill=tk.X, ipady=3, padx=6)
        ch_entry.bind('<FocusIn>', lambda e: ch_search_frame.configure(bg=c['input_focus']))
        ch_entry.bind('<FocusOut>', lambda e: ch_search_frame.configure(bg=c['input_border']))
        self.ch_search_var.trace_add('write', lambda *a: self._filter_chapters())

        lf = tk.Frame(sb, bg=c['bg'])
        lf.pack(fill=tk.BOTH, expand=True)
        sc = tk.Scrollbar(lf, orient=tk.VERTICAL)
        self.ch_lb = tk.Listbox(
            lf, yscrollcommand=sc.set,
            bg=c['card_bg'], fg=c['fg'],
            font=('Microsoft YaHei', 10),
            selectbackground=c['select_bg'],
            selectforeground=c['select_fg'],
            borderwidth=0, highlightthickness=1,
            highlightbackground=c['card_border'],
            highlightcolor=c['accent'])
        sc.config(command=self.ch_lb.yview)
        self.ch_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)
        self.ch_lb.bind('<<ListboxSelect>>', self._on_ch)
        self._all_chapters = []

    def _make_reader(self, parent, c):
        rf = tk.Frame(parent, bg=c['reader_bg'])
        rf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_row = tk.Frame(rf, bg=c['reader_bg'])
        title_row.pack(fill=tk.X, padx=4, pady=(2, 0))

        self.cht_var = tk.StringVar()
        tk.Label(title_row, textvariable=self.cht_var, bg=c['reader_bg'],
                 fg=c['reader_accent'],
                 font=('Microsoft YaHei', 15, 'bold'), anchor=tk.W,
                 padx=14, pady=8).pack(side=tk.LEFT)

        self._make_bg_palette(title_row, c)
        tk.Frame(rf, bg=c['divider'], height=1).pack(fill=tk.X, padx=14)

        tf = tk.Frame(rf, bg=c['reader_bg'])
        tf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tw = tk.Text(
            tf, wrap=tk.WORD,
            bg=c['reader_bg'], fg=c['reader_fg'],
            font=('Microsoft YaHei', 12),
            borderwidth=0, padx=20, pady=14,
            spacing1=2, spacing2=1, spacing3=8)
        ts = tk.Scrollbar(tf, orient=tk.VERTICAL, command=self.tw.yview)
        self.tw.configure(yscrollcommand=ts.set)
        self.tw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ts.pack(side=tk.RIGHT, fill=tk.Y)

        self.tw.bind('<Key>', lambda e: 'break')
        self.tw.bind('<BackSpace>', lambda e: 'break')
        self.tw.bind('<Delete>', lambda e: 'break')
        self.tw.bind('<Control-v>', lambda e: 'break')
        self.tw.bind('<Control-x>', lambda e: 'break')
        self.tw.bind('<MouseWheel>',
                     lambda e: self.tw.yview_scroll(int(-e.delta / 120), 'units'))

        self.tw.tag_configure('hl', background=c['highlight_bg'],
                              foreground=c['highlight_fg'])
        self.tw.tag_configure('ch', font=('Microsoft YaHei', 18, 'bold'),
                              foreground=c['reader_accent'],
                              spacing1=14, spacing3=18)

    def _make_bg_palette(self, parent, c):
        palette = tk.Frame(parent, bg=c['reader_bg'])
        palette.pack(side=tk.RIGHT, padx=(8, 8), pady=4)
        tk.Label(palette, text='背景 ', bg=c['reader_bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 8)).pack(side=tk.LEFT, padx=(0, 4))

        self._bg_swatches = []
        for i, (name, bg, fg, accent) in enumerate(READER_BG_PRESETS):
            sw = tk.Canvas(palette, width=22, height=22,
                           highlightthickness=0, cursor='hand2')
            sw.pack(side=tk.LEFT, padx=1)
            sw.create_oval(3, 3, 19, 19, fill=bg,
                           outline='#94a3b8' if i == self._bg_idx else '#cbd5e1',
                           width=2 if i == self._bg_idx else 1, tags='swatch')
            sw._tooltip = name
            sw.bind('<Enter>', lambda e, s=sw: self._on_swatch_enter(e, s))
            sw.bind('<Leave>', lambda e, s=sw: self._on_swatch_leave(e, s))
            sw.bind('<Button-1>', lambda e, idx=i: self._on_bg_select(idx))
            self._bg_swatches.append(sw)

    # ── 背景色事件 ──

    def _on_swatch_enter(self, event, sw):
        sw.create_oval(3, 3, 19, 19, outline='#3b82f6', width=2, tags='hover')
        if hasattr(self, '_tooltip_label'):
            self._tooltip_label.destroy()
        self._tooltip_label = tk.Label(
            sw.master, text=sw._tooltip, bg='#1e293b', fg='#ffffff',
            font=('Microsoft YaHei', 8), padx=6, pady=1)
        self._tooltip_label.place(x=sw.winfo_x() - 6, y=sw.winfo_y() - 22)

    def _on_swatch_leave(self, event, sw):
        sw.delete('hover')
        if hasattr(self, '_tooltip_label'):
            self._tooltip_label.destroy()
            self._tooltip_label = None

    def _on_bg_select(self, idx):
        self._bg_idx = idx
        name, bg, fg, accent = READER_BG_PRESETS[idx]
        self._reader_bg = bg
        self._reader_fg = fg
        self._reader_accent = accent
        for i, sw in enumerate(self._bg_swatches):
            outline = '#94a3b8' if i == idx else '#cbd5e1'
            sw.delete('swatch')
            sw.create_oval(3, 3, 19, 19,
                           fill=READER_BG_PRESETS[i][1],
                           outline=outline,
                           width=2 if i == idx else 1, tags='swatch')
        self._apply_reader_bg()
        try:
            self.db.set_setting('reader_bg_idx', str(idx))
        except Exception:
            pass

    def _apply_reader_bg(self):
        bg = self._reader_bg
        self.tw.configure(bg=bg, fg=self._reader_fg)
        self.tw.tag_configure('ch', foreground=self._reader_accent)
        rf = self.tw.master.master
        if rf:
            rf.configure(bg=bg)
            for child in rf.winfo_children():
                if isinstance(child, tk.Frame):
                    try:
                        child.configure(bg=bg)
                        for sub in child.winfo_children():
                            if isinstance(sub, (tk.Label, tk.Frame)):
                                try:
                                    sub.configure(bg=bg)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                elif isinstance(child, tk.Label):
                    try:
                        child.configure(bg=bg)
                    except Exception:
                        pass

    # ═══════════════════════════════════════════════
    #  进度条 — Canvas 绘制，醒目可拖拽
    # ═══════════════════════════════════════════════

    def _make_progress_bar(self, c):
        """Canvas 进度条：轨道 + 填充 + 拖动手柄 + 剩余时间"""
        bar_row = tk.Frame(self, bg=c['bg'], height=32)
        bar_row.pack(fill=tk.X, padx=20, pady=(4, 0))
        bar_row.pack_propagate(False)

        tk.Label(bar_row, text='进度', bg=c['bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=(0, 8))

        self._progress_canvas = tk.Canvas(
            bar_row, height=26, bg=c['bg'],
            highlightthickness=0, bd=0, cursor='hand2')
        self._progress_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._pct_label = tk.Label(bar_row, text='0%', bg=c['bg'], fg=c['fg'],
                                   font=('Microsoft YaHei', 10, 'bold'),
                                   width=5, anchor=tk.E)
        self._pct_label.pack(side=tk.RIGHT, padx=(8, 0))

        self._progress_canvas.bind('<Configure>', self._on_pbar_resize)
        self._progress_canvas.bind('<Button-1>', self._on_pbar_click)
        self._progress_canvas.bind('<B1-Motion>', self._on_pbar_drag)
        self._progress_canvas.bind('<ButtonRelease-1>', self._on_pbar_release)

    def _on_pbar_resize(self, event=None):
        self._bar_w = self._progress_canvas.winfo_width()
        self._bar_h = self._progress_canvas.winfo_height()
        self._draw_progress()

    def _draw_progress(self):
        cv = self._progress_canvas
        c = self.theme.c
        cv.delete('all')
        w, h = self._bar_w, self._bar_h
        if w < 10 or h < 10:
            return

        pct = self._progress_value / 100.0
        fill_w = int(w * pct)

        # 轨道
        ty1, ty2 = 6, h - 6
        cv.create_rectangle(0, ty1, w, ty2, fill=c['progress_bg'],
                            outline='', tags='track')

        # 已读填充
        if fill_w > 0:
            cv.create_rectangle(0, ty1, fill_w, ty2, fill=c['accent'],
                                outline='', tags='fill')

        # 拖动手柄
        thumb_r = 7
        tx = max(thumb_r, min(w - thumb_r, fill_w))
        ty = h // 2
        cv.create_oval(tx - thumb_r, ty - thumb_r,
                       tx + thumb_r, ty + thumb_r,
                       fill='#ffffff', outline=c['accent_hover'],
                       width=2, tags='thumb')

        # 剩余时间
        est = self._estimate_remaining()
        if est:
            cv.create_text(w // 2, 4, text=est, fill=c['fg_muted'],
                           font=('Microsoft YaHei', 7), anchor=tk.N, tags='time')

    def _estimate_remaining(self):
        if not self.novel or self.novel['total_chars'] <= 0:
            return None
        pos = self._get_char_position()
        remaining = self.novel['total_chars'] - pos
        rate = self.rate_v.get()
        cps = max(2.0, rate * 4.5 / 180)
        secs = remaining / cps
        mins, s = int(secs // 60), int(secs % 60)
        if mins > 60:
            h = mins // 60
            m = mins % 60
            return f'剩余约 {h}时{m}分'
        if mins > 0:
            return f'剩余约 {mins}分{s}秒'
        return f'剩余约 {s}秒'

    def _get_char_position(self):
        if not self.novel or not self.chapters:
            return 0
        ch = self.chapters[self.chapter_idx]
        offset = sum(len(self.sentences[i]) for i in range(self.sentence_idx)
                     if i < len(self.sentences))
        return ch['start_pos'] + offset

    def _refresh_progress(self):
        """更新进度条显示（从当前位置计算）"""
        if not self.novel or self.novel['total_chars'] <= 0:
            self._progress_value = 0
            self._pct_label.configure(text='0%')
            self._draw_progress()
            return
        pos = self._get_char_position()
        self._progress_value = pos * 100.0 / self.novel['total_chars']
        self._pct_label.configure(text=f'{int(self._progress_value)}%')
        self._draw_progress()

    def _on_pbar_click(self, event):
        self._update_pbar_from_mouse(event)

    def _on_pbar_drag(self, event):
        self._update_pbar_from_mouse(event)

    def _on_pbar_release(self, event):
        self._update_pbar_from_mouse(event)
        self._seek_to(self._progress_value)

    def _update_pbar_from_mouse(self, event):
        if self._bar_w <= 0:
            return
        pct = max(0.0, min(100.0, event.x / self._bar_w * 100.0))
        self._progress_value = pct
        self._pct_label.configure(text=f'{int(pct)}%')
        self._draw_progress()

    def _seek_to(self, pct):
        """跳转到 pct% 的位置"""
        if not self.novel or not self.chapters:
            return
        was = self.playing
        if was:
            self._pause()

        total = self.novel['total_chars']
        target = int(total * pct / 100.0)
        target = max(0, min(total - 1, target))

        ci = 0
        for i, ch in enumerate(self.chapters):
            if ch['start_pos'] <= target < ch['end_pos']:
                ci = i
                break
        else:
            ci = len(self.chapters) - 1
            target = self.chapters[ci]['end_pos'] - 1

        if ci != self.chapter_idx:
            self.chapter_idx = ci
            self._load_ch(ci)

        chapter = self.chapters[ci]
        rel = target - chapter['start_pos']
        acc = 0
        si = 0
        for i, s in enumerate(self.sentences):
            if acc + len(s) > rel:
                si = i
                break
            acc += len(s)
        else:
            si = len(self.sentences) - 1

        self.sentence_idx = si
        self._hl(si)
        self._refresh_progress()
        self._save()
        if was:
            self._resume()

    # ═══════════════════════════════════════════════
    #  控制栏
    # ═══════════════════════════════════════════════

    def _make_control_bar(self, c):
        ctrl = tk.Frame(self, bg=c['surface'])
        ctrl.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(6, 12))
        inner = tk.Frame(ctrl, bg=c['surface'])
        inner.pack(padx=16, pady=10)

        btn_row = tk.Frame(inner, bg=c['surface'])
        btn_row.pack()

        nav = {'bg': c['surface'], 'fg': c['fg'],
               'activebackground': c['accent'], 'activeforeground': c['accent_text'],
               'font': ('Segoe UI', 14), 'relief': tk.FLAT,
               'padx': 6, 'pady': 4, 'borderwidth': 0, 'cursor': 'hand2'}

        tk.Button(btn_row, text='⏮', command=self._prev_ch, **nav).pack(side=tk.LEFT, padx=1)
        tk.Button(btn_row, text='⏪', command=self._prev_s, **nav).pack(side=tk.LEFT, padx=1)

        self._play_canvas = tk.Canvas(btn_row, width=52, height=52,
                                      bg=c['surface'],
                                      highlightthickness=0, cursor='hand2')
        self._play_canvas.pack(side=tk.LEFT, padx=10)
        self._draw_play_icon()
        self._play_canvas.bind('<Button-1>', lambda e: self._toggle())

        tk.Button(btn_row, text='⏹', command=self._stop, **nav).pack(side=tk.LEFT, padx=1)
        tk.Button(btn_row, text='⏩', command=self._next_s, **nav).pack(side=tk.LEFT, padx=1)
        tk.Button(btn_row, text='⏭', command=self._next_ch, **nav).pack(side=tk.LEFT, padx=1)

        slider_row = tk.Frame(inner, bg=c['surface'])
        slider_row.pack(pady=(10, 2))
        ls = {'bg': c['surface'], 'fg': c['fg_secondary'],
              'font': ('Microsoft YaHei', 9)}

        tk.Label(slider_row, text='语速', **ls).pack(side=tk.LEFT, padx=(0, 4))
        self.rate_v = tk.IntVar(value=180)
        tk.Scale(slider_row, from_=50, to=350, variable=self.rate_v,
                 orient=tk.HORIZONTAL, bg=c['surface'], fg=c['fg'],
                 highlightthickness=0, length=120, troughcolor=c['progress_bg'],
                 command=lambda v: self.tts.set_rate(int(v))
                 ).pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(slider_row, text=' 音量', **ls).pack(side=tk.LEFT, padx=(0, 4))
        self.vol_v = tk.IntVar(value=100)
        tk.Scale(slider_row, from_=0, to=100, variable=self.vol_v,
                 orient=tk.HORIZONTAL, bg=c['surface'], fg=c['fg'],
                 highlightthickness=0, length=120, troughcolor=c['progress_bg'],
                 command=lambda v: self.tts.set_volume(int(v) / 100.0)
                 ).pack(side=tk.LEFT)

    def _draw_play_icon(self):
        c = self.theme.c
        cv = self._play_canvas
        cv.delete('all')
        cv.create_oval(2, 2, 50, 50,
                       fill=c['accent'],
                       outline=c['accent_hover'], width=2,
                       tags='circle')
        if self.playing:
            cv.create_rectangle(17, 14, 22, 38, fill='#ffffff', tags='icon', outline='')
            cv.create_rectangle(29, 14, 34, 38, fill='#ffffff', tags='icon', outline='')
        else:
            cv.create_polygon(18, 13, 18, 39, 38, 26,
                              fill='#ffffff', tags='icon', outline='')

    def _update_play_button(self):
        self._draw_play_icon()

    # ═══════════════════════════════════════════════
    #  加载小说
    # ═══════════════════════════════════════════════

    def open_novel(self, nid):
        n = self.db.get_novel(nid)
        if not n:
            messagebox.showerror('错误', '小说不存在')
            return
        self.novel_id = nid
        self.novel = n
        self.current_novel = n
        self.current_novel_id = nid
        self.title_var.set(n['title'])

        self.chapters = self.db.get_chapters(nid)
        if not self.chapters:
            from chapter_parser import detect_chapters
            chs = detect_chapters(n['content'])
            self.db.add_chapters_batch(
                [(nid, i, c[1], c[2], c[3]) for i, c in enumerate(chs)])
            self.chapters = self.db.get_chapters(nid)

        self._all_chapters = list(self.chapters)
        self._refresh_ch()

        prog = self.db.get_progress(nid)
        ci, si = 0, 0
        if prog and prog['chapter_id']:
            for i, ch in enumerate(self.chapters):
                if ch['id'] == prog['chapter_id']:
                    ci = i
                    break
        self.chapter_idx = ci
        self._load_ch(ci)

        if prog and prog['char_position']:
            chapter = self.chapters[ci]
            rel = prog['char_position'] - chapter['start_pos']
            acc = 0
            for i, s in enumerate(self.sentences):
                if acc <= rel < acc + len(s):
                    si = i
                    break
                acc += len(s)
        self.sentence_idx = si
        if self.sentences:
            self._hl(si)

        p = self.db.get_default_voice_profile()
        if p:
            if p['voice_id']:
                self.tts.set_voice(p['voice_id'])
            if p['rate']:
                self.tts.set_rate(p['rate'])
                self.rate_v.set(p['rate'])
            if p['volume'] is not None:
                self.tts.set_volume(p['volume'])
                self.vol_v.set(int(p['volume'] * 100))

        try:
            saved = self.db.get_setting('reader_bg_idx', '0')
            bg_idx = int(saved)
            if 0 <= bg_idx < len(READER_BG_PRESETS):
                self._on_bg_select(bg_idx)
        except Exception:
            pass

        self._refresh_progress()
        self.db.update_last_read(nid)

    def _refresh_ch(self):
        self.ch_lb.delete(0, tk.END)
        for ch in self.chapters:
            self.ch_lb.insert(tk.END, ch['title'])

    def _filter_chapters(self):
        kw = self.ch_search_var.get().strip()
        self.ch_lb.delete(0, tk.END)
        if not kw:
            for ch in self.chapters:
                self.ch_lb.insert(tk.END, ch['title'])
        else:
            for ch in self.chapters:
                if kw.lower() in ch['title'].lower():
                    self.ch_lb.insert(tk.END, ch['title'])

    def _load_ch(self, idx):
        if not self.novel or not self.chapters:
            return
        self.chapter_idx = max(0, min(idx, len(self.chapters) - 1))
        ch = self.chapters[self.chapter_idx]
        self.cht_var.set(ch['title'])
        text = self.novel['content'][ch['start_pos']:ch['end_pos']]
        self.sentences = split_sentences(text)
        self._render(text, ch['title'])
        self.ch_lb.selection_clear(0, tk.END)
        self.ch_lb.selection_set(self.chapter_idx)
        self.ch_lb.see(self.chapter_idx)
        total = self.novel['total_chars']
        pct = ch['start_pos'] * 100 // total if total > 0 else 0
        self.prog_var.set(
            f'第 {self.chapter_idx + 1}/{len(self.chapters)} 章  ·  进度 {pct}%  ·  {len(self.sentences)} 句')

    # ═══════════════════════════════════════════════
    #  渲染（字符偏移映射）
    # ═══════════════════════════════════════════════

    def _render(self, text, title):
        self._stags = []
        tw = self.tw
        tw.delete('1.0', tk.END)
        tw.insert(tk.END, title + '\n\n', 'ch')
        body_start = tw.index('end-1c')

        for p in text.split('\n'):
            ps = p.strip()
            tw.insert(tk.END, (ps + '\n') if ps else '\n')

        body_text = tw.get(body_start, 'end-1c')
        cursor = 0
        for i, s in enumerate(self.sentences):
            s_stripped = s.strip()
            if not s_stripped:
                self._stags.append(('1.0', '1.0'))
                continue
            found = body_text.find(s, cursor)
            if found < 0:
                found = body_text.find(s_stripped, cursor)
            if found < 0:
                self._stags.append(('1.0', '1.0'))
                continue
            start = tw.index(f'{body_start}+{found}c')
            end = tw.index(f'{body_start}+{found + len(s_stripped)}c')
            tw.tag_add(f's{i}', start, end)
            self._stags.append((start, end))
            cursor = found + len(s_stripped)
        tw.see('1.0')

    def _hl(self, idx):
        if not self._stags:
            return
        self.tw.tag_remove('hl', '1.0', tk.END)
        if 0 <= idx < len(self._stags):
            s, e = self._stags[idx]
            if s == '1.0' and e == '1.0':
                return
            self.tw.tag_add('hl', s, e)
            line = int(s.split('.')[0])
            total = max(1, int(self.tw.index('end-1c').split('.')[0]))
            frac = max(0.0, min(1.0, (line - 2) / total))
            self.tw.yview_moveto(frac)

    # ═══════════════════════════════════════════════
    #  播放（高亮仅由音频回调驱动）
    # ═══════════════════════════════════════════════

    def _toggle(self):
        if self.playing:
            self._pause()
        else:
            self._play()

    def _toggle_play(self):
        self._toggle()

    def _play(self):
        if not self.sentences:
            messagebox.showinfo('提示', '没有内容')
            return
        self.playing = True
        self._update_play_button()
        self._abort_pre_gen()
        self._play_batch()

    def _pause(self):
        self.playing = False
        self._abort_pre_gen()
        self.tts.stop()
        self._update_play_button()
        self._save()

    def _stop(self):
        self.playing = False
        self._abort_pre_gen()
        self.tts.stop()
        self.sentence_idx = 0
        self._update_play_button()
        if self._stags:
            self._hl(0)
        self._refresh_progress()
        self._save()

    # ── 批次 ──

    def _make_batch(self, start):
        batch = []
        total = 0
        idx = start
        while idx < len(self.sentences) and total < self.BATCH_CHARS:
            batch.append((idx, self.sentences[idx]))
            total += len(self.sentences[idx])
            idx += 1
        return batch

    def _play_batch(self):
        if not self.playing:
            return

        if self.sentence_idx >= len(self.sentences):
            if self.chapter_idx + 1 < len(self.chapters):
                self.chapter_idx += 1
                self.sentence_idx = 0
                self._load_ch(self.chapter_idx)
                self.update_idletasks()
                self._abort_pre_gen()
                self.after(200, self._play_batch)
            else:
                self._stop()
                messagebox.showinfo('播放完毕', '已读完所有章节！')
            return

        batch = self._make_batch(self.sentence_idx)
        if not batch:
            return
        self._batch_n = len(batch)

        self._hl(batch[0][0])
        self._save_safe()
        self._start_pre_gen(batch)

        if self._try_use_pre_gen():
            pass
        else:
            sentences = [s for _, s in batch]
            self.tts.speak_sentences(sentences, callback=self._on_done)

    # ── 预生成 ──

    def _try_use_pre_gen(self):
        if (self._pre_gen_mp3 and
                self._pre_gen_start_idx == self.sentence_idx):
            mp3 = self._pre_gen_mp3
            self._pre_gen_mp3 = None
            self._pre_gen_start_idx = -1
            self.tts.play(mp3, callback=self._on_done)
            return True
        return False

    def _start_pre_gen(self, current_batch):
        next_start = self.sentence_idx + len(current_batch)
        if next_start >= len(self.sentences):
            return
        next_batch = self._make_batch(next_start)
        if not next_batch:
            return
        sentences = [s for _, s in next_batch]
        self._pre_gen_token += 1
        token = self._pre_gen_token

        def on_ready(mp3_path):
            if self._pre_gen_token != token or not self.playing:
                if mp3_path:
                    try:
                        os.remove(mp3_path)
                    except Exception:
                        pass
                return
            if self._pre_gen_mp3 and self._pre_gen_start_idx != next_start:
                try:
                    if os.path.exists(self._pre_gen_mp3):
                        os.remove(self._pre_gen_mp3)
                except Exception:
                    pass
            self._pre_gen_mp3 = mp3_path
            self._pre_gen_start_idx = next_start

        self._pre_gen_mp3 = None
        self._pre_gen_start_idx = next_start
        self.tts.generate_sentences_async(sentences, on_ready)

    def _abort_pre_gen(self):
        self._pre_gen_token += 1
        if self._pre_gen_mp3:
            try:
                if os.path.exists(self._pre_gen_mp3):
                    os.remove(self._pre_gen_mp3)
            except Exception:
                pass
        self._pre_gen_mp3 = None
        self._pre_gen_start_idx = -1

    # ── 回调 ──

    def _on_done(self):
        """音频播完 → 推进句子 → 更新进度条"""
        if not self.playing:
            self._abort_pre_gen()
            return
        try:
            self.sentence_idx += self._batch_n
            self._save_safe()
            self._refresh_progress()
            self.after(30, self._play_batch)
        except Exception:
            try:
                self.after(30, self._play_batch)
            except Exception:
                pass

    def _save_safe(self):
        try:
            self._save()
        except Exception:
            pass

    # ── 导航 ──

    def _next_s(self):
        w = self.playing
        self._pause()
        if self.sentences and self.sentence_idx + 1 < len(self.sentences):
            self.sentence_idx += 1
            self._hl(self.sentence_idx)
        elif self.chapter_idx + 1 < len(self.chapters):
            self.chapter_idx += 1
            self.sentence_idx = 0
            self._load_ch(self.chapter_idx)
        self._refresh_progress()
        self._save()
        if w:
            self._resume()

    def _prev_s(self):
        w = self.playing
        self._pause()
        if self.sentence_idx > 0:
            self.sentence_idx -= 1
            self._hl(self.sentence_idx)
        elif self.chapter_idx > 0:
            self.chapter_idx -= 1
            self._load_ch(self.chapter_idx)
            self.sentence_idx = max(0, len(self.sentences) - 1)
            if self.sentences:
                self._hl(self.sentence_idx)
        self._refresh_progress()
        self._save()
        if w:
            self._resume()

    def _next_ch(self):
        w = self.playing
        self._pause()
        if self.chapter_idx + 1 < len(self.chapters):
            self.chapter_idx += 1
            self.sentence_idx = 0
            self._load_ch(self.chapter_idx)
        self._refresh_progress()
        self._save()
        if w:
            self._resume()

    def _prev_ch(self):
        w = self.playing
        self._pause()
        if self.chapter_idx > 0:
            self.chapter_idx -= 1
            self.sentence_idx = 0
            self._load_ch(self.chapter_idx)
        self._refresh_progress()
        self._save()
        if w:
            self._resume()

    def _on_ch(self, event):
        sel = self.ch_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx != self.chapter_idx:
            w = self.playing
            self._pause()
            self.chapter_idx = idx
            self.sentence_idx = 0
            self._load_ch(idx)
            self._refresh_progress()
            self._save()
            if w:
                self._resume()

    def _resume(self):
        self.playing = True
        self._update_play_button()
        self._abort_pre_gen()
        self.after(100, self._play_batch)

    # ═══════════════════════════════════════════════
    #  语音设置弹窗
    # ═══════════════════════════════════════════════

    def _show_voice_dlg(self):
        c = self.theme.c
        win = tk.Toplevel(self)
        win.title('语音设置')
        win.geometry('420x380')
        win.transient(self)
        win.grab_set()
        win.configure(bg=c['bg'])
        win.resizable(False, False)

        tk.Label(win, text='🔊  语音设置', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 14, 'bold')).pack(pady=(16, 12))

        card = tk.Frame(win, bg=c['card_bg'],
                        highlightbackground=c['card_border'],
                        highlightthickness=1)
        card.pack(fill=tk.X, padx=20, pady=(0, 12))
        inner = tk.Frame(card, bg=c['card_bg'])
        inner.pack(fill=tk.X, padx=16, pady=14)

        # 语音选择
        tk.Label(inner, text='朗读语音', bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(anchor=tk.W)
        combo_row = tk.Frame(inner, bg=c['card_bg'])
        combo_row.pack(fill=tk.X, pady=(4, 0))

        self._dlg_voice_var = tk.StringVar()
        self._dlg_voice_combo = ttk.Combobox(
            combo_row, textvariable=self._dlg_voice_var,
            font=('Microsoft YaHei', 10), state='readonly')
        self._dlg_voice_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self._dlg_voice_combo.bind('<<ComboboxSelected>>',
                                   lambda e: self._on_dlg_voice_select())

        tk.Button(combo_row, text='🔊 试听', command=self._dlg_test_voice,
                  bg=c['accent'], fg=c['accent_text'],
                  activebackground=c['accent_hover'],
                  activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 9), relief=tk.FLAT,
                  padx=10, pady=3, borderwidth=0, cursor='hand2'
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # 语速
        tk.Label(inner, text='语速', bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(anchor=tk.W, pady=(12, 0))
        rate_row = tk.Frame(inner, bg=c['card_bg'])
        rate_row.pack(fill=tk.X, pady=(2, 0))
        self._dlg_rate_v = tk.IntVar(value=self.rate_v.get())
        self._dlg_rate_lbl = tk.Label(rate_row, text=str(self.rate_v.get()),
                                      bg=c['card_bg'], fg=c['fg'],
                                      font=('Microsoft YaHei', 9), width=4, anchor=tk.E)
        self._dlg_rate_lbl.pack(side=tk.RIGHT)
        tk.Scale(rate_row, from_=50, to=350, variable=self._dlg_rate_v,
                 orient=tk.HORIZONTAL, bg=c['card_bg'], fg=c['fg'],
                 highlightthickness=0, length=280, troughcolor=c['progress_bg'],
                 command=lambda v: (self._dlg_rate_lbl.configure(text=str(int(float(v)))),
                                    self.tts.set_rate(int(float(v))))
                 ).pack(side=tk.LEFT)

        # 音量
        tk.Label(inner, text='音量', bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(anchor=tk.W, pady=(10, 0))
        vol_row = tk.Frame(inner, bg=c['card_bg'])
        vol_row.pack(fill=tk.X, pady=(2, 0))
        self._dlg_vol_v = tk.IntVar(value=self.vol_v.get())
        self._dlg_vol_lbl = tk.Label(vol_row, text=f'{self.vol_v.get()}%',
                                     bg=c['card_bg'], fg=c['fg'],
                                     font=('Microsoft YaHei', 9), width=4, anchor=tk.E)
        self._dlg_vol_lbl.pack(side=tk.RIGHT)
        tk.Scale(vol_row, from_=0, to=100, variable=self._dlg_vol_v,
                 orient=tk.HORIZONTAL, bg=c['card_bg'], fg=c['fg'],
                 highlightthickness=0, length=280, troughcolor=c['progress_bg'],
                 command=lambda v: (self._dlg_vol_lbl.configure(text=f'{int(float(v))}%'),
                                    self.tts.set_volume(int(float(v)) / 100.0))
                 ).pack(side=tk.LEFT)

        # 按钮
        btn_row = tk.Frame(win, bg=c['bg'])
        btn_row.pack(pady=(0, 16))
        tk.Button(btn_row, text='💾  保存为默认', command=self._dlg_save,
                  bg=c['accent'], fg=c['accent_text'],
                  activebackground=c['accent_hover'],
                  activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 11, 'bold'), relief=tk.FLAT,
                  padx=20, pady=8, borderwidth=0, cursor='hand2'
                  ).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text='关闭', command=win.destroy,
                  bg=c['card_bg'], fg=c['fg'],
                  activebackground=c['accent'], activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 11), relief=tk.FLAT,
                  padx=20, pady=8, borderwidth=0, cursor='hand2',
                  highlightbackground=c['card_border'], highlightthickness=1
                  ).pack(side=tk.LEFT, padx=4)

        self._load_dlg_voices()
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 420) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 380) // 2
        win.geometry(f'+{x}+{y}')

    def _load_dlg_voices(self):
        voices = self.tts.list_voices()
        self._dlg_voices = voices
        names = []
        for v in voices:
            if v.get('source') == 'sep':
                names.append(v['name'])
            else:
                tag = ' [在线]' if v.get('source') == 'edge' else ' [系统]'
                names.append(f"{v['name']}{tag}")
        self._dlg_voice_combo['values'] = names
        p = self.db.get_default_voice_profile()
        if p and p['voice_id']:
            for i, v in enumerate(voices):
                if v.get('source') == 'sep':
                    continue
                if v['id'] == p['voice_id']:
                    self._dlg_voice_combo.current(i)
                    break

    def _on_dlg_voice_select(self):
        idx = self._dlg_voice_combo.current()
        if 0 <= idx < len(self._dlg_voices):
            v = self._dlg_voices[idx]
            if v.get('source') != 'sep':
                self.tts.set_voice(v['id'])

    def _dlg_test_voice(self):
        idx = self._dlg_voice_combo.current()
        if 0 <= idx < len(self._dlg_voices):
            v = self._dlg_voices[idx]
            if v.get('source') != 'sep':
                self.tts.set_voice(v['id'])
        self.tts.set_rate(self._dlg_rate_v.get())
        self.tts.set_volume(self._dlg_vol_v.get() / 100.0)
        self.tts.speak('你好，这是小说播放器的语音测试。可以听到我的声音吗？')

    def _dlg_save(self):
        idx = self._dlg_voice_combo.current()
        voice_id = ''
        if 0 <= idx < len(self._dlg_voices):
            v = self._dlg_voices[idx]
            if v.get('source') != 'sep':
                voice_id = v['id']
        rate = self._dlg_rate_v.get()
        vol = self._dlg_vol_v.get() / 100.0

        if voice_id:
            self.tts.set_voice(voice_id)
        self.tts.set_rate(rate)
        self.tts.set_volume(vol)
        self.rate_v.set(rate)
        self.vol_v.set(int(vol * 100))

        p = self.db.get_default_voice_profile()
        if p:
            self.db.update_voice_profile(p['id'],
                                         voice_id=voice_id, rate=rate, volume=vol)
        else:
            self.db.add_voice_profile(name='默认', voice_id=voice_id,
                                      rate=rate, volume=vol, is_default=1)
        messagebox.showinfo('成功', '语音方案已保存为默认')

    # ═══════════════════════════════════════════════
    #  书签
    # ═══════════════════════════════════════════════

    def _add_bm(self):
        if not self.novel:
            return
        note = simpledialog.askstring('添加书签', '备注（可选）:', parent=self)
        ch = self.chapters[self.chapter_idx]
        pos = ch['start_pos'] + sum(
            len(self.sentences[i]) for i in range(self.sentence_idx))
        self.db.add_bookmark(self.novel_id, ch['id'], pos, note or '')
        messagebox.showinfo('成功', '书签已添加')

    def _show_bms(self):
        if not self.novel:
            return
        bms = self.db.get_bookmarks(self.novel_id)
        if not bms:
            messagebox.showinfo('书签', '暂无书签')
            return
        self._show_bookmark_window(bms)

    def _show_bookmark_window(self, bms):
        c = self.theme.c
        win = tk.Toplevel(self)
        win.title('书签列表')
        win.geometry('480x380')
        win.transient(self)
        win.grab_set()
        win.configure(bg=c['bg'])

        tk.Label(win, text='🔖 书签列表', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 14, 'bold')).pack(pady=(16, 8))

        lf = tk.Frame(win, bg=c['bg'])
        lf.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        sb = tk.Scrollbar(lf)
        lb = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=c['input_bg'], fg=c['fg'],
            font=('Microsoft YaHei', 11),
            selectbackground=c['select_bg'],
            selectforeground=c['select_fg'],
            borderwidth=0, highlightthickness=1,
            highlightbackground=c['card_border'])
        sb.config(command=lb.yview)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for bm in bms:
            ct = bm['chapter_title'] or f'第{bm["chapter_id"]}章'
            lb.insert(tk.END, f'{ct}  —  {bm["note"] or "(无备注)"}')

        def jump():
            sel = lb.curselection()
            if not sel:
                return
            bm = bms[sel[0]]
            for i, ch in enumerate(self.chapters):
                if ch['id'] == bm['chapter_id']:
                    self.chapter_idx = i
                    self._load_ch(i)
                    rel = bm['char_position'] - self.chapters[i]['start_pos']
                    acc = 0
                    for j, s in enumerate(self.sentences):
                        if acc <= rel < acc + len(s):
                            self.sentence_idx = j
                            self._hl(j)
                            break
                        acc += len(s)
                    break
            self._refresh_progress()
            win.destroy()

        def rm():
            sel = lb.curselection()
            if not sel:
                return
            i = sel[0]
            self.db.delete_bookmark(bms[i]['id'])
            lb.delete(i)
            del bms[i]

        bf = tk.Frame(win, bg=c['bg'])
        bf.pack(fill=tk.X, padx=16, pady=12)
        tk.Button(bf, text='跳转', bg=c['accent'], fg=c['accent_text'],
                  font=('Microsoft YaHei', 10), relief=tk.FLAT,
                  padx=18, pady=6, cursor='hand2',
                  command=jump).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text='删除', bg=c['danger'], fg='#ffffff',
                  font=('Microsoft YaHei', 10), relief=tk.FLAT,
                  padx=18, pady=6, cursor='hand2',
                  command=rm).pack(side=tk.RIGHT, padx=5)
        lb.bind('<Double-1>', lambda e: jump())

    # ═══════════════════════════════════════════════
    #  辅助
    # ═══════════════════════════════════════════════

    def _save(self):
        if not self.novel or not self.chapters:
            return
        ch = self.chapters[self.chapter_idx]
        pos = ch['start_pos'] + sum(
            len(self.sentences[i]) for i in range(self.sentence_idx)
            if i < len(self.sentences))
        self.db.save_progress(self.novel_id, ch['id'], pos)

    def _go_back(self):
        self.playing = False
        self._abort_pre_gen()
        self.tts.stop()
        self._save()
        if self.on_back:
            self.on_back()

    def cleanup(self):
        self.playing = False
        self._abort_pre_gen()
        self.tts.stop()
        self._save()
