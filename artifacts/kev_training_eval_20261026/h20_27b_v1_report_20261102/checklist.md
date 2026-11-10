# 实验检查表

## 研究设计

- [x] 实验目标已写明。
- [ ] 未找到训练前冻结的主指标阈值。 — 未做原因：现有归档中无 preregistration 文件。
- [x] 负结果和评测弱项已保留在报告中。

## 计算可复现性

- [ ] 完整代码 commit 未冻结。 — 未做原因：本次使用当前代码与未提交 distributed-LoRA 改动。
- [x] 随机种子已记录（seed=2）。
- [x] 训练数据、adapter、head、config、metrics 都有 SHA-256。
- [ ] 没有从新的干净目录做第二次完整重跑。 — 未做原因：本次只跑了单 seed 正式训练。

## 数据与预处理

- [x] 基座 revision、数据记录数和 SHA-256 已记录。
- [x] rejected/truncated 都已记录为 0。
- [x] none-pair 扩增导致 records seen 多于 requested records 已说明。
- [x] 六套评测使用冻结 manifest，评测副本的改动边界已保存。

## 建模

- [x] 基座、LoRA rank、学习率、batch、epoch、precision、max state 和 seed 已记录。
- [x] 六卡 effective batch=6 与官方 effective batch=8 的差异已披露。
- [ ] 4B/9B 不是同训练预处理和同数据预算。 — 未做原因：它们只用于描述性对比，不称受控 scaling。

## 数据泄漏

- [x] 训练数据是官方 B1-v2 数据，六套 test 没有被本次用于训练或选 checkpoint。
- [ ] 本次未重做 B1-v2 与六套 test 的全量近重复扫描。 — 未做原因：复现使用官方冻结数据与官方评测套件。

## 指标与不确定性

- [x] 每套准确率、分母和 clean 加权结果已报告。
- [ ] 没有 seed 间方差。 — 未做原因：只训练了 seed=2 一个 checkpoint。
- [ ] 未为本次与官方对比重算 paired bootstrap 区间。 — 未做原因：没有官方模型在本地的逐题 logits/rows。

## 泛化性

- [x] transfer-v4 和 transfer-v9 作为域外/迁移证据分开报告。
- [x] hard/devtools/documents 与 v2 的 trained-family 边界已说明。
- [x] 没有把单 seed、单训练配方的结果扩写成普遍结论。

