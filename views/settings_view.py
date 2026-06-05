"""
设置视图 — 现代化设置面板
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class SettingsView(ttk.Frame):
    def __init__(self, parent, db_manager, tts_engine, theme_manager,
                 on_theme_toggle=None):
        super().__init__(parent)
        self.db = db_manager
        self.tts = tts_engine
        self.theme = theme_manager
        self.on_theme_toggle = on_theme_toggle

        self.current_profile_id = None
        self.voices = []

        self._setup_ui()
        self._load_voices()
        self._refresh_profiles()

    # ═══════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════

    def _setup_ui(self):
        c = self.theme.c

        # 标题
        header = tk.Frame(self, bg=c['bg'])
        header.pack(fill=tk.X, padx=24, pady=(20, 0))

        tk.Label(header, text='设置', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 20, 'bold')).pack(side=tk.LEFT)

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=24, pady=(14, 20))

        self._create_voice_tab(c)
        self._create_appearance_tab(c)
        self._create_about_tab(c)

    def _create_voice_tab(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='  语音配置  ')

        # ── 左右分栏 ──
        left = tk.Frame(tab, bg=c['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 8), pady=16)

        right = tk.Frame(tab, bg=c['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 16), pady=16)

        # ── 左栏：方案列表 ──
        tk.Label(left, text='语音方案', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 8))

        # 方案列表
        lf = tk.Frame(left, bg=c['bg'])
        lf.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(lf)
        self.profile_listbox = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=c['input_bg'], fg=c['fg'],
            font=('Microsoft YaHei', 11),
            selectbackground=c['select_bg'],
            selectforeground=c['select_fg'],
            borderwidth=0, highlightthickness=1,
            highlightbackground=c['card_border'],
            height=7)
        sb.config(command=self.profile_listbox.yview)
        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_listbox.bind('<<ListboxSelect>>', self._on_profile_select)

        # 方案操作按钮
        btn_frame = tk.Frame(left, bg=c['bg'])
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        for text, cmd in [('➕ 新建', self._add_profile),
                           ('⭐ 设为默认', self._set_default_profile),
                           ('🗑️ 删除', self._delete_profile)]:
            bg = c['accent'] if '新建' in text else c['card_bg']
            fg = c['accent_text'] if '新建' in text else c['fg']
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=bg, fg=fg,
                      activebackground=c['accent'],
                      activeforeground=c['accent_text'],
                      font=('Microsoft YaHei', 9), relief=tk.FLAT,
                      padx=10, pady=4, borderwidth=0, cursor='hand2').pack(
                side=tk.LEFT, padx=2)

        # ── 右栏：详细配置 ──
        tk.Label(right, text='方案配置', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 8))

        # 卡片
        card = tk.Frame(right, bg=c['card_bg'],
                        highlightbackground=c['card_border'],
                        highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(card, bg=c['card_bg'])
        inner.pack(fill=tk.X, padx=16, pady=14)

        # 方案名称
        self._make_field(inner, card, c, '方案名称')
        row1 = tk.Frame(inner, bg=c['card_bg'])
        row1.pack(fill=tk.X, pady=(0, 10))
        tk.Label(row1, text='方案名称', bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(anchor=tk.W)
        self.profile_name_var = tk.StringVar()
        self.profile_name_var.trace_add('write', lambda *a: self._on_profile_name_change())
        name_frame = tk.Frame(row1, bg=c['input_border'], padx=1, pady=1)
        name_frame.pack(fill=tk.X, pady=(4, 0))
        self.profile_name_entry = tk.Entry(
            name_frame, textvariable=self.profile_name_var,
            bg=c['input_bg'], fg=c['fg'],
            font=('Microsoft YaHei', 11),
            relief=tk.FLAT, borderwidth=0,
            insertbackground=c['fg'])
        self.profile_name_entry.pack(fill=tk.X, ipady=5, padx=10)
        self.profile_name_entry.bind('<FocusIn>', lambda e: name_frame.configure(bg=c['input_focus']))
        self.profile_name_entry.bind('<FocusOut>', lambda e: name_frame.configure(bg=c['input_border']))

        # 语音选择
        self._make_section(inner, card, c, '朗读语音')
        row2 = tk.Frame(inner, bg=c['card_bg'])
        row2.pack(fill=tk.X, pady=(0, 10))
        tk.Label(row2, text='朗读语音', bg=c['card_bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 9)).pack(anchor=tk.W)
        combo_row = tk.Frame(row2, bg=c['card_bg'])
        combo_row.pack(fill=tk.X, pady=(4, 0))

        self.voice_var = tk.StringVar()
        self.voice_combo = ttk.Combobox(
            combo_row, textvariable=self.voice_var,
            font=('Microsoft YaHei', 10),
            state='readonly')
        self.voice_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self.voice_combo.bind('<<ComboboxSelected>>', self._on_voice_select)

        tk.Button(combo_row, text='🔊 试听', command=self._test_voice,
                  bg=c['accent'], fg=c['accent_text'],
                  activebackground=c['accent_hover'],
                  activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 9), relief=tk.FLAT,
                  padx=10, pady=3, borderwidth=0, cursor='hand2'
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        # 语速
        self._make_section(inner, card, c, '朗读语速')
        self.rate_val_var = tk.IntVar(value=180)
        self.rate_label = tk.Label(inner, text='180', bg=c['card_bg'], fg=c['fg'],
                                    font=('Microsoft YaHei', 9))
        tk.Scale(inner, from_=50, to=400,
                 variable=self.rate_val_var, orient=tk.HORIZONTAL,
                 bg=c['card_bg'], fg=c['fg'],
                 highlightthickness=0, length=260, troughcolor=c['progress_bg'],
                 command=lambda v: (self.rate_label.configure(text=str(int(float(v)))),
                                     self.tts.set_rate(int(float(v))))
                 ).pack(fill=tk.X)
        self.rate_label.pack(anchor=tk.E, pady=(0, 8))

        # 音量
        self._make_section(inner, card, c, '朗读音量')
        self.vol_val_var = tk.DoubleVar(value=100)
        self.vol_label = tk.Label(inner, text='100%', bg=c['card_bg'], fg=c['fg'],
                                   font=('Microsoft YaHei', 9))
        tk.Scale(inner, from_=0, to=100,
                 variable=self.vol_val_var, orient=tk.HORIZONTAL,
                 bg=c['card_bg'], fg=c['fg'],
                 highlightthickness=0, length=260, troughcolor=c['progress_bg'],
                 command=lambda v: (self.vol_label.configure(text=f'{int(float(v))}%'),
                                     self.tts.set_volume(int(float(v)) / 100.0))
                 ).pack(fill=tk.X)
        self.vol_label.pack(anchor=tk.E, pady=(0, 8))

        # 保存
        tk.Button(inner, text='💾  保存当前方案', command=self._save_current_profile,
                  bg=c['accent'], fg=c['accent_text'],
                  activebackground=c['accent_hover'],
                  activeforeground=c['accent_text'],
                  font=('Microsoft YaHei', 11, 'bold'), relief=tk.FLAT,
                  padx=20, pady=10, borderwidth=0, cursor='hand2'
                  ).pack(pady=(8, 0))

    def _make_field(self, parent, card, c, label):
        pass  # 保留兼容

    def _make_section(self, parent, card, c, label):
        pass  # 保留兼容

    def _create_appearance_tab(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='  外观设置  ')

        content = tk.Frame(tab, bg=c['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        tk.Label(content, text='主题模式', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 13, 'bold')).pack(anchor=tk.W, pady=(0, 12))

        # 主题卡片
        card = tk.Frame(content, bg=c['card_bg'],
                        highlightbackground=c['card_border'],
                        highlightthickness=1)
        card.pack(fill=tk.X)

        card_inner = tk.Frame(card, bg=c['card_bg'])
        card_inner.pack(fill=tk.X, padx=20, pady=16)

        self.theme_var = tk.StringVar(value=self.theme.current_theme)

        for val, icon, label, desc in [
            ('light', '☀️', '亮色模式', '清新明亮，适合白天阅读'),
            ('dark', '🌙', '暗色模式', '护眼舒适，适合夜间阅读'),
        ]:
            row = tk.Frame(card_inner, bg=c['card_bg'])
            row.pack(fill=tk.X, pady=4)

            rb = tk.Radiobutton(
                row, text=f'{icon}  {label}', variable=self.theme_var,
                value=val, bg=c['card_bg'], fg=c['fg'],
                font=('Microsoft YaHei', 12),
                selectcolor=c['input_bg'],
                activebackground=c['card_bg'],
                activeforeground=c['fg'],
                command=self._on_theme_change)
            rb.pack(anchor=tk.W)

            tk.Label(row, text=f'    {desc}', bg=c['card_bg'], fg=c['fg_muted'],
                     font=('Microsoft YaHei', 9)).pack(anchor=tk.W, padx=(28, 0))

    def _create_about_tab(self, c):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='  关于  ')

        content = tk.Frame(tab, bg=c['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        tk.Label(content, text='📚', bg=c['bg'], fg=c['fg'],
                 font=('Segoe UI', 48)).pack(pady=(20, 8))

        tk.Label(content, text='小说播放器', bg=c['bg'], fg=c['fg'],
                 font=('Microsoft YaHei', 18, 'bold')).pack()

        tk.Label(content, text='v2.0.0', bg=c['bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 10)).pack(pady=(2, 16))

        desc = ('支持导入 TXT 小说、章节自动识别、\n'
                '多语音方案切换、书签管理等功能\n'
                '使用 Windows 系统语音 + 在线 AI 语音')
        tk.Label(content, text=desc, bg=c['bg'], fg=c['fg_secondary'],
                 font=('Microsoft YaHei', 10),
                 justify=tk.CENTER).pack()

        shortcuts = ('\n快捷键:\n'
                     '  Ctrl+I   导入小说\n'
                     '  Space    播放/暂停\n'
                     '  →/←     下一句/上一句\n'
                     '  Ctrl+B   添加书签\n'
                     '  Esc      返回书架')
        tk.Label(content, text=shortcuts, bg=c['bg'], fg=c['fg_muted'],
                 font=('Microsoft YaHei', 9),
                 justify=tk.LEFT).pack(pady=(20, 0))

    # ═══════════════════════════════════════════════
    #  语音管理
    # ═══════════════════════════════════════════════

    def _load_voices(self):
        self.voices = self.tts.list_voices()
        voice_names = []
        for v in self.voices:
            if v.get('source') == 'sep':
                voice_names.append(v['name'])
            else:
                tag = ' [在线]' if v.get('source') == 'edge' else ' [系统]'
                voice_names.append(f"{v['name']}{tag}")
        self.voice_combo['values'] = voice_names

    def _refresh_profiles(self):
        self.profile_listbox.delete(0, tk.END)
        profiles = self.db.get_all_voice_profiles()

        for p in profiles:
            mark = ' ⭐' if p['is_default'] else ''
            self.profile_listbox.insert(tk.END, f"{p['name']}{mark}")

        if profiles:
            self.profile_listbox.selection_set(0)
            self._on_profile_select(None)

    def _on_profile_select(self, event):
        sel = self.profile_listbox.curselection()
        if not sel:
            return

        profiles = self.db.get_all_voice_profiles()
        idx = sel[0]
        if idx >= len(profiles):
            return

        p = profiles[idx]
        self.current_profile_id = p['id']
        self.profile_name_var.set(p['name'])
        self.rate_val_var.set(p['rate'] or 180)
        self.rate_label.configure(text=str(p['rate'] or 180))

        vol_pct = int((p['volume'] or 1.0) * 100)
        self.vol_val_var.set(vol_pct)
        self.vol_label.configure(text=f'{vol_pct}%')

        if p['voice_id']:
            for i, v in enumerate(self.voices):
                if v.get('source') == 'sep':
                    continue
                if v['id'] == p['voice_id']:
                    self.voice_combo.current(i)
                    break

    def _add_profile(self):
        name = simpledialog.askstring('新建方案', '请输入方案名称:', parent=self)
        if not name:
            return

        vid = self.voices[0]['id'] if self.voices else ''
        self.db.add_voice_profile(name=name, voice_id=vid, rate=180, volume=1.0)
        self._refresh_profiles()

    def _set_default_profile(self):
        if not self.current_profile_id:
            return
        self.db.update_voice_profile(self.current_profile_id, is_default=1)
        self._refresh_profiles()

    def _delete_profile(self):
        if not self.current_profile_id:
            return

        profiles = self.db.get_all_voice_profiles()
        if len(profiles) <= 1:
            messagebox.showwarning('提示', '至少保留一个语音方案')
            return

        if messagebox.askyesno('确认删除', '确定要删除这个语音方案吗？'):
            self.db.delete_voice_profile(self.current_profile_id)
            self.current_profile_id = None
            self._refresh_profiles()

    def _save_current_profile(self):
        if not self.current_profile_id:
            name = self.profile_name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '请输入方案名称')
                return
            self.current_profile_id = self.db.add_voice_profile(
                name=name, voice_id='',
                rate=self.rate_val_var.get(),
                volume=1.0)
            self._refresh_profiles()
            return

        voice_idx = self.voice_combo.current()
        voice_id = ''
        if 0 <= voice_idx < len(self.voices):
            v = self.voices[voice_idx]
            if v.get('source') != 'sep':
                voice_id = v['id']

        vol = self.vol_val_var.get() / 100.0

        self.db.update_voice_profile(
            self.current_profile_id,
            name=self.profile_name_var.get().strip(),
            voice_id=voice_id,
            rate=self.rate_val_var.get(),
            volume=vol)

        if voice_id:
            self.tts.set_voice(voice_id)
        self.tts.set_rate(self.rate_val_var.get())
        self.tts.set_volume(vol)

        self._refresh_profiles()
        messagebox.showinfo('成功', '语音方案已保存')

    def _on_profile_name_change(self):
        pass

    def _on_voice_select(self, event):
        idx = self.voice_combo.current()
        if 0 <= idx < len(self.voices):
            v = self.voices[idx]
            if v.get('source') != 'sep':
                self.tts.set_voice(v['id'])

    def _test_voice(self):
        idx = self.voice_combo.current()
        if 0 <= idx < len(self.voices):
            v = self.voices[idx]
            if v.get('source') != 'sep':
                self.tts.set_voice(v['id'])
        self.tts.set_rate(self.rate_val_var.get())
        self.tts.speak('你好，这是小说播放器的语音测试。可以听到我的声音吗？')

    def _on_rate_change(self, val):
        self.rate_label.configure(text=str(int(float(val))))
        self.tts.set_rate(int(float(val)))

    def _on_vol_change(self, val):
        self.vol_label.configure(text=f'{int(float(val))}%')
        self.tts.set_volume(int(float(val)) / 100.0)

    def _on_theme_change(self):
        new_theme = self.theme_var.get()
        if new_theme != self.theme.current_theme:
            self.theme.toggle()
            if self.on_theme_toggle:
                self.on_theme_toggle()

    def refresh_ui(self):
        self._refresh_profiles()
        self._load_voices()
