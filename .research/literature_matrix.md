# DeepWide × 信息熵文献比较矩阵

检索截止：2026-07-19。矩阵只纳入对研究设计有直接约束的核心工作；完整检索范围、方法和引用见 `survey.md`。

| 工作 | 被建模的随机变量/状态 | 估计器或核心机制 | 控制用途 | 是否训练 | 开放集覆盖 | 对本项目的约束 |
|---|---|---|---|---|---|---|
| DeepWideSearch (2510.20168) | 隐藏核心实体与目标表 | depth/width 交织基准及表格指标 | 评测 | 否 | 是，但不估计遗漏质量 | 主基准；必须分 Deep2Wide 与 Wide2Deep 报告 |
| Table-as-Search (2602.06724) | 外部表格中的行、列、空单元格 | 表格作为持久搜索状态 | 规划、补行、补格 | 否 | 用空格表示缺口，无概率覆盖 | “表即状态”不是新颖点 |
| A-MapReduce (2602.01331) | 横向检索子任务及经验 | 自适应 MapReduce 与经验记忆 | 大规模宽搜 | 否 | 启发式任务分解 | 强系统基线；比较相同预算和骨干 |
| Web2BigTable (2604.27221) | 大表构建子任务 | 双层多智能体搜索与抽取 | 宽搜、聚合 | 否 | 面向大规模表，但无遗漏后验 | 宽搜强基线 |
| WebSwarm (2607.08662) | 递归搜索节点、局部模式、网页结构 | progressive delegation；atom/deep/wide/entity_collect | 动态深宽切换 | 否 | 处理 open-set enumeration，但为 LLM 定性判断 | “动态深宽路由”不是新颖点；可作为执行器 |
| SearchOS (2607.15257) | Frontier、Evidence Graph、Coverage Map、Failure Memory | 持久共享状态、middleware、scope audit | 覆盖驱动调度与停滞恢复 | 否 | 显式区分 cell saturation 与 row scope | “coverage map/持久状态”不是新颖点；需比较遗漏风险而非已知格覆盖 |
| Semantic Entropy (2302.09664；Nature 2024) | 自由文本答案的语义等价类 | 多样本语义聚类后的熵 | 被动错误/幻觉检测 | 否 | 有限采样答案集 | 提供 cell/anchor 语义熵候选估计器，不提供 controller |
| FLARE (2305.06983) | 下一句 token 置信度 | 低置信 token 阈值 | 触发检索 | 否 | 否 | 低成本 heuristic baseline |
| Self-RAG (2310.11511) | 是否检索、证据相关性与支持性 | 学得的 reflection tokens | 检索、生成、批判 | 是 | 否 | adaptive retrieval 基线，不等同熵 |
| Dartboard/RIG (2407.12101) | 检索集合中与查询相关的信息 | relevant information gain | 去冗余选 passage | 否 | 否 | 多样性/相关性基线，不是任务信念 EIG |
| SePer (2503.01478) | 答案正确性的模型内部信念 | retrieval 前后 semantic perplexity reduction | 离线评估检索效用 | 否 | 否 | “检索后不确定性下降”已被研究 |
| CuriosiTree (2506.09173) | 诊断/决策假设 | tree search 近似 EIG/成本 | 测试时选择信息获取动作 | 否 | 有限动作与诊断假设 | EIG-per-cost 不是新颖点；DeepWide 分层信念才可能新 |
| Conformal Information Pursuit (2507.03279) | 交互预测标签 | conformal prediction-set size 近似条件熵上界 | 下一问题与停止 | 否 | 有限标签集；需校准集 | 说明原始 LLM 概率失校准；必须做概率校准/覆盖审计 |
| IGPO (2510.14967) | gold answer 的模型概率 | 每轮 gold-answer probability 增量 | RL 稠密奖励 | 是 | 否 | 训练信号；运行时无 gold 时不能照搬 |
| QuCo-RAG (2512.19134) | 模型知识缺口 | 预训练语料实体频率/共现 | 动态触发检索 | 否 | 长尾实体但非结果集遗漏 | 内部 logits/entropy 可能过度自信；必须与外部统计比较 |
| InfoReasoner (2602.00845) | 语义答案分布 | 双向蕴含聚类后的语义 IG | RL 检索奖励 | 是 | 有限答案采样 | 语义熵下降作为训练奖励已存在 |
| TEPO (2602.02050) | 工具调用前后 token 段熵 | delta segment entropy | RL 工具调用奖励 | 是 | 否 | “奖励降低熵的工具调用”已存在；token 熵不是事实正确性 |
| SIGHT (2602.11551) | 检索状态的自证据/信息量 | IG 驱动分支、去重、反思 | RL 搜索策略 | 是 | 否 | IG 驱动搜索分支已存在 |
| ECR (2603.28444) | 有限竞争答案假设 | Shannon entropy、EER proxy、coherence gate | 推理时选证据和停止 | 否 | 否；真答案缺席可低熵错收敛 | 最直接近邻；新方法必须显式建模 OTHER/未见质量和表级层次 |
| IG-Search (2604.15148) | gold answer 的 likelihood | 真文档相对随机文档的 log-likelihood ratio | RL step reward | 是 | 否 | 作者明确称其不是 Shannon IG；术语需精确定义 |
| WebUncertainty (2604.17821) | 任务规划与网页动作不确定性 | verbalized/采样 UQ + MCTS | 规划模式与动作树搜索 | 否 | 网页环境，不是结果集遗漏 | “双层 uncertainty web agent”不是新颖点 |
| InfoTree/RIFB (2605.05262) | rollout 集的梯度信息量 | submodular objective、UUCB、预算分配 | 训练时树展开 | 是 | 否 | 熵/子模搜索理论不是新颖点 |
| TASR (2606.13814) | 答案正确概率 | isotonic-calibrated logit margin + answer stability | 训练免检索停止 | 否（需校准） | 否 | 强停止基线；口头 confidence 会塌缩 |
| Know Before You Fetch (2606.29959) | 答案正确概率 | 校准 sequence log-prob/prefix-logit 信号 | k=0/1/5/abstain 预算分配 | 否（需校准） | 否 | 核心贡献是校准概率接口而非 raw entropy；新计划需同样校准 |
| IGRPO (2607.06223) | 中间状态 informativeness | IG 驱动预算感知树 rollout | RL rollout 分配 | 是 | 否 | 最新训练时近邻 |
| Good (1953); Efron–Thisted (1976); Chao–Jost (2012) | 尚未观察到的物种/质量与样本覆盖 | Good–Turing、unseen-species、coverage extrapolation | 估计开放集合遗漏风险 | 否 | 是 | 仅看已知行熵不够；width 必须含 unseen mass/coverage posterior |
| Golovin & Krause (2011) | 部分观测下的随机状态 | adaptive submodularity | 自适应贪心动作选择 | 否 | 取决于先验/观测模型 | 只在假设成立时给近似保证；不得宣称普遍最优 |

## 综述写作分级

- **必须深度讨论**：WebSwarm、SearchOS、Table-as-Search、ECR、Semantic Entropy、Conformal Information Pursuit、TASR、Good–Turing/coverage。
- **方法对照**：A-MapReduce、Web2BigTable、CuriosiTree、InfoReasoner、IG-Search、TEPO、SIGHT、Know Before You Fetch、QuCo-RAG。
- **背景引用**：FLARE、Self-RAG、Dartboard、SePer、InfoTree、IGPO、IGRPO、WebUncertainty。

## 矩阵结论

现有工作已覆盖表格状态、动态 deep/wide 路由、熵下降、EIG-per-cost、校准停止和覆盖图。当前仍可能成立、但需要实验证明的缺口是：在隐藏 anchor 与未知结果集大小并存的 DeepWide 任务中，用一个**校准的分层开放世界信念**同时表示 anchor、未见质量、行资格与单元格值，并以期望任务风险下降/成本路由动作。该判断是检索截止日下的 novelty hypothesis，不是首创证明。
