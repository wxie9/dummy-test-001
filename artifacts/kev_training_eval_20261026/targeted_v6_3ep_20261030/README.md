# Kev v6 固定数据三轮对照

保持v6的1500个情境、3440个子问、6000条回放、开发集和训练探针完全一致；两模型均从原stage3初始化。仅把训练轮数从1改为3，其余参数相同，OneCycle学习率计划相应延长至2814次更新。

动机：v6一轮后，多跳训练探针Qwen3为8→8/30、Qwen3.5为10→15/30，真实多跳均下降；概率训练探针也只小幅提高。这组对照检查训练样本是否能够进一步学会，并同时检查全部七类旧错题和新增错误。不预设增加训练量能解决问题。

不是从v6一轮权重接着训练。唯一情境数量仍为1500，三次遍历不记成4500个新情境。原三类已知歧义保持原样，现有诊断评测不是全新盲测。结果未完成前不作提升结论。


## Completed result

Both models completed all training and evaluation. Qwen3: 512 to 516/1000; Qwen3.5: 551 to 582/1000. The all-seven improvement objective is not achieved. Historical launch paragraphs above do not indicate a live job. See comparison-seven.json and the Chinese result-and-next-steps report.
