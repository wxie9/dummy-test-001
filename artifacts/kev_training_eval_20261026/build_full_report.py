from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
REFERENCE = Path("/Users/chen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_bqcdaq8tutkg12_93e3/temp/RWTemp/2026-10/4ce29512088ca8a5a3d00dc10dca9247/Kev训练与评测报告.docx")
OUT = ROOT / "Kev训练与评测完整报告.docx"
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

NAVY = "244B60"
BLUE = "416C85"
PALE = "EEF2F4"
MID = "B7C4CB"
TEXT = "1A1A1A"
FONT = "PingFang SC"
SANS = "Arial"
PIL_SANS = "/System/Library/Fonts/Supplemental/Arial.ttf"

RUNS = {
    "Qwen3.5-0.8B": ROOT / "runs/replica-20261026",
    "Qwen3-0.6B": ROOT / "runs/qwen3-06b-20261026",
}
SUITES = [
    ("decision-v7", "decision-v7-test"),
    ("transfer-v4", "transfer-v4-test"),
    ("transfer-v9", "transfer-v9-test"),
    ("hard-v1", "hard-v1-test"),
    ("devtools-v1", "devtools-v1-test"),
    ("documents-v1", "documents-v1-test"),
]


def set_run_font(run, size=None, bold=None, color=None, name=FONT):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run._element.rPr.rFonts.set(qn("w:ascii"), SANS if name == FONT else name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), SANS if name == FONT else name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color="D5DDE1", size="6"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for side in ("top", "left", "bottom", "right"):
        edge = borders.find(qn(f"w:{side}"))
        if edge is None:
            edge = OxmlElement(f"w:{side}")
            borders.append(edge)
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), size)
        edge.set(qn("w:space"), "0")
        edge.set(qn("w:color"), color)


def prevent_row_break(row):
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    tr_pr.append(el)


def set_cell_text(cell, text, *, bold=False, color=TEXT, size=8.8, align=None, mono=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    if align is not None:
        p.alignment = align
    r = p.add_run(str(text))
    set_run_font(r, size=size, bold=bold, color=color, name="Consolas" if mono else FONT)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_cell_border(cell)


def add_table(doc, headers, rows, widths=None, font_size=8.6):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.style = "Table Grid"
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_cells = table.rows[0].cells
    for idx, header in enumerate(headers):
        set_cell_shading(header_cells[idx], NAVY)
        set_cell_text(header_cells[idx], header, bold=True, color="FFFFFF", size=font_size, align=WD_ALIGN_PARAGRAPH.CENTER)
        if widths:
            header_cells[idx].width = Inches(widths[idx])
    prevent_row_break(table.rows[0])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for cidx, value in enumerate(row):
            if ridx % 2:
                set_cell_shading(cells[cidx], PALE)
            align = WD_ALIGN_PARAGRAPH.LEFT if cidx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            set_cell_text(cells[cidx], value, size=font_size, align=align)
            if widths:
                cells[cidx].width = Inches(widths[cidx])
        prevent_row_break(table.rows[-1])
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(0)
    return table


def set_para(p, before=0, after=5, line=1.22, keep=False):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if keep:
        pf.keep_with_next = True


def add_body(doc, text, *, after=5):
    p = doc.add_paragraph()
    set_para(p, after=after)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    set_run_font(r, size=9.6, color=TEXT)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_para(p, before=1, after=6, line=1.0)
    r = p.add_run(text)
    set_run_font(r, size=8.2, color="56636A")
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    set_para(p, before=9 if level == 1 else 6, after=4, line=1.0, keep=True)
    r = p.add_run(text)
    set_run_font(r, size=14 if level == 1 else 11, bold=True, color=TEXT)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="Normal")
    set_para(p, after=2, line=1.18)
    p.paragraph_format.left_indent = Cm(0.45)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    r = p.add_run("• " + text)
    set_run_font(r, size=9.3, color=TEXT)
    return p


def add_page_break(doc):
    doc.add_page_break()


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1); run._r.append(instr_text); run._r.append(fld_char2)
    set_run_font(run, size=8.0, color="3E464A")


def style_document(doc):
    for section in doc.sections:
        section.top_margin = Inches(0.67)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        section.header_distance = Inches(0.28)
        section.footer_distance = Inches(0.28)
        header = section.header
        hp = header.paragraphs[0]
        hp.clear()
        hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_para(hp, after=0, line=1.0)
        hr = hp.add_run("KEV")
        set_run_font(hr, size=8.0, bold=True, color="3E464A", name=SANS)
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.clear()
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        set_para(fp, after=0, line=1.0)
        r = fp.add_run("Kev Qwen3 / Qwen3.5 训练与评测  |  ")
        set_run_font(r, size=8.0, color="3E464A")
        add_page_field(fp)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(9.6)
    title = styles["Title"]
    title.font.name = FONT
    title._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    title.font.size = Pt(25)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def clear_body_keep_section(doc):
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def parse_losses(path):
    pattern = re.compile(r"ep\d+ step (\d+)/\d+ loss ([0-9.]+)")
    pairs = []
    for match in pattern.finditer(path.read_text(errors="replace")):
        pairs.append((int(match.group(1)), float(match.group(2))))
    return pairs


def pil_font(size, bold=False):
    path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else PIL_SANS
    return ImageFont.truetype(path, size)


def line(draw, points, fill, width=2):
    if len(points) > 1:
        draw.line(points, fill=fill, width=width, joint="curve")


def draw_axes(draw, left, top, right, bottom, ymax, title, row_label=None):
    draw.rectangle((left, top, right, bottom), outline="#AAB7BD", width=1)
    for value in (0, ymax / 2, ymax):
        y = bottom - (value / ymax) * (bottom - top)
        draw.line((left, y, right, y), fill="#E4EAED", width=1)
        draw.text((left - 32, y - 6), f"{value:.1f}", fill="#56636A", font=pil_font(15), anchor="ra")
    draw.text(((left + right) / 2, top - 27), title, fill="#1A1A1A", font=pil_font(20, True), anchor="ma")
    if row_label:
        draw.text((left - 60, (top + bottom) / 2), row_label, fill="#1A1A1A", font=pil_font(17, True), anchor="mm")


def points_for(series, left, top, right, bottom, ymax):
    max_step = max(s for s, _ in series)
    return [(left + (s / max_step) * (right - left), bottom - min(v, ymax) / ymax * (bottom - top)) for s, v in series]


def make_loss_figure():
    width, height = 2800, 1650
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    colors = {"Qwen3.5-0.8B": "#244B60", "Qwen3-0.6B": "#6E8491"}
    last = {}
    for col, stage in enumerate((1, 2, 3)):
        for label, run in RUNS.items():
            pairs = parse_losses(run.parent / f"{run.name}-pipeline.log") if False else parse_losses(ROOT / ("runs/replica-20261026" if label.startswith("Qwen3.5") else "runs/qwen3-06b-20261026") / f"stage{stage}-train.log")
            steps = [x for x, _ in pairs]
            vals = [y for _, y in pairs]
            last[(label, stage)] = vals[-1]
            row = 0 if label.startswith("Qwen3.5") else 1
            left = 110 + col * 900
            right = left + 760
            top = 100 + row * 760
            bottom = top + 520
            ymax = 2.25 if stage in (1, 3) else 0.75
            draw_axes(draw, left, top, right, bottom, ymax, f"Stage {stage}", label if col == 0 else None)
            raw_pts = points_for(pairs, left, top, right, bottom, ymax)
            line(draw, raw_pts, "#B8C7CE", width=2)
            if len(vals) >= 7:
                smooth = [sum(vals[max(0, i-3): min(len(vals), i+4)]) / len(vals[max(0, i-3): min(len(vals), i+4)]) for i in range(len(vals))]
                line(draw, points_for(list(zip(steps, smooth)), left, top, right, bottom, ymax), colors[label], width=5)
            draw.text((right - 5, top + 12), f"last {vals[-1]:.3f}", fill=colors[label], font=pil_font(17, True), anchor="ra")
            draw.text(((left + right) / 2, bottom + 28), "optimizer step", fill="#56636A", font=pil_font(15), anchor="ma")
    draw.text((width / 2, 25), "Training cross-entropy loss (raw log / 7-point moving average)", fill="#1A1A1A", font=pil_font(26, True), anchor="ma")
    out = FIG_DIR / "loss_curves_qwen3_qwen35.png"
    image.save(out)
    return out, last


def report(path):
    return json.loads(path.read_text())


def suite_metrics(run):
    out = {}
    for display, folder in SUITES:
        out[display] = report(run / "benchmarks" / folder / "report.json")["clean"]
    return out


def make_accuracy_figure(q35, q3):
    labels = [x[0] for x in SUITES]
    a = [100 * q35[x]["acc"] for x in labels]
    b = [100 * q3[x]["acc"] for x in labels]
    width, height = 2800, 1080
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, right, top, bottom = 145, 2730, 130, 815
    draw.rectangle((left, top, right, bottom), outline="#AAB7BD", width=1)
    for tick in (0, 25, 50, 75, 100):
        y = bottom - tick / 100 * (bottom - top)
        draw.line((left, y, right, y), fill="#E4EAED", width=1)
        draw.text((left - 15, y), str(tick), fill="#56636A", font=pil_font(18), anchor="rm")
    group = (right-left)/len(labels)
    barw = group * 0.28
    for i, (v1, v2) in enumerate(zip(a, b)):
        center = left + group * (i + 0.5)
        for offset, value, color, label in [(-barw-8, v1, "#244B60", "Qwen3.5"), (8, v2, "#728A96", "Qwen3")]:
            x0 = center + offset
            y0 = bottom - value / 100 * (bottom-top)
            draw.rectangle((x0, y0, x0 + barw, bottom), fill=color)
            draw.text((x0 + barw/2, y0 - 10), f"{value:.1f}", fill="#1A1A1A", font=pil_font(17), anchor="ms")
        draw.text((center, bottom + 32), labels[i], fill="#1A1A1A", font=pil_font(18), anchor="ma")
    draw.text((width/2, 38), "Held-out accuracy under the same evaluation protocol", fill="#1A1A1A", font=pil_font(27, True), anchor="ma")
    draw.rectangle((left, 910, left+24, 934), fill="#244B60")
    draw.text((left+34, 922), "Qwen3.5-0.8B", fill="#1A1A1A", font=pil_font(19), anchor="lm")
    draw.rectangle((left+260, 910, left+284, 934), fill="#728A96")
    draw.text((left+294, 922), "Qwen3-0.6B", fill="#1A1A1A", font=pil_font(19), anchor="lm")
    out = FIG_DIR / "heldout_accuracy_comparison.png"
    image.save(out)
    return out


def fmt_dur(seconds):
    seconds = round(seconds)
    return f"{seconds // 3600} h {(seconds % 3600) // 60} min {seconds % 60} s" if seconds >= 3600 else f"{seconds // 60} min {seconds % 60} s"


def main():
    q35 = suite_metrics(RUNS["Qwen3.5-0.8B"])
    q3 = suite_metrics(RUNS["Qwen3-0.6B"])
    loss_fig, last_losses = make_loss_figure()
    acc_fig = make_accuracy_figure(q35, q3)

    doc = Document(REFERENCE)
    clear_body_keep_section(doc)
    style_document(doc)

    # Title page and result summary
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_para(p, before=18, after=5, line=1.0)
    r = p.add_run("Kev 训练与评测完整报告")
    set_run_font(r, size=25, bold=True, color="000000")
    p = doc.add_paragraph()
    set_para(p, after=16, line=1.0)
    r = p.add_run("Qwen3-0.6B 与 Qwen3.5-0.8B：三阶段 LoRA 训练、校准与公开评测对比")
    set_run_font(r, size=12.5, color="4C565B")
    p = doc.add_paragraph()
    set_para(p, after=14)
    r = p.add_run("报告日期：2026 年 10 月 27 日    |    实验硬件：NVIDIA A800 SXM4 80GB（单卡）")
    set_run_font(r, size=9.5, color="4C565B")
    add_body(doc, "本报告汇总两次使用同一 Kev 三阶段配方完成的训练与测试。两次均从各自的预训练基座开始，重新训练 LoRA adapter 与 256 维 pointer head；没有加载或微调官方发布的 Kev 成品 checkpoint。训练、温度校准和六项公开测试套件均已完成。", after=8)
    add_heading(doc, "核心结论", 2)
    add_table(doc, ["问题", "结论"], [
        ["质量", "Qwen3.5-0.8B 在六个相同的留出面板上均高于 Qwen3-0.6B，领先 1.28–7.81 个百分点；hard-v1 的差距最大。"],
        ["效率", "Qwen3-0.6B 总训练用时 1 h 33 min 59 s，比 Qwen3.5-0.8B 的 1 h 59 min 40 s 少 21.5%；峰值分配显存也更低。"],
        ["官方对照", "Qwen3.5-0.8B 复现与官方 Kev-0.8B 在四个可直接对齐面板上相差 +0.20 至 −1.86 个百分点；这是一轮单次复现，不是逐位权重复现或统计等价结论。"],
        ["使用边界", "Kev 是面向给定选项的概率式决策模型，不是通用生成式聊天模型；训练和本报告的评测均使用 Transformers / PyTorch，不依赖 vLLM。"],
    ], widths=[1.15, 5.55], font_size=9.0)
    doc.add_picture(str(acc_fig), width=Inches(6.45))
    add_caption(doc, "图 1　六项留出测试的准确率；同一套件按相同 clean 口径比较。")

    add_page_break(doc)
    add_heading(doc, "一、实验范围与方法概览", 1)
    add_body(doc, "目标是复现 Kev-0.8B 所公开的三阶段训练思路，并在同一服务器、同一训练数据配方和同一评测入口下，对 Qwen3.5-0.8B-Base 与 Qwen3-0.6B-Base 进行一次可追溯比较。结果来自保存的训练日志、training_metrics.json 与每个 benchmark 的 report.json。")
    add_heading(doc, "1.1 模型形式", 2)
    add_body(doc, "模型输入一段任务描述、候选选项与上下文，输出各选项的概率；损失为正确选项上的交叉熵。预训练基座保持冻结，可训练部分由 LoRA 和新建的 256 维 pointer head 构成。Qwen3.5 的可训练参数约 11.3M，Qwen3 约 10.6M。")
    add_heading(doc, "1.2 共同训练设置", 2)
    add_table(doc, ["组件", "配置"], [
        ["参数高效微调", "LoRA rank 16，alpha 32，dropout 0.05；覆盖注意力、MLP 与 DeltaNet 投影。"],
        ["优化", "AdamW，weight decay 0.01；OneCycleLR（pct_start=0.1）；梯度裁剪 1.0。head 与 LoRA 使用同一学习率。"],
        ["数值精度", "冻结基座以 FP32 载入，前向采用 BF16 autocast；评测用 FP32，LoRA 不合并。"],
        ["选项扰动", "每 epoch 打乱选项；p_none=0.10、p_none_distract=0.12、p_distract=0.15、p_none_pair=0.25。"],
        ["关闭的附加项", "KL、ordinal、label smoothing、Brier 与 focal 等附加损失均为 0 / 关闭。"],
    ], widths=[1.35, 5.35])
    add_heading(doc, "1.3 运行环境与实现差异", 2)
    add_table(doc, ["项目", "本次环境"], [
        ["硬件", "NVIDIA A800 SXM4 80GB；训练与评测使用单卡。"],
        ["主要软件", "Python 3.12.12，PyTorch 2.8.0+cu128，Transformers 5.17.0，PEFT 0.21.0，Accelerate 1.15.0。"],
        ["系统约束", "Ubuntu 18.04 / glibc 2.27；Qwen3.5 通过 glibc 2.31 兼容加载器运行，不是系统重装。"],
        ["内核提示", "Qwen3.5 日志显示 causal_conv1d 未安装，部分计算回退到参考 PyTorch 实现。结果正确，但速度可能变慢；本次没有做该因素的受控归因。"],
    ], widths=[1.35, 5.35])

    add_page_break(doc)
    add_heading(doc, "二、三阶段训练协议与数据组成", 1)
    add_body(doc, "三个阶段严格顺序衔接：阶段二加载本次阶段一产出的 adapter 与 head，阶段三加载本次阶段二产物。数据按官方冻结的 JSONL 分区读取；评测分区没有加入训练。下表的“训练记录”包含回放，但不把增强后的重复访问误写为独立样本量。")
    add_table(doc, ["阶段", "训练角色与主要数据", "训练记录（含回放）", "Epoch", "LR", "Batch × accum", "更新步数"], [
        ["1", "基础决策：decision-v7", "12,576", "2", "1e-4", "8 × 1", "3,144"],
        ["2", "日期规则与缺失证据：dates_unknowable + decision 回放", "3,425", "1", "4e-5", "8 × 1", "429"],
        ["3", "documents-v1、hard-v1、devtools-v1 + decision 回放", "22,539", "1", "2e-5", "4 × 2", "2,818"],
    ], widths=[0.45, 2.3, 0.75, 0.45, 0.52, 0.78, 0.62], font_size=8.0)
    add_heading(doc, "2.1 数据边界", 2)
    add_bullet(doc, "阶段一的 decision-v7 由十个公开分类来源各 1,000 条、896 条策略样本和 1,680 条组合规则样本组成。")
    add_bullet(doc, "阶段二的 dates_unknowable 有 1,425 条原始记录，并加入 2,000 条 decision-v7 回放。")
    add_bullet(doc, "阶段三原始数据共 16,539 条（documents-v1 5,219、hard-v1 6,000、devtools-v1 5,320），再加入 6,000 条回放。")
    add_bullet(doc, "三阶段累计请求 51,116 条源记录；数据增强后实际送入训练的记录变体合计 64,636。两者都包含重复、回放和多 epoch 访问，不能解释成 64,636 个独立训练样本。")
    add_heading(doc, "2.2 训练与推理组件的分工", 2)
    add_body(doc, "训练通过 Transformers / PyTorch 直接前向、反向和更新 LoRA 与 head；vLLM 是面向大规模文本生成的推理引擎，不参与这套 pointer-head 训练。即使服务器未来能安装新版 vLLM，也不会替代 Kev 的训练循环；其价值主要在常规 Qwen 生成式模型的部署与吞吐。")

    add_page_break(doc)
    add_heading(doc, "三、训练过程、损失曲线与资源开销", 1)
    add_body(doc, "图 2 从六份 stageN-train.log 中提取每 10 个 optimizer step 记录的训练交叉熵。浅线是原始日志值，深线为相邻 7 个记录点的移动平均。每阶段的数据构成、序列长度和学习率都不同，因此曲线仅用于观察各阶段内部的优化状态，不能用不同阶段的绝对 loss 高低比较模型优劣，也不是验证集损失。")
    doc.add_picture(str(loss_fig), width=Inches(6.45))
    add_caption(doc, "图 2　两次训练的三阶段 CE loss。每个面板独立计步；终点标注为最后一次日志记录。")
    add_heading(doc, "3.1 训练时间、token 与显存", 2)
    resource_rows = []
    for stage in (1, 2, 3):
        m35 = json.loads((RUNS["Qwen3.5-0.8B"] / f"stage{stage}" / "training_metrics.json").read_text())
        m3 = json.loads((RUNS["Qwen3-0.6B"] / f"stage{stage}" / "training_metrics.json").read_text())
        resource_rows.append([
            f"Stage {stage}",
            fmt_dur(m35["wall_seconds"]),
            f"{m35['forward_tokens']:,}",
            f"{m35['peak_device_bytes'] / 2**30:.2f} GiB",
            fmt_dur(m3["wall_seconds"]),
            f"{m3['forward_tokens']:,}",
            f"{m3['peak_device_bytes'] / 2**30:.2f} GiB",
        ])
    add_table(doc, ["阶段", "Qwen3.5 时间", "Qwen3.5 token", "Qwen3.5 峰值", "Qwen3 时间", "Qwen3 token", "Qwen3 峰值"], resource_rows, widths=[0.47, 0.85, 1.0, 0.82, 0.82, 1.0, 0.82], font_size=7.7)
    add_body(doc, "总训练时间分别为 1 h 59 min 40 s（Qwen3.5）和 1 h 33 min 59 s（Qwen3），Qwen3 少用 25 min 41 s，即 21.5%。峰值是 PyTorch 的 max_memory_allocated，不等于 nvidia-smi 的预留显存或整卡占用。两次训练均未记录非有限 loss、截断记录或拒绝记录。", after=6)
    add_heading(doc, "3.2 曲线解读", 2)
    add_bullet(doc, f"阶段一从约 1.8–2.0 的初始 CE 降到最后日志点：Qwen3.5={last_losses[('Qwen3.5-0.8B', 1)]:.3f}，Qwen3={last_losses[('Qwen3-0.6B', 1)]:.3f}。")
    add_bullet(doc, f"阶段二数据较小且只有一个 epoch，曲线波动相对更大；终点为 Qwen3.5={last_losses[('Qwen3.5-0.8B', 2)]:.3f}，Qwen3={last_losses[('Qwen3-0.6B', 2)]:.3f}。")
    add_bullet(doc, f"阶段三混合了文档、困难推理和开发工具任务，终点为 Qwen3.5={last_losses[('Qwen3.5-0.8B', 3)]:.3f}，Qwen3={last_losses[('Qwen3-0.6B', 3)]:.3f}；它不表示对任一单独测试集的泛化误差。")

    add_page_break(doc)
    add_heading(doc, "四、评测协议与完整结果", 1)
    add_body(doc, "最终评测只使用各自阶段三 checkpoint。温度在 decision-v7 development clean 集上通过对数网格最小化 NLL 后固定：Qwen3.5 的 T=2.406050，Qwen3 的 T=2.351096。温度缩放只调整置信度尖锐程度，不改变同一道题的 argmax，因此不会直接提高准确率。评测采用官方 kev.benchmark，关闭 date_facts 预处理、多轮选项旋转、TF32 和融合 SDPA。")
    eval_rows = []
    for name, _ in SUITES:
        a, b = q35[name], q3[name]
        n = a["n"]
        correct_a, correct_b = round(n * a["acc"]), round(n * b["acc"])
        eval_rows.append([name, f"{n:,}", f"{correct_a:,}", f"{a['acc']*100:.2f}%", f"{b['acc']*100:.2f}%", f"{(a['acc']-b['acc'])*100:+.2f}", f"{a['ece']:.4f}", f"{b['ece']:.4f}"])
    add_table(doc, ["测试集", "计分题数", "Q3.5 正确", "Qwen3.5", "Qwen3", "差值 pp", "Q3.5 ECE", "Q3 ECE"], eval_rows, widths=[1.05, 0.65, 0.65, 0.68, 0.63, 0.57, 0.65, 0.65], font_size=7.8)
    add_caption(doc, "表 4　准确率越高越好；ECE 越低越好。devtools-v1 此表采用两次运行共有的 1,073 题原始口径。")
    add_heading(doc, "4.1 评测覆盖与口径", 2)
    add_body(doc, "六套件共读取 5,378 条记录、6,565 道问题；所有问题都返回了结果，拒绝与截断为 0。上表的准确率累计计分 5,999 题：decision-v7 从 1,440 题中取 1,200 道 clean 题；transfer-v4 从 764 题中取 656 道 clean 题；transfer-v9 从 1,264 题中排除 108 道变体及 110 道不可判定题，计分 1,046 题；hard-v1、devtools-v1、documents-v1 的全部题目计分。")
    add_heading(doc, "4.2 两个基座的比较", 2)
    add_body(doc, "Qwen3.5-0.8B 在六个面板均高于 Qwen3-0.6B：decision-v7 +2.33 pp、transfer-v4 +2.44 pp、transfer-v9 +2.29 pp、hard-v1 +7.81 pp、devtools-v1 +2.14 pp、documents-v1 +1.28 pp。这个结果支持在本次单 seed、同配方条件下优先选择 Qwen3.5 追求准确率；但没有多 seed 置信区间、逐题 McNemar 检验或基座对照，不能延伸为总体架构优劣结论。")

    add_page_break(doc)
    add_heading(doc, "五、与官方 Kev-0.8B 的对照", 1)
    add_body(doc, "官方参考值来自 Kev-0.8B 模型卡公开的 locked/test 面板。下表只放入能明确对应的项目。官方报告以三位小数呈现，因此本表用于规模判断，不应解读为小数点后差异的精确显著性检验。")
    official = {"decision-v7": 0.838, "transfer-v4": 0.697, "hard-v1": 0.665, "documents-v1": 0.851}
    official_rows = []
    for name, off in official.items():
        ours = q35[name]["acc"]
        official_rows.append([name, f"{ours*100:.2f}%", f"{off*100:.1f}%", f"{(ours-off)*100:+.2f}", "可直接对齐的同名面板"])
    official_rows.append(["devtools-v1", "65.17%", "63.7%", "+1.47", "本次去除重复 ID 后 1,071 题；官方也为 1,071 题"])
    official_rows.append(["transfer-v9", "61.38%", "—", "—", "模型卡未给出可直接对应的 locked 总分"])
    add_table(doc, ["同名面板", "本次 Qwen3.5", "官方 Kev", "差值 pp", "可比性说明"], official_rows, widths=[1.05, 1.02, 0.83, 0.7, 2.7], font_size=8.2)
    add_heading(doc, "5.1 为什么 devtools 要单列口径", 2)
    add_body(doc, "冻结的 devtools-v1 test.jsonl 含 1,073 题；其中 CodeReviewer 的记录 ID `codereviewer/cls-test/19245` 重复出现两次。官方公开对照排除两题，故分母为 1,071。本次 Qwen3.5 原始分数为 65.14%（699/1,073）；按相同 ID 排除规则重算为 65.17%。内部 Qwen3/Qwen3.5 对比则保持原始 1,073 题，避免只改动其中一次运行。")
    add_heading(doc, "5.2 复现边界", 2)
    add_bullet(doc, "官方成品使用的是另一轮训练后选定的 checkpoint；本次从基座重新训练 LoRA 与 head，因此不能期待权重哈希、逐题预测或耗时完全一致。")
    add_bullet(doc, "公开记录中的官方环境包含 H100/H200、Python 3.13、glibc 2.36；本次是 A800、Python 3.12 与兼容加载器。硬件、内核和依赖差异均可能影响速度和随机训练轨迹。")
    add_bullet(doc, "四个直接可比面板相差 +0.20 至 −1.86 pp。该范围说明配方能在本环境跑通并接近公开量级，但不足以证明官方结果被精确复现。")

    add_page_break(doc)
    add_heading(doc, "六、结论、限制与下一步", 1)
    add_heading(doc, "6.1 可操作结论", 2)
    add_bullet(doc, "若目标是当前 Kev 测试集上的质量，选择 Qwen3.5-0.8B：六项留出面板全部领先 Qwen3-0.6B，尤其 hard-v1 增益明显。")
    add_bullet(doc, "若资源或迭代时间优先，Qwen3-0.6B 是可用的低成本版本：在相同训练配方下节省约 21.5% 训练时长与显存，但绝对准确率较低。")
    add_bullet(doc, "Qwen3.5 的 stage3 较慢不能简单归因于系统版本；日志确认 causal_conv1d 的参考实现回退是潜在因素，但需要同模型、同数据、仅改变内核的对照才能量化。")
    add_heading(doc, "6.2 当前限制", 2)
    add_bullet(doc, "每个基座只有一轮 seed=2 运行；未进行多 seed、配对显著性检验和完整消融。")
    add_bullet(doc, "没有在本环境直接评测官方发布的 adapter/head；因此“与官方对比”是公开指标对照，不是同机基线。")
    add_bullet(doc, "缺少 breadth、tasksource-heldout、longdoc、documents-v2 等未运行面板；结论只覆盖本报告列出的六个公开测试套件。")
    add_heading(doc, "6.3 建议的后续验证", 2)
    add_bullet(doc, "补一个官方 adapter/head 的同环境只评测基线，再用完全一致的数据清洗口径比较。")
    add_bullet(doc, "至少增加两个独立随机种子，并对相同问题做 paired bootstrap 或 McNemar 检验。")
    add_bullet(doc, "在兼容环境安装 causal_conv1d 后，以固定 checkpoint 和固定输入测吞吐，再决定是否值得升级系统或更换镜像。")
    add_heading(doc, "附录：本报告的数据来源", 1)
    add_table(doc, ["证据", "归档位置", "用途"], [
        ["训练日志", "runs/replica-20261026/stageN-train.log；runs/qwen3-06b-20261026/stageN-train.log", "绘制 loss 曲线与核对最终日志点。"],
        ["训练指标", "两个 run 的 stageN/training_metrics.json", "时间、步数、token、峰值显存、数据拒绝/截断。"],
        ["评测报告", "两个 run 的 benchmarks/*/report.json", "准确率、ECE、NLL、Brier 与题数。"],
        ["官方参考", "https://huggingface.co/jaredpalmer/kev-0.8b/blob/main/README.md", "公开模型卡中的 locked/test 指标和训练配方。"],
    ], widths=[0.9, 3.65, 1.7], font_size=8.0)
    add_body(doc, "本报告由保存的本地实验产物重新汇总生成；图表和表格数值没有从人工转抄截图中提取。为了便于复查，生成脚本与所有输入日志均保留在本报告所在的归档目录。", after=0)

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
