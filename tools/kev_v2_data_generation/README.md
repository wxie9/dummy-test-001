# Kev v2 公开近似重建：数据生成代码

这套代码生成 Kev corpus 中当前缺失的候选合成数据。它生成的是独立公开近似重建，**不是官方逐行数据，也不会匹配官方 SHA-256**。

## 生成范围

| family | 目标数 | 标签来源 | LLM用途 |
|---|---:|---|---|
| abstention | 3,530 | 缺失变量枚举与规则求解 | 不需要 |
| intent | 4,848 | 程序预设意图 | 生成自然用户表达 |
| long_doc | 6,042 | 程序化政策规则求解 | 渲染长政策和案例 |
| numeric | 3,684 | 精确数值计算 | 不需要 |
| retrieval | 2,772 | 程序控制证据位置 | 不需要 |
| rubric_judge | 7,288 | 程序预设winner和错误类型 | 生成候选回答 |
| tool_routing | 5,514 | 工具能力状态机 | 不需要 |
| hard_v1_extra | 6,000 | 程序化政策规则求解 | 渲染复杂政策和案例 |

LLM只写语言表面；标准答案在调用LLM前已经由程序确定。四个使用LLM的family默认都会再调用一次模型做忠实性审核，不通过的样本会拒绝并重试。

## API占位

代码使用 OpenAI-compatible `POST /chat/completions`。真实Key只从环境变量读取，不会写入记录、manifest或日志：

```bash
export DEEPSEEK_API_KEY='...'
export DEEPSEEK_BASE_URL='https://api.deepseek.com/v1'
export DEEPSEEK_MODEL='deepseek-v4-flash'
```

如果服务商给出的model ID或base URL不同，只修改环境变量即可。

## 先做dry run

```bash
python3 tools/kev_v2_data_generation/generate.py --family numeric --dry-run
python3 tools/kev_v2_data_generation/generate.py --family long_doc --dry-run
```

第一条打印一条求解器标注样本；第二条只打印将发送给LLM的prompt，不调用API。

## 小规模试跑

```bash
python3 tools/kev_v2_data_generation/generate.py \
  --family numeric --count 100 \
  --out-dir outputs/kev-v2-public-reconstruction/smoke

python3 tools/kev_v2_data_generation/generate.py \
  --family intent --count 32 --batch-size 8 --concurrency 2 \
  --out-dir outputs/kev-v2-public-reconstruction/smoke
```

生成器可恢复：再次运行会校验已有JSONL，只补缺失的稳定index。长任务默认每完成25个API批次原子保存一次，可用`--checkpoint-every`调整。单批API永久失败不会中断其他批次；LLM调用失败或校验失败的记录写入对应的`.rejected.jsonl`。

## 正式目标数量

规则生成部分不调用API：

```bash
for family in abstention numeric retrieval tool_routing; do
  python3 tools/kev_v2_data_generation/generate.py --family "$family"
done
```

需要DeepSeek API的部分：

```bash
for family in intent long_doc rubric_judge hard_v1_extra; do
  python3 tools/kev_v2_data_generation/generate.py \
    --family "$family" --batch-size 8 --concurrency 4
done
```

也可以使用`--all`，但正式生产建议逐family运行，便于单独抽样审查和控制费用。

## 审计

```bash
python3 tools/kev_v2_data_generation/audit.py \
  outputs/kev-v2-public-reconstruction/synthetic-v1/numeric.jsonl \
  --out outputs/kev-v2-public-reconstruction/synthetic-v1/numeric.audit.json
```

加入一个或多个冻结评测JSONL后会检查exact state hash和8-gram污染：

```bash
python3 tools/kev_v2_data_generation/audit.py DATA.jsonl \
  --heldout /path/to/hard-v1-test.jsonl \
  --heldout /path/to/devtools-v1-test.jsonl
```

这里的8-gram规则是我们的公开重建规则，不等于官方私有污染筛查实现。正式训练前仍需：人工抽查、完整held-out集合筛查、tokenizer长度预检、跨family去重和最终混合审计。

## DecisionPivot 薄弱类别定向 20K

这一部分与上面的 Kev corpus 近似重建分开保存。`pivot_spec.py` 固定45个细类的配额；其中两类现有候选已经过量，目标为0，因此实际生成43类、共20,000条。

先生成机器可复算的结构化 scaffold：

```bash
python3 tools/kev_v2_data_generation/generate_pivot_structured.py \
  --out outputs/kev-v2-pivot-augmentation/structured.jsonl --fresh
```

结构化层包含公开题目状态、语义选项、程序答案和求解轨迹。求解轨迹不会发送给语言模型；最终状态、期望总额和规则执行结果等派生答案也不会放入公开题面状态。

再用 DeepSeek 只渲染自然语言表面：

```bash
python3 tools/kev_v2_data_generation/render_pivot_deepseek.py \
  --input outputs/kev-v2-pivot-augmentation/structured.jsonl \
  --out outputs/kev-v2-pivot-augmentation/rendered.jsonl \
  --model deepseek-v4-flash --batch-size 8 --concurrency 4 \
  --checkpoint-every 1
```

每批先生成题面，再调用一次模型核对事实、数字、边界、逻辑连接词、例外、单位、图边和操作顺序。失败样本不会进入正式JSONL，而是写入`rendered.rejected.jsonl`；重复运行只补缺失ID。

离线测试不调用API：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/kev_v2_data_generation/test_pivot_generation.py
```

这套数据是基于 DecisionPivot 错误类型设计的定向训练候选，不是官方 Kev v2 私有训练数据。在 DecisionPivot 上的后续收益只能称定向补强回测，还需要不参与配额设计的独立评测集验证泛化。

