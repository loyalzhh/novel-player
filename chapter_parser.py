"""
章节解析模块 - 自动识别小说章节
支持中文和英文的章节格式
"""

import re


# 章节匹配正则模式列表
CHAPTER_PATTERNS = [
    # 第X章, 第X节, 第X回 等中文格式
    re.compile(r'^[　\s]*(第[零一二三四五六七八九十百千万0-9]+[章節节回回卷部集篇])[　\s]*(.*?)$', re.MULTILINE),
    # 第X章 XXXX (可能不在行首)
    re.compile(r'(第[零一二三四五六七八九十百千万0-9]+[章節节回回卷部集篇])[　\s]+[^\n]{0,50}', re.MULTILINE),
    # Chapter X, CHAPTER X 等英文格式
    re.compile(r'^(?:Chapter|CHAPTER|Ch\.|ch\.)\s*([0-9]+)\s*(.*?)$', re.MULTILINE),
    # 数字章节: 1. XXXX, 001 XXXX
    re.compile(r'^[　\s]*([0-9]+)[\.\、\s]\s*(.{2,40})$', re.MULTILINE),
    # 卷/部: 第一卷 XXX, 第二部 XXX
    re.compile(r'^(第[零一二三四五六七八九十百千万0-9]+[卷部])[　\s]*(.*?)$', re.MULTILINE),
    # 序章/楔子/尾声/番外
    re.compile(r'^[　\s]*(序章|楔子|引子|前言|尾声|番外|后记|附录|完结感言)[　\s:]*(.*?)$', re.MULTILINE),
]


def detect_chapters(text):
    """
    识别文本中的章节

    返回: [(chapter_index, title, start_pos, end_pos), ...]
    如果未识别到章节，则将全文作为一个章节
    """
    if not text or len(text.strip()) == 0:
        return [(0, "正文", 0, 0)]

    matches = []

    for pattern in CHAPTER_PATTERNS:
        for m in pattern.finditer(text):
            start = m.start()
            # 提取标题
            if m.lastindex and m.lastindex >= 1:
                title = m.group(1).strip()
                # 如果有第二组且非空，添加到标题
                if m.lastindex >= 2 and m.group(2):
                    title += " " + m.group(2).strip()
            else:
                title = m.group(0).strip()

            # 标题太长则截断
            if len(title) > 60:
                title = title[:57] + "..."

            matches.append((start, title))

    # 按位置排序并去重（同一位置只保留第一个匹配）
    matches.sort(key=lambda x: x[0])
    seen_positions = set()
    unique_matches = []
    for pos, title in matches:
        # 允许5个字符的容差来去重
        is_dup = False
        for sp in seen_positions:
            if abs(pos - sp) <= 5:
                is_dup = True
                break
        if not is_dup:
            seen_positions.add(pos)
            unique_matches.append((pos, title))

    matches = unique_matches

    chapters = []
    if len(matches) == 0:
        # 没有识别到章节，整文作为一章
        chapters.append((0, "正文", 0, len(text)))
    else:
        for i, (pos, title) in enumerate(matches):
            start_pos = pos
            if i + 1 < len(matches):
                end_pos = matches[i + 1][0]
            else:
                end_pos = len(text)
            chapters.append((i, title, start_pos, end_pos))

        # 如果第一个章节不是从0开始，添加前言
        if chapters[0][2] > 50:
            chapters.insert(0, (0, "前言/简介", 0, chapters[0][2]))
            # 重新编号
            chapters = [(j, ch[1], ch[2], ch[3]) for j, ch in enumerate(chapters)]

    return chapters


def get_chapter_text(text, chapter):
    """获取指定章节的文本内容"""
    _, _, start_pos, end_pos = chapter
    return text[start_pos:end_pos]


def split_sentences(text):
    """
    将文本按句子分割，用于逐句朗读
    句子分隔符: 。！？；… \n
    """
    # 先按换行分割段落
    paragraphs = text.split('\n')

    sentences = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 按中文标点分割句子
        # 使用正则保留分隔符
        parts = re.split(r'([。！？；…!?;]+)', para)

        current = ""
        for part in parts:
            if re.match(r'^[。！？；…!?;]+$', part):
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            else:
                current += part

        if current.strip():
            sentences.append(current.strip())

    # 过滤掉太短的句子（如纯标点）
    sentences = [s for s in sentences if len(s) >= 1]

    return sentences
