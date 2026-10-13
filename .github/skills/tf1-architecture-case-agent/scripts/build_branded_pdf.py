#!/usr/bin/env python3
"""
Convert the three Patient Access 360 deliverables into branded PDFs that match
the visual standard of the original Data Architecture Academy case documents
(source/*.pdf): a plain academic layout with a small repeating header block
(DATA ARCHITECTURE ACADEMY / level line / document line / page number) and
plain black/navy text, numbered sections, and simple tables — no colour
gradients or dashboard styling.

No substantive content is invented, added, or removed. HTML/Markdown markup
is stripped and re-flowed into the branded layout; tables are rendered as
reportlab Table objects; the two Mermaid diagrams (which reportlab cannot
render directly) are rendered as clearly labeled indented text/tree
summaries of their node content.
"""

import re
import html as html_lib
from bs4 import BeautifulSoup

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, ListFlowable, ListItem, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.pdfgen import canvas as canvas_mod
from PIL import Image as PILImage
import os
import argparse
import glob

# DIAGRAM_FILES maps a 0-based mermaid-block-encounter-order index (the Nth
# <div class="mermaid"> found top-to-bottom in the HTML) to an image path.
# Populated at runtime from --diagrams-dir (sorted alphabetically) unless
# --diagram-map is given explicitly. Left empty here; see configure_diagrams().
DIAGRAM_FILES = {}


def configure_diagrams(diagrams_dir):
    """Auto-map every *.png in diagrams_dir, sorted by filename, to mermaid
    block index 0, 1, 2, ... in encounter order. Rename files so sort order
    matches diagram order in the document (e.g. 00_utility-tree.png,
    01_architecture.png) if you need a specific order."""
    DIAGRAM_FILES.clear()
    if not diagrams_dir or not os.path.isdir(diagrams_dir):
        return
    pngs = sorted(glob.glob(os.path.join(diagrams_dir, "*.png")))
    for i, p in enumerate(pngs):
        DIAGRAM_FILES[i] = p

NAVY = colors.HexColor("#0b1f3a")
BLACK = colors.black
GRAY = colors.HexColor("#444444")
RULE = colors.HexColor("#999999")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.9 * inch

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------

def build_styles():
    ss = getSampleStyleSheet()
    styles = {}
    styles['DocTitle'] = ParagraphStyle(
        'DocTitle', parent=ss['Title'], fontName='Helvetica-Bold', fontSize=20,
        leading=25, textColor=NAVY, spaceAfter=6, alignment=TA_CENTER)
    styles['DocSubtitle'] = ParagraphStyle(
        'DocSubtitle', parent=ss['Normal'], fontName='Helvetica', fontSize=12.5,
        leading=16, textColor=BLACK, spaceAfter=4, alignment=TA_CENTER)
    styles['DocMeta'] = ParagraphStyle(
        'DocMeta', parent=ss['Normal'], fontName='Helvetica-Oblique', fontSize=9.5,
        leading=13, textColor=GRAY, spaceAfter=2, alignment=TA_CENTER)
    styles['H1'] = ParagraphStyle(
        'H1', parent=ss['Heading1'], fontName='Helvetica-Bold', fontSize=14.5,
        leading=18, textColor=NAVY, spaceBefore=16, spaceAfter=8)
    styles['H2'] = ParagraphStyle(
        'H2', parent=ss['Heading2'], fontName='Helvetica-Bold', fontSize=12.5,
        leading=16, textColor=NAVY, spaceBefore=12, spaceAfter=6)
    styles['H3'] = ParagraphStyle(
        'H3', parent=ss['Heading3'], fontName='Helvetica-Bold', fontSize=10.8,
        leading=14, textColor=BLACK, spaceBefore=10, spaceAfter=5)
    styles['Body'] = ParagraphStyle(
        'Body', parent=ss['Normal'], fontName='Helvetica', fontSize=9.6,
        leading=13.2, textColor=BLACK, spaceAfter=7, alignment=TA_LEFT)
    styles['BodyBold'] = ParagraphStyle(
        'BodyBold', parent=styles['Body'], fontName='Helvetica-Bold')
    styles['Bullet'] = ParagraphStyle(
        'Bullet', parent=styles['Body'], leftIndent=14, bulletIndent=2, spaceAfter=4)
    styles['TableCell'] = ParagraphStyle(
        'TableCell', parent=ss['Normal'], fontName='Helvetica', fontSize=8.2,
        leading=10.6, textColor=BLACK)
    styles['TableHeadCell'] = ParagraphStyle(
        'TableHeadCell', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=8.3,
        leading=10.6, textColor=colors.white)
    styles['Mono'] = ParagraphStyle(
        'Mono', parent=ss['Normal'], fontName='Courier', fontSize=8.6,
        leading=11.6, textColor=BLACK, leftIndent=10, spaceAfter=3)
    styles['Caption'] = ParagraphStyle(
        'Caption', parent=ss['Normal'], fontName='Helvetica-Oblique', fontSize=8.8,
        leading=12, textColor=GRAY, spaceBefore=2, spaceAfter=6)
    return styles


# ---------------------------------------------------------------------------
# Header / footer page decoration
# ---------------------------------------------------------------------------

class HeaderFooterDoc(BaseDocTemplate):
    """BaseDocTemplate with a shared onPage callback drawing the repeating
    header block + footer page number that matches the original case docs."""

    def __init__(self, filename, level_line, doc_line, **kw):
        super().__init__(filename, pagesize=LETTER, **kw)
        self.level_line = level_line
        self.doc_line = doc_line
        frame = Frame(
            MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - 0.55 * inch,
            id='normal', topPadding=0, bottomPadding=0
        )
        template = PageTemplate(id='main', frames=[frame], onPage=self._draw_header_footer)
        self.addPageTemplates([template])

    def _draw_header_footer(self, canvas: canvas_mod.Canvas, doc):
        canvas.saveState()
        top_y = PAGE_H - 0.55 * inch
        canvas.setFont('Helvetica-Bold', 8.4)
        canvas.setFillColor(BLACK)
        canvas.drawString(MARGIN, top_y + 26, "DATA ARCHITECTURE ACADEMY")
        canvas.setFont('Helvetica', 8.1)
        canvas.drawString(MARGIN, top_y + 15, self.level_line)
        canvas.drawString(MARGIN, top_y + 4, self.doc_line)
        canvas.setFont('Helvetica', 8.1)
        canvas.drawRightString(PAGE_W - MARGIN, top_y + 4, str(canvas.getPageNumber()))
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, top_y - 2, PAGE_W - MARGIN, top_y - 2)
        canvas.restoreState()


def make_title_block(styles, title, subtitle, doc_label, author_name=None, author_role=None):
    flow = []
    flow.append(Spacer(1, 0.35 * inch))
    flow.append(Paragraph(title, styles['DocTitle']))
    flow.append(Paragraph(subtitle, styles['DocSubtitle']))
    flow.append(Paragraph(doc_label, styles['DocMeta']))
    if author_name:
        byline = f"Prepared by: {author_name}" + (f" — {author_role}" if author_role else "")
        flow.append(Paragraph(byline, styles['DocMeta']))
    flow.append(Spacer(1, 10))
    flow.append(HRFlowable(width="100%", thickness=0.75, color=RULE, spaceAfter=14))
    return flow

# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------

TAG_RE = re.compile(r'\[PA-[A-Za-z0-9]+\]')


def esc(text):
    return html_lib.escape(text, quote=False)


_BOX_DRAW_MAP = {
    '\u2500': '-', '\u2502': '|', '\u250c': '+', '\u2510': '+',
    '\u2514': '`', '\u2518': '+', '\u251c': '|', '\u2524': '+',
    '\u252c': '+', '\u2534': '+', '\u253c': '+', '\u2192': '->',
    '\u2190': '<-', '\u2191': '^', '\u2193': 'v',
}


def ascii_safe_mono(text):
    """Base-14 PDF fonts (Courier/Helvetica) lack box-drawing glyphs; swap
    them for plain ASCII so monospace/code blocks render visibly."""
    for uch, rep in _BOX_DRAW_MAP.items():
        text = text.replace(uch, rep)
    return text


def inline_md_to_rl(text):
    """Convert a small subset of inline Markdown (**bold**, *italic*, `code`)
    and citation tags into reportlab-paragraph-safe markup, preserving text."""
    text = esc(text)
    # restore citation bracket tags readability (escape wouldn't change [ ])
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'`([^`]+?)`', r'<font face="Courier">\1</font>', text)
    return text


def para(text, style):
    return Paragraph(inline_md_to_rl(text), style)


def table_from_rows(rows, styles, col_widths=None, head=True):
    """rows: list of list[str] (plain text / light markdown). First row is header if head=True."""
    data = []
    for i, row in enumerate(rows):
        style = styles['TableHeadCell'] if (head and i == 0) else styles['TableCell']
        data.append([Paragraph(inline_md_to_rl(c), style) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1 if head else 0)
    style_cmds = [
        ('GRID', (0, 0), (-1, -1), 0.5, RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if head:
        style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), NAVY))
    for i in range(1 if head else 0, len(rows)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f7fa')))
    t.setStyle(TableStyle(style_cmds))
    return t


def auto_col_widths(n, total=6.6 * inch):
    return [total / n] * n


def table_from_markup_rows(rows, styles, col_widths=None, head=True):
    """Like table_from_rows, but cells already contain reportlab-safe markup
    (e.g. from render_inline()) and must NOT be re-escaped/re-converted."""
    data = []
    for i, row in enumerate(rows):
        style = styles['TableHeadCell'] if (head and i == 0) else styles['TableCell']
        data.append([Paragraph(c, style) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1 if head else 0)
    style_cmds = [
        ('GRID', (0, 0), (-1, -1), 0.5, RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if head:
        style_cmds.append(('BACKGROUND', (0, 0), (-1, 0), NAVY))
    for i in range(1 if head else 0, len(rows)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f7fa')))
    t.setStyle(TableStyle(style_cmds))
    return t


# ---------------------------------------------------------------------------
# Mermaid -> indented text/tree fallback rendering
# ---------------------------------------------------------------------------

def _clean_mermaid_label(label):
    label = label.replace('<br/>', ' ').replace('<br>', ' ')
    label = re.sub(r'</?b>', '', label)
    return label.strip()


def parse_mermaid_tree(source):
    """Parse a mermaid `graph TD` tree (no subgraphs) into nodes + edges."""
    nodes = {}
    edges = []  # (src, dst) in order
    edge_re = re.compile(r'(\w+)(?:\["(.*?)"\])?\s*-->\s*(\w+)(?:\["(.*?)"\])?')
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith('graph') or line.startswith('style'):
            continue
        m = edge_re.match(line)
        if not m:
            continue
        src, src_label, dst, dst_label = m.groups()
        if src_label:
            nodes[src] = _clean_mermaid_label(src_label)
        if dst_label:
            nodes[dst] = _clean_mermaid_label(dst_label)
        edges.append((src, dst))
    return nodes, edges


def render_tree_text(nodes, edges):
    children = {}
    all_ids = set()
    for src, dst in edges:
        children.setdefault(src, []).append(dst)
        all_ids.add(src)
        all_ids.add(dst)
    targets = {dst for _, dst in edges}
    roots = [n for n in all_ids if n not in targets]
    lines = []

    def walk(node_id, prefix, is_last, is_root=False):
        label = nodes.get(node_id, node_id)
        if is_root:
            lines.append(label)
            new_prefix = ""
        else:
            connector = "`-- " if is_last else "|-- "
            lines.append(prefix + connector + label)
            new_prefix = prefix + ("    " if is_last else "|   ")
        kids = children.get(node_id, [])
        for i, kid in enumerate(kids):
            walk(kid, new_prefix, i == len(kids) - 1)

    for r in roots:
        walk(r, "", False, is_root=True)
    return "\n".join(lines)


def parse_mermaid_flowchart(source):
    """Parse a mermaid flowchart with subgraphs into (subgraphs, edges).
    subgraphs: list of (sg_id, sg_label, [(node_id, node_label), ...])
    edges: list of (src, dst)
    """
    subgraphs = []
    node_label_all = {}
    current = None
    sg_start_re = re.compile(r'subgraph\s+(\w+)\["(.*?)"\]')
    node_re = re.compile(r'^(\w+)\["(.*?)"\]$')
    edge_re = re.compile(r'^(\w+)\s*-->\s*(\w+)$')
    edges = []
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith('flowchart') or line.startswith('style'):
            continue
        sg_m = sg_start_re.match(line)
        if sg_m:
            current = {'id': sg_m.group(1), 'label': sg_m.group(2), 'nodes': []}
            subgraphs.append(current)
            node_label_all[sg_m.group(1)] = sg_m.group(2)
            continue
        if line == 'end':
            current = None
            continue
        node_m = node_re.match(line)
        if node_m and current is not None:
            nid, nlabel = node_m.groups()
            nlabel = _clean_mermaid_label(nlabel)
            current['nodes'].append((nid, nlabel))
            node_label_all[nid] = nlabel
            continue
        edge_m = edge_re.match(line)
        if edge_m:
            edges.append(edge_m.groups())
    return subgraphs, edges, node_label_all


def render_flowchart_text(subgraphs, edges, node_labels):
    lines = []
    for sg in subgraphs:
        lines.append(f"[{sg['label']}]")
        for nid, nlabel in sg['nodes']:
            lines.append(f"    - {nlabel}")
        lines.append("")
    lines.append("Flow:")
    for src, dst in edges:
        src_l = node_labels.get(src, src)
        dst_l = node_labels.get(dst, dst)
        lines.append(f"    {src_l}  ->  {dst_l}")
    return "\n".join(lines)


def mermaid_block_to_flowables(raw_source, title, styles, kind, diagram_index=None):
    # decode_contents() from bs4 re-serializes with HTML entity escaping
    # (e.g. literal "&" becomes "&amp;"); unescape once here so the later
    # esc() call below is the single, correct escaping pass.
    raw_source = html_lib.unescape(raw_source)
    flow = []
    img_path = DIAGRAM_FILES.get(diagram_index) if diagram_index is not None else None
    if img_path and os.path.exists(img_path):
        flow.append(Paragraph(f"<i>Diagram: {esc(title)}</i>", styles['Caption']))
        with PILImage.open(img_path) as im:
            w_px, h_px = im.size
        max_w = 6.6 * inch
        max_h = 8.5 * inch
        w = max_w
        h = h_px * (w / w_px)
        if h > max_h:
            h = max_h
            w = w_px * (h / h_px)
        flow.append(RLImage(img_path, width=w, height=h))
        return flow
    # Fallback: indented text/tree rendering (used only if a PNG isn't available)
    flow.append(Paragraph(f"<i>Diagram (text rendering): {esc(title)}</i>", styles['Caption']))
    if kind == 'tree':
        nodes, edges = parse_mermaid_tree(raw_source)
        text = render_tree_text(nodes, edges)
    else:
        subgraphs, edges, node_labels = parse_mermaid_flowchart(raw_source)
        text = render_flowchart_text(subgraphs, edges, node_labels)
    for line in text.split('\n'):
        safe = esc(line) if line.strip() else '&nbsp;'
        safe = safe.replace(' ', '&nbsp;')  # preserve indentation/box-drawing spacing
        flow.append(Paragraph(safe, styles['Mono']))
    return flow


# ---------------------------------------------------------------------------
# HTML inline rendering (strong/em/code -> reportlab markup)
# ---------------------------------------------------------------------------

def render_inline_node(node):
    """Render a bs4 node (Tag or NavigableString) to reportlab-safe markup."""
    from bs4 import NavigableString, Tag
    if isinstance(node, NavigableString):
        return esc(str(node))
    if not isinstance(node, Tag):
        return ''
    name = node.name
    inner = ''.join(render_inline_node(c) for c in node.children)
    if name in ('strong', 'b'):
        return f'<b>{inner}</b>'
    if name in ('em', 'i'):
        return f'<i>{inner}</i>'
    if name == 'code':
        return f'<font face="Courier">{inner}</font>'
    if name == 'br':
        return '<br/>'
    if name == 'a':
        return inner
    return inner


def render_inline(tag):
    return ''.join(render_inline_node(c) for c in tag.children).strip()


def html_table_to_flowable(table_tag, styles, total_width=6.6 * inch):
    rows = []
    for tr in table_tag.find_all('tr'):
        cells = tr.find_all(['th', 'td'])
        rows.append([render_inline(c) for c in cells])
    if not rows:
        return None
    n = len(rows[0])
    return table_from_markup_rows(rows, styles, col_widths=auto_col_widths(n, total_width), head=True)


def html_list_to_flowable(ul_tag, styles):
    items = []
    for li in ul_tag.find_all('li', recursive=False):
        txt = render_inline(li)
        items.append(ListItem(Paragraph(txt, styles['Body']), leftIndent=12))
    return ListFlowable(items, bulletType='bullet', start='\u2022', leftIndent=10, bulletFontSize=8)


MERMAID_TITLES_DEFAULT = {
    0: "Diagram 1",
    1: "Diagram 2",
    2: "Diagram 3",
    3: "Diagram 4",
}


def html_node_to_flowables(node, styles, mermaid_counter, mermaid_titles=None):
    """Dispatch a single top-level bs4 child of a <section> to flowables."""
    from bs4 import Tag
    mermaid_titles = mermaid_titles or MERMAID_TITLES_DEFAULT
    flow = []
    if not isinstance(node, Tag):
        return flow, mermaid_counter
    name = node.name
    classes = node.get('class') or []
    if name == 'span':
        return flow, mermaid_counter  # badges: skip (visual chrome only)
    if name == 'h2':
        flow.append(Paragraph(render_inline(node), styles['H1']))
    elif name == 'h3':
        flow.append(Paragraph(render_inline(node), styles['H3']))
    elif name == 'h4':
        flow.append(Paragraph(render_inline(node), styles['H3']))
    elif name == 'p':
        txt = render_inline(node)
        if txt:
            cls = 'BodyBold' if 'tradeoff' in classes else 'Body'
            flow.append(Paragraph(txt, styles[cls]))
    elif name == 'table':
        tbl = html_table_to_flowable(node, styles)
        if tbl:
            flow.append(Spacer(1, 2))
            flow.append(tbl)
            flow.append(Spacer(1, 8))
    elif name == 'ul':
        flow.append(html_list_to_flowable(node, styles))
        flow.append(Spacer(1, 4))
    elif name == 'div' and 'mermaid' in classes:
        raw = node.decode_contents()
        kind = 'tree' if 'graph TD' in raw else 'flowchart'
        title = mermaid_titles.get(mermaid_counter, f'Diagram {mermaid_counter + 1}')
        flow.extend(mermaid_block_to_flowables(raw, title, styles, kind, diagram_index=mermaid_counter))
        flow.append(Spacer(1, 8))
        mermaid_counter += 1
    elif name == 'div':
        # decision / assume-box / gap-box / change-note: walk children recursively
        for child in node.children:
            sub_flow, mermaid_counter = html_node_to_flowables(child, styles, mermaid_counter, mermaid_titles)
            flow.extend(sub_flow)
        flow.append(Spacer(1, 4))
    return flow, mermaid_counter


def build_solution_pdf(src_path, out_path, title, subtitle, doc_label, level_line, doc_line,
                        author_name=None, author_role=None, mermaid_titles=None):
    styles = build_styles()
    html_text = open(src_path, encoding='utf-8').read()
    soup = BeautifulSoup(html_text, 'html.parser')
    main = soup.find('main') or soup.find('body') or soup

    story = []
    story.extend(make_title_block(styles, title, subtitle, doc_label, author_name, author_role))

    mermaid_counter = 0
    sections = main.find_all('section', recursive=False) or [main]
    for section in sections:
        section_flow = []
        for child in section.children:
            flo, mermaid_counter = html_node_to_flowables(child, styles, mermaid_counter, mermaid_titles)
            section_flow.extend(flo)
        story.extend(section_flow)
        story.append(Spacer(1, 6))

    footer_note = soup.find('footer')
    if footer_note:
        story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=10, spaceAfter=6))
        story.append(Paragraph(esc(footer_note.get_text(strip=True)), styles['Caption']))

    doc = HeaderFooterDoc(
        out_path,
        level_line=level_line,
        doc_line=doc_line,
        topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN,
    )
    doc.build(story)


# ---------------------------------------------------------------------------
# Markdown -> flowables (used for the workbook and the validation checklist)
# ---------------------------------------------------------------------------

def split_md_table_row(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]


def is_md_table_sep(line):
    return bool(re.match(r'^\|?[\s:\-|]+\|?$', line.strip())) and '-' in line


def markdown_to_story(md_text, styles, h1_style='H1', total_width=6.6 * inch):
    lines = md_text.splitlines()
    story = []
    i = 0
    n = len(lines)
    list_buffer = []

    def flush_list():
        nonlocal list_buffer
        if list_buffer:
            items = [ListItem(Paragraph(inline_md_to_rl(t), styles['Body']), leftIndent=12)
                      for t in list_buffer]
            story.append(ListFlowable(items, bulletType='bullet', start='\u2022',
                                       leftIndent=10, bulletFontSize=8))
            story.append(Spacer(1, 4))
            list_buffer = []

    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_list()
            i += 1
            continue

        if stripped == '---':
            flush_list()
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.4, color=RULE))
            story.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith('```'):
            flush_list()
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            for cl in code_lines:
                cl = ascii_safe_mono(cl)
                safe = esc(cl) if cl.strip() else '&nbsp;'
                safe = safe.replace(' ', '&nbsp;')
                story.append(Paragraph(safe, styles['Mono']))
            story.append(Spacer(1, 6))
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            flush_list()
            level = len(m.group(1))
            text = m.group(2).strip()
            style = styles[h1_style] if level <= 2 else styles['H3']
            story.append(Paragraph(inline_md_to_rl(text), style))
            i += 1
            continue

        # Markdown table: header row + separator row
        if stripped.startswith('|') and i + 1 < n and is_md_table_sep(lines[i + 1]):
            flush_list()
            header = split_md_table_row(stripped)
            i += 2
            rows = [header]
            while i < n and lines[i].strip().startswith('|'):
                rows.append(split_md_table_row(lines[i].strip()))
                i += 1
            ncols = len(header)
            tbl = table_from_rows(rows, styles, col_widths=auto_col_widths(ncols, total_width), head=True)
            story.append(Spacer(1, 2))
            story.append(tbl)
            story.append(Spacer(1, 8))
            continue

        if re.match(r'^[-*]\s+', stripped):
            item_text = re.sub(r'^[-*]\s+', '', stripped)
            list_buffer.append(item_text)
            i += 1
            continue

        m2 = re.match(r'^\d+\.\s+(.*)$', stripped)
        if m2:
            list_buffer.append(m2.group(1))
            i += 1
            continue

        # plain paragraph
        flush_list()
        para_lines = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(r'^(#{1,6})\s', lines[i].strip()) \
                and lines[i].strip() != '---' and not lines[i].strip().startswith('|') \
                and not re.match(r'^[-*]\s+', lines[i].strip()) and not re.match(r'^\d+\.\s+', lines[i].strip()) \
                and not lines[i].strip().startswith('```'):
            para_lines.append(lines[i].strip())
            i += 1
        text = ' '.join(para_lines)
        story.append(Paragraph(inline_md_to_rl(text), styles['Body']))

    flush_list()
    return story


def build_markdown_pdf(src_path, out_path, title, subtitle, doc_label, level_line, doc_line,
                        author_name=None, author_role=None):
    styles = build_styles()
    md_text = open(src_path, encoding='utf-8').read()

    story = []
    story.extend(make_title_block(styles, title, subtitle, doc_label, author_name, author_role))
    story.extend(markdown_to_story(md_text, styles))

    doc = HeaderFooterDoc(
        out_path, level_line=level_line, doc_line=doc_line,
        topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN,
    )
    doc.build(story)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
#
# Two input modes:
#   --input-html report.html   -> treated as a full TF1 HTML report (same
#                                  structure as the architech-explorer /
#                                  VerdantGrocers-style reports: <main><section>...
#                                  with <div class="mermaid"> blocks)
#   --input-md   report.md     -> treated as plain markdown (headings, lists,
#                                  tables, ```code``` fences) -- used for
#                                  filled workbooks / validation checklists
#
# Example:
#   python3 build_branded_pdf.py \
#       --input-html Solution.html --output Solution.pdf \
#       --title "MediSynth Patient Access 360" \
#       --subtitle "First-Release Architecture Recommendation" \
#       --doc-label "Architecture Recommendation \u2014 full TF1 report" \
#       --level-line "Level 1 case" \
#       --doc-line "Patient Access 360 \u2022 Architecture Recommendation" \
#       --author-name "Jane Doe" --author-role "Solution Architect" \
#       --diagrams-dir ./diagrams

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Render a TF1 case deliverable (HTML or Markdown) into a branded, paginated PDF matching the Data Architecture Academy document style.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--input-html', help='Path to a TF1-style HTML report (<main><section> structure)')
    src.add_argument('--input-md', help='Path to a plain Markdown document')
    ap.add_argument('--output', required=True, help='Output PDF path')
    ap.add_argument('--title', required=True, help='e.g. "MediSynth Patient Access 360"')
    ap.add_argument('--subtitle', required=True, help='e.g. "First-Release Architecture Recommendation"')
    ap.add_argument('--doc-label', required=True, help='Italic line under the subtitle, e.g. "Architecture Recommendation \u2014 full TF1 report"')
    ap.add_argument('--level-line', required=True, help='Repeating header, 2nd line, e.g. "Level 1 case"')
    ap.add_argument('--doc-line', required=True, help='Repeating header, 3rd line, e.g. "Patient Access 360 \u2022 Architecture Recommendation"')
    ap.add_argument('--author-name', default=None)
    ap.add_argument('--author-role', default=None)
    ap.add_argument('--diagrams-dir', default=None,
                     help='Directory of pre-rendered diagram PNGs (see render_mermaid.py). '
                          'Files are matched to <div class="mermaid"> blocks in --input-html '
                          'in alphabetical-filename order = document order. '
                          'Prefix filenames like 00_, 01_, 02_ to control order. '
                          'If omitted/empty, falls back to an indented text/tree rendering.')
    args = ap.parse_args()

    if args.diagrams_dir:
        configure_diagrams(args.diagrams_dir)

    if args.input_html:
        build_solution_pdf(
            args.input_html, args.output,
            title=args.title, subtitle=args.subtitle, doc_label=args.doc_label,
            level_line=args.level_line, doc_line=args.doc_line,
            author_name=args.author_name, author_role=args.author_role,
        )
    else:
        build_markdown_pdf(
            args.input_md, args.output,
            title=args.title, subtitle=args.subtitle, doc_label=args.doc_label,
            level_line=args.level_line, doc_line=args.doc_line,
            author_name=args.author_name, author_role=args.author_role,
        )
    print(f"Wrote {args.output}")
