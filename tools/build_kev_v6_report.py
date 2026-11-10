#!/usr/bin/env python3
"""Build a source-backed Chinese report; never run an experiment."""
from pathlib import Path
import csv
import hashlib
import json
import re
from collections import Counter

import subprocess
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/kev_training_eval_20261026'
SRC = BASE / 'targeted_v6_20261030'
OUT = BASE / 'reports/v6_report_20261030'
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((SRC/'comparison-seven.json').read_text())['models']
manifest = json.loads((SRC/'manifest.json').read_text())
probe = json.loads((SRC/'train_probe_comparison.json').read_text())['models']
families = ['tool_routing','temporal','probability','insufficient','multihop','policy','injection']
names = dict(zip(families,['工具路由','时间与数值','概率','信息不足','多跳推理','长政策','提示注入']))
models = ['qwen3','qwen35']
model_names = ['Qwen3','Qwen3.5']
hashes = json.loads((SRC/'frozen_input_hashes.json').read_text())
for f in ['train.jsonl','development.jsonl','train_probe.jsonl']:
    assert hashlib.sha256((SRC/f).read_bytes()).hexdigest() == hashes[f]
for m in models:
    x=data[m]['seven_pooled']
    assert sum(data[m]['seven_categories'][f]['after_correct'] for f in families)==x['after_correct']
    assert x['after_correct']-x['before_correct']==x['repaired']-x['newly_wrong']

# Extract the actual archived training logs, not the early local pipeline snapshots.
loss = {}
with (OUT/'loss_points.csv').open('w',newline='') as out:
    w=csv.writer(out);w.writerow(['model','epoch','optimizer_step','total_steps','logged_ce'])
    for m in models:
        log=(SRC/'evidence/targeted_v6_20261030'/f'pipeline_{m}.log').read_text()
        pts=[(int(e),int(s),int(n),float(v)) for e,s,n,v in re.findall(r'ep(\d+) step (\d+)/(\d+) loss ([\d.]+)',log)]
        assert len(pts)==93 and pts[-1][1]==930 and pts[-1][2]==938
        loss[m]=pts
        for row in pts:w.writerow([m,*row])
drawing=Drawing(510,350)
for i,(m,title,col) in enumerate(zip(models,model_names,['#285B82','#B56B31'])):
    y=205 if i==0 else 45
    plot=LinePlot();plot.x=50;plot.y=y;plot.width=438;plot.height=105
    plot.data=[[(r[1],r[3]) for r in loss[m]]]
    plot.lines[0].strokeColor=colors.HexColor(col);plot.lines[0].strokeWidth=.9
    plot.xValueAxis.valueMin=0;plot.xValueAxis.valueMax=938;plot.xValueAxis.valueSteps=[0,200,400,600,800]
    plot.yValueAxis.valueMin=0;plot.yValueAxis.valueMax=1.2;plot.yValueAxis.valueSteps=[0,.3,.6,.9,1.2]
    plot.xValueAxis.labels.fontSize=9;plot.yValueAxis.labels.fontSize=9
    plot.yValueAxis.visibleGrid=True;plot.yValueAxis.gridStrokeColor=colors.HexColor('#DDDDDD');plot.yValueAxis.gridStrokeWidth=.4
    drawing.add(plot)
    drawing.add(String(50,y+120,title+'  |  93 logged windows',fontName='Helvetica-Bold',fontSize=11))
    drawing.add(String(8,y+49,'CE',fontSize=10))
drawing.add(String(215,12,'Optimizer step',fontSize=10))
renderSVG.drawToFile(drawing,str(OUT/'training_loss.svg'))
node='/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
sharp='/Users/chen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
subprocess.run([node,'-e',f"const sharp=require({json.dumps(sharp)});sharp(process.argv[1],{{density:240}}).png().toFile(process.argv[2]);",str(OUT/'training_loss.svg'),str(OUT/'training_loss.png')],check=True)

doc=Document();sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.68);sec.bottom_margin=Inches(.65)
sec.left_margin=Inches(.75);sec.right_margin=Inches(.75)
sec.header_distance=Inches(.28);sec.footer_distance=Inches(.3)
for sty in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption','Header','Footer']:
    s=doc.styles[sty];s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0)
    fonts=s.element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn('w:eastAsia'),'Songti SC' if sty=='Normal' else 'Heiti SC')
    for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
        fonts.attrib.pop(qn('w:'+attr),None)
    for border in list(s.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Subtitle'].font.italic=False
normal=doc.styles['Normal'];normal.font.size=Pt(11.5)
normal.paragraph_format.line_spacing=Pt(16.5);normal.paragraph_format.space_after=Pt(6)
for sty,size in [('Title',23),('Heading 1',17),('Heading 2',13),('Heading 3',11.5)]:
    s=doc.styles[sty];s.font.size=Pt(size);s.font.bold=True
    s.paragraph_format.space_before=Pt(10 if sty!='Title' else 0)
    s.paragraph_format.space_after=Pt(7)
    s.paragraph_format.keep_with_next=True
    s.paragraph_format.line_spacing=Pt(size*1.25)
doc.styles['Subtitle'].paragraph_format.line_spacing=Pt(19)
doc.styles['Caption'].font.size=Pt(9.5)
doc.styles['Caption'].paragraph_format.space_after=Pt(6)
for sty in ['Header','Footer']:
    doc.styles[sty].font.size=Pt(9)
hp=sec.header.paragraphs[0];hp.text='Kev v6 数据与续训实验报告';hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fp.add_run('2026 年 10 月 30 日   ·   ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld)

def p(t,style=None):
    return doc.add_paragraph(t,style)
def h(t,level=1):
    return doc.add_heading(t,level)
def page(t):
    doc.add_page_break();h(t)
def caption(t):
    return p(t,'Caption')
def table(headers,rows,widths=None,size=10):
    tb=doc.add_table(rows=1,cols=len(headers));tb.alignment=WD_TABLE_ALIGNMENT.CENTER;tb.autofit=False
    widths=widths or [7/len(headers)]*len(headers)
    for c,w in zip(tb.columns,widths):c.width=Inches(w)
    for cell,txt in zip(tb.rows[0].cells,headers):cell.text=str(txt)
    for row in rows:
        for cell,txt in zip(tb.add_row().cells,row):cell.text=str(txt)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'5');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    tb._tbl.tblPr.append(borders)
    for i,row in enumerate(tb.rows):
        trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
        if i==0:trpr.append(OxmlElement('w:tblHeader'))
        for j,(c,w) in enumerate(zip(row.cells,widths)):
            c.width=Inches(w);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
            for edge,v in [('top',65),('bottom',65),('left',85),('right',85)]:
                el=OxmlElement('w:'+edge);el.set(qn('w:w'),str(v));el.set(qn('w:type'),'dxa');mar.append(el)
            pr.append(mar)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'24465C' if i==0 else ('F1F4F6' if i%2==0 else 'FFFFFF'));pr.append(shade)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=Pt(size*1.3)
                para.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
                for run in para.runs:
                    run.font.size=Pt(size);run.font.bold=(i==0)
                    run.font.color.rgb=RGBColor.from_string('FFFFFF' if i==0 else '000000')
    spacer=p('')
    spacer.paragraph_format.line_spacing=Pt(4)
    spacer.paragraph_format.space_after=Pt(2)
    return tb

p('Kev v6 数据生成与续训实验报告','Title')
p('Qwen3 与 Qwen3.5 的七类弱项定向续训','Subtitle')
p('实验日期 2026 年 10 月 30 日   文档范围 v6 原版一轮及两个已完成对照')
h('1 实验范围与主要结果')
p('本报告记录 v6 如何生成训练数据、如何分配七类题、如何续训，以及续训前后的逐题结果。主实验是从原始 Kev stage3 检查点出发的一轮续训：Qwen3 使用 0.6B Base，Qwen3.5 使用 0.8B Base。基线是我们原先训练好的 Kev，并非未经 Kev 训练的 Qwen 原始模型，也不是 Kev 官方发布检查点。[S1–S3]')
p('v6 没有实现两个模型七类都提升。Qwen3 在七类真实测试题上从 512/1000 降到 509/1000；Qwen3.5 从 551/1000 升到 585/1000，但概率、多跳和时间题仍下降。Qwen3.5 的主要收益集中在工具路由和提示注入。合成开发集改善明显大于真实测试题改善，不能据此称为普遍能力提升。')
h('1 1 数据规模与配比',2)
rows=[]
for f in families:
    n=manifest['files']['train']['families'][f];q=manifest['files']['train']['subquestions_by_family'][f]
    rows.append([names[f],n,q,f'{n/15:.2f}%',f'{n/75:.2f}%'])
rows += [['定向数据合计','1500','3440','100.00%','20.00%'],['旧训练数据回放','6000','7426','—','80.00%'],['训练输入总计','7500','10866','—','100.00%']]
table(['类别','情境数','子问数','定向情境占比','全部情境占比'],rows,[1.55,.85,.85,1.8,1.95])
p('训练配比为定向数据∶回放数据＝1∶4，两个模型使用同一份输入。1500 指不同可见情境，不是 1500 个独立统计样本：其中含配对案例，共 1210 组。一个情境可有多个子问；子问数和梯度权重也不等价。另有开发集 336 个情境、770 个子问、271 组，不参与训练。[S1、S4]')

page('2 数据生成原则与保留类别')
p('v6 的生成方式是先设计可计算的情境、规则和反事实变化，再用固定种子的程序实例化题目，由规则求解器产生答案，并从可见题面复算。Codex 的工作主要是分析错误类型、编写题目规则、干扰项和校验代码；没有调用外部教师 LLM 对每一道题自由生成答案，也没有训练自然语言思维链。题面主要为英文，下文例子为中文说明。[S5]')
p('七类不是各取一道真实错题反复改数字。它们覆盖多种决策规则；但覆盖仍由有限模板限定。真实 hard-v1 错题曾用于诊断与设计，因此本报告把正式测试上的结果当作已知测试分布的改进证据，不作为全新盲测。')
h('2 1 三类原样保留',2)
table(['类别','训练情境与细分','v6 处理'],[
 ['工具路由','求和 31；预约 25；兑换 24；物流 20','100 条原样保留'],
 ['时间与数值','按比例退款 28；时区 28；滞纳金 22；截止时间 22','100 条原样保留'],
 ['提示注入','网页 24；邮件 22；工具结果 22；JSON 字段 18；代码注释 14','100 条原样保留'],
],[1.2,4.3,1.5])
p('这三类训练共 300 条、开发共 90 条，与上一版保留行逐字一致；没有重新生成、改标签或调整日期边界。工具题要求按工具能力和参数选择行动；时间题进行日期、时区或费用计算；注入题区分正常内容与越权指令。它们原有的质量问题也随之保留。已知 28 条退款训练题及 12 条开发题的 through 结束日表述存在边界歧义，本版按用户要求未修订，不能称为全量语义审核通过。')
h('2 2 概率题的生成与标注',2)
p('350 个情境包含：条件频数表 75、贝叶斯反推 60、全部成功 40、至少一个失败 50、至少一个成功 25、概率比较 40、期望收益 60，共 720 个子问。独立事件题覆盖 2–5 个组成事件；概率覆盖低、中、高区间，包括接近 0% 与 100% 的情况。频数表和期望收益将数量或金额按 1、10、100、1000、10000 倍缩放，检验同一运算在不同量级下的表现。')
p('答案用精确分数计算，再按题目要求舍入；“全部成功”用成功率连乘，“至少一次”用相反事件的补集，贝叶斯题区分先验、命中率与误报率。部分题同时问数值、概率区间或是否超过 50%。干扰项包括反向条件、补事件和错误分母等，不直接写死选项字母。')
p('实际例子：垃圾邮件占 1%，真垃圾被标记概率为 80%，非垃圾被误标记概率为 5%。从被标记邮件中抽一封，垃圾邮件的后验概率为 0.01×0.80 ÷ (0.01×0.80＋0.99×0.05)＝13.91%。该情境另标注区间 [10%, 30%)，以及“是否更可能是垃圾邮件”为否。来源末级 ID 为 train/bayes/25。')

page('3 信息不足与多跳数据')
h('3 1 信息不足通过多个问法监督同一决定',2)
p('本类复用 v5 的 280 个可见情境和语义答案，覆盖退货、审批、任职年限、配送、加班、保修、价格匹配七个场景，每场景 40 条。每个场景有完整事实 20 条、缺失决定性事实 16 条、缺失非决定性事实 4 条；合计为 140、112、28 条，构成 140 组配对。新增的是监督问法，并非新增了 280 个业务场景。')
table(['同一情境的子问','监督内容'],[
 ['原始决定','满足／不满足／无法确定'],
 ['具体行动','如批准退货／不批准／事实不能决定'],
 ['简短决定','Yes／No／Cannot be determined'],
 ['证据是否足以支持肯定','必须是保证为真，而非仅有可能'],
 ['证据是否足以支持否定','必须是保证为假，而非仅有可能'],
],[1.9,5.1])
p('每条情境 5 个子问，共 1400 个，其中选择题 840、布尔题 560。标注时枚举与已知事实一致的合法补全：若所有补全结论相同，则可决定；若存在相反结论，则标为无法确定。缺少非决定性字段时仍应给出确定答案。')
p('实际例子：退货须在签收后 30 个自然日内提出；订单日为 2027-11-30，退货申请日为 2028-01-23，只知道签收发生在二者之间。签收当天申请可以合格，若订单当天签收则相隔 54 天、不合格，因此三个决定问法均标为无法确定，两个“是否保证”均为否。来源 v5 原情境编号为 insufficient/train/000007。')
h('3 2 多跳补充不同关系规则',2)
table(['机制','情境数','子问数'],[
 ['控制权与经济权益','90','180'],['带日期的资产值班表','60','120'],
 ['沿主管关系走指定跳数','30','30'],['依赖传播','45','45'],['按职级向上审批','45','45'],
 ['合计','270','420'],
],[4.4,1.3,1.3])
p('其中 180 条为新增情境，依赖传播和职级审批共 90 条由旧 v5 按固定种子抽取。指定跳数为 2、3 或 4，禁止用职级或可用性替代跳数规则；值班题先查资产归属，再按事故日期查缺勤区间，依次选择首联系人、替补和负责人。控制权按超过 50% 的投票权反复求闭包，经济权益则沿所有持股路径乘积求和，二者分开标注。')
p('实际例子：要求从 Violet 沿主管边走恰好两次。关系为 Violet→Sienna→Hazel，另混入其他主管边；正确审批人为 Hazel，而不是第一跳 Sienna。来源末级 ID 为 train/exact_supervisor_hops/00010。')

page('4 长政策数据与质量检查')
h('4 1 长政策保留情境并修订候选答案',2)
p('长政策复用 v5 的 300 个情境、150 组配对，每个情境同时回答赔付金额和处理结果，共 600 个子问。配对围绕扣除与封顶顺序、阈值边界和多项拒付优先级构造：顺序变化 120 条、边界变化 120 条、多拒付条件 60 条。按实际金额标签统计，正金额 180 条、零金额 120 条；不能直接把元数据中的 subtype 当作最终支付标签。')
p('v6 把同一对情境原先不同的候选金额取并集，纳入两边正确答案和已有干扰项，再固定打乱。这样原始 JSON 中，两题的选项值、键和顺序一致，避免模型只利用选项差异判断答案。实际训练还会独立做随机增强，因此“配对选项一致”只对冻结输入文件成立。')
p('处理结果由简短原因名改为与该事件、物品和保障编号对应的完整描述。八种原因包括按损失支付、总限额封顶、部件限额封顶，以及未购买、等待期、使用量超限、不安全保管、超期报案等拒付情况。求解器先按可见政策执行拒付优先级，再计算损失、免赔额与各项上限，核对金额和处理结果两个标签。')
p('实际例子：某烤箱电路故障损失为 $2316，相关保障上限 $2000，免赔额 $75；该条款先封顶、再扣除免赔额，且无拒付条件，金额答案为 $1925，处理结果为按该项保障上限赔付。该条训练记录的旧 subtype 是 not_purchased，但配对后的事实已购买保障，说明必须查看实际题面和标签。来源 v5 原情境编号为 policy/train/000471。')
h('4 2 标签与数据隔离检查',2)
table(['检查项','冻结结果'],[
 ['训练与开发情境完全重复','0 条'],['训练与开发配对组重叠','0 组'],
 ['与 4923 个冻结测试情境完全重复','0 条'],
 ['四类训练标签扰动检查','3140 次错误标签替换均被拒绝'],
 ['四类开发标签扰动检查','680 次错误标签替换均被拒绝'],
 ['原三类保留行与政策原始选项配对','逐行保留检查通过；配对选项一致'],
 ['训练输入预检','7500 情境；10866 子问；开发无拒绝'],
],[3.8,3.2])
p('校验程序从可见题面重新取数和读取规则，不以隐藏 facts 或已存答案直接证明标签正确。生成与复核由同一作者编写，采用分开的实现，但不等同于外部独立语义审查。每个改写子问只替换测试一个错误标签，并未穷举所有错误候选。[S1、S4、S5]')
p('完全重复为零不代表语义无重叠，也不代表没有模板偏差。开发集与训练集共享生成规则；信息不足的五个问法和政策配对高度相关。v6 增加了子问数量，又同时改变了覆盖、选项和措辞，不是等子问数的单因素消融。')

page('5 模型与续训方法')
p('两模型都从首次 Kev 三阶段训练完成后的 stage3 继续训练，加载原 LoRA adapter 和 pointer head；没有接着 v5、v6 或其他定向续训的 stage4 再训练。基座权重冻结，可训练部分为 LoRA 与 256 维 pointer head。本次是监督式决策训练，使用 Transformers／PyTorch Kev 实现，不是 RL 或全参数微调，也不依赖 vLLM。[S2、S6]')
table(['设置','实际值或含义'],[
 ['基座','Qwen3-0.6B-Base；Qwen3.5-0.8B-Base'],
 ['初始化','分别加载本模型原 stage3 adapter 与 head'],
 ['LoRA','rank 16；targets=all；placement=full'],
 ['可训练参数','Qwen3 约 10.6M；Qwen3.5 约 11.3M'],
 ['优化器与学习率','AdamW；峰值 LR 1e-5；weight decay 0.01'],
 ['Head 学习率','head_lr=0 表示沿用 LR 1e-5，不是冻结'],
 ['调度与裁剪','OneCycleLR；pct_start=0.1；梯度范数上限 1.0'],
 ['轮数与随机种子','1 epoch；seed 101'],
 ['批量与梯度累积','batch 4 × accum 2；通常每次更新 8 条原始记录'],
 ['优化器更新','938 次；最后一次覆盖 4 条原始记录'],
 ['精度与内存','BF16 计算；weights_dtype=fp32；梯度检查点开启'],
 ['上下文预算','max_state 7552；branch 8192；packed 9216'],
 ['附加损失','perm_kl、ord_w、anchor_w、平滑、Brier、focal 均为 0'],
],[1.7,5.3],size=10.3)
h('5 1 数据回放与损失计算',2)
p('回放从 decision-v7 的训练分区 12576 条记录中，用 random.Random("replay:101") 固定抽取 6000 条，与 1500 条定向数据混合、按轮打乱。两模型输入一致，回放用来维持原任务分布。并没有额外生成 6000 条新题。')
p('输入类型包括 choice 候选选择、noul 布尔判断、score 有序区间。各子问均按正确候选计算交叉熵；同一增强变体内部先对子问取平均，再汇总并按当前累积组和增强量归一化。score 也没有额外排序损失，因为 ord_w=0。因此信息不足虽然占 1400/3440 个定向子问，不能直接说它占相同比例的训练梯度。')
h('5 2 训练增强',2)
p('p_none=0.10、p_none_distract=0.12、p_distract=0.15、p_none_pair=0.25，synthetic_repeat=1。增强可更换或打乱选项、引入 none 对照。45 个已带显式 none 答案的多跳子问增加 one-hot target 保护，避免生成重复的等价 none 候选；其事实、问题和语义答案不变。增强后的记录曝光数为 9498，而原始输入仍是 7500 条。')

page('6 训练过程与实际耗时')
rows=[]
for key,label in [('requested_records','原始记录曝光'),('records_seen','含增强变体的曝光'),('optimizer_steps','优化器更新'),('forward_tokens','前向 token 计数')]:
    rows.append([label,*[f"{data[m]['training'][key]:,}" for m in models]])
rows += [['训练阶段耗时','14 分 29 秒','16 分 58 秒'],['记录的峰值设备内存',*[f"{data[m]['training']['peak_device_bytes']/2**30:.2f} GiB" for m in models]],['截断／拒绝记录','0／0','0／0']]
table(['指标','Qwen3','Qwen3.5'],rows,[3.2,1.9,1.9])
p('两次训练分别使用一张 A800，均完成 938 次更新。耗时来自训练代码的 wall_seconds（868.914 秒、1017.575 秒），包含该阶段保存操作，不包含前后评测。内存数字为训练代码记录的设备分配量，不等同于 nvidia-smi 的整卡占用。')
doc.add_picture(str(OUT/'training_loss.png'),width=Inches(5.85))
doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
caption('图 1  原版 v6 一轮训练的交叉熵日志。上下图共用纵轴尺度；未平滑。')
p('每 10 次更新记录一个窗口，窗口内为增强变体的平均子问交叉熵；两模型各 93 个点，覆盖 step 10–930。总更新为 938，最后 8 次没有单独 loss 日志，图中没有补点。曲线来自完整归档日志，不是较早保存的本地 pipeline 快照。[S6]')
p('曲线随批次组成波动，不能把最后一个窗口值当作全量训练集损失，也不能把它当作验证损失。训练顺利完成只表明优化过程可运行，是否改善目标能力由下一节的冻结评测决定。')

page('7 真实测试题上的前后对比')
p('七类目标子集来自 hard-v1 与 devtools-v1，共 800 个情境、1000 个子问；同一题按前后检查点配对，使用 argmax 选项答案。未把合成开发题混入此表。表中准确率按子问计算，pp 为百分点；“前”均指原 stage3。[S3]')
rows=[]
for f in families:
    a=data['qwen3']['seven_categories'][f];b=data['qwen35']['seven_categories'][f]
    rows.append([names[f],a['questions'],f"{a['before_pct']:.2f}→{a['after_pct']:.2f}",f"{a['delta_pp']:+.2f}",f"{b['before_pct']:.2f}→{b['after_pct']:.2f}",f"{b['delta_pp']:+.2f}"])
rows.append(['七类合计',1000,'51.20→50.90','−0.30','55.10→58.50','+3.40'])
table(['类别','题数','Qwen3 前→后 %','变化 pp','Qwen3.5 前→后 %','变化 pp'],rows,[1.12,.5,1.7,.65,1.85,1.18],size=9.7)
h('7 1 原错题修复和新增错误',2)
rows=[]
for m,label in zip(models,model_names):
    x=data[m]['seven_pooled'];rows.append([label,x['old_wrong'],x['repaired'],f"{x['repair_pct']:.2f}%",x['newly_wrong'],f"{x['after_correct']-x['before_correct']:+d}"])
table(['模型','原错题','修复','原错题修复率','原对变错','净增正确'],rows,[1.1,.8,.65,1.9,1.2,1.35])
p('Qwen3 修复 43 道，同时新增 46 道错误，净少 3 道；Qwen3.5 修复 57 道，同时新增 23 道错误，净多 34 道。只统计错题转对会高估收益。Qwen3.5 的工具与注入两类各净增 18 道，其余五类合计净少 2 道。')
h('7 2 完整测试集结果',2)
rows=[]
for suite in ['hard-v1','devtools-v1']:
    for m,label in zip(models,model_names):
        x=data[m]['suite_overall'][suite];rows.append([suite,label,x['questions'],f"{x['before_pct']:.2f}→{x['after_pct']:.2f}",f"{x['delta_pp']:+.2f}"])
table(['测试集','模型','子问数','准确率前→后 %','变化 pp'],rows,[1.3,1.15,.8,2.35,1.4])
p('完整 hard-v1 上两个模型均下降；Qwen3.5 的总体收益集中在 devtools-v1。此处是固定子问准确率，不能与旧报告中的类别宏平均或 Kev 官方卡片分数直接拼接比较。devtools 原始数据包含重复 ID，按出现序号保留并配对，没有删题；该重复不属于七类目标子集。')

page('8 哪些能力改善以及哪些仍未学会')
h('8 1 四类重点问题的细分结果',2)
table(['真实测试细类','题数','Qwen3 正确数','Qwen3.5 正确数'],[
 ['信息不足且确实无法决定',39,'36→38','34→38'],
 ['事实足够可以决定',61,'30→23','35→32'],
 ['多跳中的依赖传播',26,'13→8','17→13'],
 ['多跳中的值班查询',25,'8→7','7→10'],
 ['政策中的正金额计算',35,'16→14','17→16'],
 ['对应正金额案例的处理结果',35,'8→9','8→10'],
 ['政策中的零金额计算',65,'65→65','65→65'],
 ['反向条件概率',11,'2→2','1→1'],
],[3.2,.6,1.6,1.6])
p('信息不足：两个模型更容易在未知时保留判断，却也更容易对信息足够的题拒绝判断。多问法监督尚未形成平衡，Qwen3 的类别总分因此下降。多跳：依赖传播是主要退步来源；本版把依赖情境从 90 减到 45，是待验证的影响因素，但同时修改了其他数据，无法单独归因。')
p('长政策：Qwen3.5 的净增主要来自处理结果，正金额计算反而少对一道，不能称为金额推理改善。概率：增加量级和概率区间覆盖后，真实题没有收益，反向条件概率仍很差。现有证据说明这些能力没有得到稳定改善，不足以断言某一种模板或训练参数是唯一原因。[S7]')
h('8 2 合成训练探针与开发集',2)
table(['类别','Qwen3 训练探针','Qwen3.5 训练探针','Qwen3 开发','Qwen3.5 开发'],[
 [names[f],*[f"{probe[m]['families'][f]['before_correct']}→{probe[m]['families'][f]['after_correct']}/{probe[m]['families'][f]['questions']}" for m in models],*[f"{data[m]['development']['by_family'][f]['before_correct']}→{data[m]['development']['by_family'][f]['after_correct']}/{data[m]['development']['by_family'][f]['questions']}" for m in models]]
 for f in ['probability','insufficient','multihop','policy']
],[1,1.5,1.6,1.4,1.5],size=9.7)
p('训练探针来自训练集，每类固定抽 20 个情境，共 140 情境、268 子问，只回答“这批训练题是否学会”，不代表泛化。Qwen3 多跳探针仍为 8/30，因此不能一概解释为“训练题都学会了，只是迁移失败”。Qwen3.5 在合成政策和信息不足上的改善较大，但没有等比例迁移到真实题。[S7]')
p('全部开发子问上，Qwen3 从 309/770 升到 378/770（40.13%→49.09%），Qwen3.5 从 341/770 升到 480/770（44.29%→62.34%）。这说明模型能适应部分生成分布；由于开发与训练共享模板，不能用开发提升替代真实测试结果。')

page('9 已完成对照与结论边界')
p('以下是已完成实验的回顾，不是本次重新启动的训练。v6 原版一轮是本报告主结果；三轮版和事实表达改写版独立列出，避免混用。三轮版从原 stage3 重新开始，不是在一轮成品上再接两轮。[S8]')
table(['版本','与主实验的区别','Qwen3 七类','Qwen3.5 七类'],[
 ['原 stage3','续训前基线','512/1000','551/1000'],
 ['v5 增强修复对照','上一版数据，同为 1500 定向情境、一轮','514/1000','584/1000'],
 ['v6 原版一轮','本报告主实验','509/1000','585/1000'],
 ['v6 三轮','固定 v6 数据与初始化，只将 epoch 改为 3','516/1000','582/1000'],
 ['v6 事实表达改写','140 条信息不足情境改句式，事实与标签保持','504/1000','584/1000'],
],[1.3,3.1,1.3,1.3],size=10)
p('相对 v5 增强修复对照，v6 主实验在 Qwen3 少对 5 道、Qwen3.5 多对 1 道，没有表现出明确的整体优势。三轮相对一轮，Qwen3 多对 7 道、Qwen3.5 少对 3 道；单纯增加训练轮数没有让两个模型共同改善。只改变事实表达也未优于主实验。')
h('9 1 可以支持的结论',2)
p('第一，v6 使 Qwen3.5 在指定七类测试的合计准确率增加 3.4 个百分点，主要由工具路由和提示注入贡献。第二，Qwen3 的同口径合计结果没有改善。第三，合成数据上的学习与真实测试表现存在差距，其中信息不足的保留判断倾向、政策的正金额计算和多跳依赖传播仍是明确问题。')
h('9 2 不能支持的结论',2)
p('不能据此声称七类均改善、通用能力全面提升、优于 Kev 官方模型，或确定数据生成中的某个改动导致了涨跌。两个模型都只报告 seed 101；没有多种子重复。测试题已参与此前错误分析，开发集又共享生成规则，因此目前没有独立新分布泛化证据。')
p('按情境成组重采样的七类合计准确率变化 95% bootstrap 区间：Qwen3 为 −2.09 至 +1.58 pp；Qwen3.5 为 +1.65 至 +5.23 pp。区间反映这组冻结题的抽样波动，不覆盖训练随机性；14 个模型与类别比较未进行多重比较校正。')
h('9 3 对后续决策的含义',2)
p('这版可以作为可追溯的实验检查点保留，不能替代原 stage3 成为两个模型共同的默认版本。若未来恢复实验，应分别检查数据覆盖、证据充分性与损失权重，而不是仅按开发集分数或训练完成状态选择版本。当前实验保持暂停，本次只整理既有证据，没有新启动训练或评测。')

page('10 复核路径与文件索引')
p('本报告全部数值来自本地冻结记录和归档的实际训练代码。manifest.json 的 status 保留了组装阶段的旧状态；是否完成以训练指标、完整预测及 run_status 等后续证据为准。报告没有将旧状态误读为尚未训练。')
p('本地证据根目录为 procogs/artifacts/kev_training_eval_20261026/targeted_v6_20261030。下面文件名相对此目录；生成脚本以 procogs/tools 为根。服务器根目录为 /C20545/kev-08b-official-repro-20261026。',None)
h('10 1 主要证据',2)
sources=[
 ('S1 数据与配比','manifest.json；train.jsonl；development.jsonl；train_probe.jsonl；frozen_input_hashes.json。提供情境、子问、分组、保留行及输入哈希。'),
 ('S2 训练参数与初始化','evidence/runs/qwen3-20261030-targeted-v6/stage4/ 与 qwen35-20261030-targeted-v6/stage4/ 下的 training_config.json、training_metrics.json。'),
 ('S3 真实测试结果','comparison-seven.json、comparison-seven.csv、paired-seven.jsonl。包含七类与完整测试、逐题对错转换及 bootstrap 区间。'),
 ('S4 输入预检与增强','preflight_qwen3.json、preflight_qwen35.json、none_guard_records.json、none_augmentation_with_replay.json。'),
 ('S5 数据生成与规则复算','tools/build_targeted_v6.py；build_kev_probability_coverage_candidate.py；build_kev_insufficient_multiview_candidates.py；build_kev_multihop_coverage_candidates.py；build_kev_policy_fixed_options_candidate.py。'),
 ('S6 实际代码与训练日志','evidence/stages/stage3/kev/train.py；evidence/targeted_v6_20261030/pipeline_qwen3.log 与 pipeline_qwen35.log。loss 曲线仅使用这两份完整归档日志。'),
 ('S7 学习与机制诊断','all_seven_mechanism_diagnostics.json、train_probe_comparison.json、development_pair_diagnostics.json。'),
 ('S8 已完成对照','relative_to_v5_guard.json；同级 targeted_v6_3ep_20261030/ 与 targeted_v6_factmix_candidate_20261030/ 下的 comparison-seven.json。'),
]
for title,body in sources:
    para=p('');r=para.add_run(title+'  ');r.bold=True;para.add_run(body)
    para.paragraph_format.space_after=Pt(5)
    for r in para.runs:r.font.size=Pt(10)
h('10 2 输入与归档校验',2)
for label,value in [('train.jsonl',hashes['train.jsonl']),('development.jsonl',hashes['development.jsonl']),('v6-verified-evidence.tar.gz','4e833233af5596a368c55e11b720210c950f876b7a2c3950ae3b01e36ab1b980')]:
    para=p(label+'  SHA256');para.paragraph_format.space_after=Pt(0)
    para=p(value);para.paragraph_format.space_after=Pt(5)
    for r in para.runs:r.font.size=Pt(8.5);r.font.name='Courier New'
p('归档中的 84 个索引文件此前已逐一核验。模型权重保留在服务器对应 runs/<模型>-20261030-targeted-v6/stage4，证据包记录检查点哈希；本地报告不包含权重。报告生成时再次核对三份输入 JSONL 的 SHA256，未改动实验输入。')

doc.core_properties.title='Kev v6 数据生成与续训实验报告'
doc.core_properties.subject='七类定向数据配比、LoRA 续训与配对评测'
doc.core_properties.author='Chen'
doc.core_properties.keywords='Kev,v6,Qwen3,Qwen3.5,LoRA,定向续训'
final=OUT/'Kev_v6数据生成与续训实验报告.docx'
doc.save(final)
(OUT/'report_sources.json').write_text(json.dumps({'scope':'v6 original 1 epoch; completed controls separately','source_root':str(SRC),'input_sha256':hashes,'loss_points':{m:len(v) for m,v in loss.items()},'report':str(final),'no_training_or_evaluation_launched':True},ensure_ascii=False,indent=2)+'\n')
print(final)
