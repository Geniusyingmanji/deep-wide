# Entropy-DeepWide：信息熵与信息增益驱动 Deep-and-Wide Search 文献综述

> 检索截止：2026-07-19
>
> 结论强度：这是基于公开文献的 novelty audit，不是“没有任何相关工作”的证明。2026 年文献多为尚未同行评审的 arXiv 预印本，文中将预印本结果视为作者报告，而非独立复现事实。

## 摘要

“把信息熵用于搜索代理”不能作为本项目的核心首创主张。Semantic Entropy 已将自由文本答案聚类为语义等价类并用熵预测错误；FLARE、Self-RAG、TASR 和 Know Before You Fetch 已用置信或校准概率控制检索与停止；CuriosiTree、Conformal Information Pursuit 和 ECR 已用期望信息增益或期望熵下降选择下一动作；InfoReasoner、IGPO、IG-Search、SIGHT、TEPO 和 IGRPO 已把信息量用于搜索代理训练或 rollout 分配。DeepWide 侧也已出现 Table-as-Search、A-MapReduce、Web2BigTable、WebSwarm 与 SearchOS，分别覆盖持久表格状态、横向并行、递归 deep/wide 路由和 coverage-aware 调度。

仍有一个可验证、也可被否证的研究缺口：这些线索尚未在 DeepWide 的**分层开放世界信念**中统一。DeepWide 不只有“最终答案是否确定”，还同时包含隐藏核心实体（anchor）是谁、结果集中还有多少未见质量、候选行是否满足约束、每个单元格的语义值是什么。有限候选集上的低 Shannon 熵不代表开放集合完整，甚至可能是在错误 anchor 上过度确信。因此，本综述建议将创新假设收窄为：用校准的 anchor、unseen-mass、row-eligibility、cell-semantic 四层信念估计期望任务风险下降/成本，并验证其是否优于相同动作空间中的启发式控制器。只有通过这一机制验证，才能把“信息熵视角”升级为论文贡献。

## 1. 范围、问题与检索方法

### 1.1 研究问题

本综述回答四个问题：

1. DeepWide 搜索系统已经解决了哪些状态管理、深宽路由和覆盖问题？
2. 熵、信息增益与不确定性已经怎样用于 LLM/RAG/搜索代理？
3. 哪些工作与拟议创新直接重叠，哪些缺口仍可辩护？
4. 信息论视角怎样转化为可校准、可比较、可否证的研究计划？

### 1.2 检索过程

检索在 2026-07-19 进行，采用三层策略：

- 精确追踪用户给出的 WebSwarm（arXiv:2607.08662），并沿其 related work 核对 DeepWideSearch、Table-as-Search、A-MapReduce、Web2BigTable、SearchOS、TreeSeeker 等系统。
- 在 arXiv API 以 `entropy`、`information gain`、`expected entropy reduction`、`retrieval`、`search agent`、`open set`、`unseen mass`、`capture-recapture` 等组合查询，各抓取按提交日期排序的前 100 条，共 300 条记录、去重后 297 条，再按标题与摘要筛选直接相关工作。
- 对经典信息论与覆盖估计文献用 Crossref/OpenAlex/DOI 核验元数据；对关键 2023–2026 论文读取 arXiv 原文而不只依赖摘要。

纳入标准是：方法直接控制检索、证据选择、工具调用、搜索树、停止或开放集合覆盖；或者直接定义 DeepWide/table-search 的系统与评测边界。排除纯推荐、视觉检索、物理导航等仅共享“entropy/search”词面但不能约束本研究设计的工作。检索记录的高密度比较版见 [.research/literature_matrix.md](.research/literature_matrix.md)。

### 1.3 证据限制

arXiv 的未来月份编号与当前时间一致，但不代表论文已经同行评审。公开检索不能证明不存在未公开、未索引或术语不同的工作。文献中的系统分数通常使用不同模型、工具、预算和子集，不能横向当作严格排行榜；本综述只在同一论文、同一骨干的受控比较中解释差值。

## 2. DeepWide 系统演进：新方法必须超过什么

DeepWideSearch 将任务分成 Deep2Wide 与 Wide2Deep：前者先从多跳线索识别隐藏核心实体，再围绕它枚举表格；后者先确定范围，再为每一行做深度属性搜索。评测同时要求 Core Entity Accuracy、Row F1、Item F1、Column F1 和整表 Success Rate，因此一个流畅的最终答案无法掩盖错误 anchor 或漏行。[1]

Table-as-Search 把搜索过程外化为表格：行是候选实体，列是约束或目标属性，已填/空单元格分别记录结果与下一步计划。这已经占据了“以表作为搜索状态”的创新位置。[2] A-MapReduce 用任务自适应 MapReduce 和经验记忆横向执行大规模检索，在其 DeepWideSearch 表中，GPT-5-mini 的 Avg@4 CE Accuracy、Column F1、Item F1、Row F1、SR 分别为 79.09、51.78、42.11、26.44、4.43。[3] Web2BigTable 则采用双层多智能体系统面向 internet-scale 大表构建。[4]

2026 年 7 月的 WebSwarm 进一步削弱了“动态深/宽切换”本身的新颖性。它在推理中渐进构造递归委派树，每个节点选择 atom、deep、wide 或 entity_collect 模式；Web-Probing 先判断相关信息在网页上集中还是分散，同质兄弟节点之间复用轨迹经验。在 DeepWideSearch-EN、同为 GLM-4.5 骨干时，WebSwarm 报告 SR 6.58、Row F1 29.64、Item F1 58.40，相对 ReAct 分别提高 2.63、9.56、11.77 个百分点。[5] 这些数字证明的是该论文设置中的受控差值，不能直接与本项目的 GPT-5.5 全量中英混合单次运行比较。

SearchOS-V1 则把开放域信息搜寻建模为带引用的 relational schema completion，并用 Frontier Task、Evidence Graph、Coverage Map、Failure Memory 和 middleware 管理状态、覆盖与停滞。其案例明确指出“已知行的 cell coverage 达到 100%”仍可能漏掉大量应有行，因此还要独立做 row-scope audit。[6] 这正是本项目需要继承而不是重新宣称的洞见：已知单元格饱和与开放集合完整性是两个问题。

由此，当前系统缺口不是“有没有表格状态、coverage map 或 deep/wide routing”，而是这些控制决策是否由一个经过校准、显式包含开放集遗漏质量的信念模型驱动，并在相同动作空间和预算下带来更低任务风险。

## 3. 信息论基础：熵测量什么，不测量什么

Shannon 熵对离散随机变量 $Z$ 定义为：

\[
H(Z)=-\sum_z p(z)\log p(z).
\]

观察 $O$ 后的信息增益是先验熵与期望后验熵之差：

\[
\operatorname{EIG}(a)=H(B_t)-\mathbb{E}_{o\sim p(o\mid a,B_t)}
\left[H(B_{t+1}\mid a,o)\right],
\]

其中 $B_t$ 是当前信念，$a$ 是信息获取动作。Lindley 将实验提供的信息表述为这种后验不确定性下降，MacKay 将信息型目标用于主动数据选择。[7–9] 若观测模型、先验和损失满足条件，adaptive submodularity 可为贪心自适应选择给出近似保证；这些条件不会因为系统使用 LLM 就自动成立。[10]

三个区分对 DeepWide 至关重要：

- **熵不等于错误率。** 一个错误分布也可以非常尖锐。低熵只表示在当前假设空间内集中，不表示真答案在假设空间内。
- **熵下降不总是好消息。** 偏置或重复证据可能让错误信念更集中；高价值反证也可能先提高熵，因为它揭露了原先被隐藏的冲突。
- **已见类别熵不等于开放集完整性。** 对已发现行的分布很确定，不能推出没有未发现行。宽度停止需要未见质量或覆盖后验，而不能只计算已见实体的 Shannon 熵。

因此，本文用“expected task-risk reduction”作为最终决策量：

\[
\operatorname{score}(a)=
\frac{\mathbb{E}[L(B_t)-L(B_{t+1})\mid a]}{\mathbb{E}[C(a)]},
\]

其中 $L$ 是与 anchor 错误、漏行、错格和无证据格对应的任务损失，$C(a)$ 是工具、token、延迟或货币成本。EIG 恰好是对数评分下的期望 Bayes risk 下降；对 0–1 或表格指标损失，它至多是需要验证的 surrogate，而不是等价的万能分数。

## 4. 熵与信息增益在 LLM 搜索中的六条路线

### 4.1 被动预测与语义熵

Kuhn、Gal 与 Farquhar 指出，token 序列的多样性会把同义表达误当作不同答案，因此把多次生成按双向语义蕴含聚类，再对语义类概率计算 entropy。ICLR 2023 的 Semantic Uncertainty 和 Nature 2024 的后续工作报告该信号比 token-level entropy 与若干 self-evaluation 基线更能预测问答错误或幻觉。[11,12] 这为 anchor 和 cell 的语义分布提供了自然估计器，但它本身是被动检测器：没有定义搜索动作、开放集覆盖或停止。

### 4.2 何时检索与何时停止

FLARE 用即将生成句子中的低置信 token 触发检索；Self-RAG 学习 reflection tokens 来决定检索、生成与批判。[13,14] TASR 要求规范化答案连续两轮稳定且 isotonic-calibrated logit margin 超阈值才停止，并报告口头 1–5 confidence 在 RLHF 模型上严重塌缩。[15] Know Before You Fetch 把 raw sequence/prefix uncertainty 校准为正确概率，再在 closed-book、$k=1$、$k=5$ 与 abstain 之间分配预算；它强调“概率接口”而不是发明新的 raw uncertainty signal，并显示 gating 不一定降低真实延迟。[16]

QuCo-RAG 从另一个方向提出警告：模型内部 logits/entropy 会因失校准而对错误答案高置信，因此用预训练语料中的实体频率与共现统计触发检索。[17] 这些工作共同要求本项目比较 raw entropy、校准 entropy、verbalized confidence、logit margin、support count 和外部语料/检索统计，而不能默认“熵更数学”就更可靠。

更广的 agent-control 文献也已经占据相邻主张。Agentic Uncertainty Quantification 把口头不确定性与解释变成记忆和反思触发信号；WebUncertainty 分别建模任务规划与网页动作不确定性并结合 MCTS；TreeSeeker 用 value、uncertainty、risk 的 textual UCB 在深搜树上探索、利用或回退。[37–39] 它们没有估计 DeepWide 结果集的未见质量，但意味着“主动 uncertainty controller”“双层 web uncertainty”或“uncertainty/risk tree search”都不能作为本项目的独立首创表述。现代神经网络校准研究也早已表明 raw confidence 与真实正确率可能不一致，并系统化了 temperature scaling 等后处理基线。[40]

### 4.3 检索效用与证据选择

Dartboard 的 Relevant Information Gain 在 passage set 中联合鼓励相关性与非冗余；SePer 用检索前后 semantic perplexity reduction 衡量检索对生成器的效用；Information Gain Pruning 用 generator-aligned utility 删除弱或有害 passage。[18–20] 它们主要回答“哪些已检索文档应该进入上下文”，不建模 DeepWide 的隐藏 anchor 和未见实体质量，但构成 passage selection 强基线。

### 4.4 下一问题或动作的期望信息增益

CuriosiTree 在临床诊断模拟中以树搜索估计每个信息获取动作的 EIG 与成本，证明“EIG per cost 的测试时动作选择”并非空白。[21] Conformal Information Pursuit 每轮选择预期使 conformal prediction set 最小的问题，以 prediction-set size 近似条件熵上界，并在边际覆盖假设下缓解 LLM 概率失校准。[22] 它也揭示了直接迁移的困难：DeepWide 的标签空间和潜在实体集合会随搜索扩展，并不天然满足固定候选集与 exchangeable calibration data 的假设。

### 4.5 训练奖励与 rollout 分配

InfoReasoner 用语义聚类后的 entropy reduction 构造 dense semantic information-gain reward；TEPO 奖励工具调用前后的 token-segment entropy 下降；SIGHT 用信息增益定位分支、去重或反思时机；IGPO 用 gold-answer probability 的逐轮增量训练多轮搜索代理；IGRPO 用中间状态 informativeness 分配树状 rollout 预算。[23–27] InfoTree/RIFB 还从固定训练预算下的 submodular rollout informativeness 推导 UUCB。[28]

IG-Search 的术语尤其值得谨慎。其公式是“真实检索上下文相对随机文档上下文的 gold-answer log-likelihood ratio”；作者脚注明确说明这不是 Shannon information gain，只共享“正值提高 gold-answer confidence”的直觉。[29] 因此，本项目必须把 Shannon entropy、mutual information、pointwise log-likelihood ratio、semantic perplexity reduction 和启发式 utility 分开命名。

### 4.6 推理时 EER：最直接的撞车工作

Entropic Claim Resolution（ECR）在有限竞争答案假设上维护概率分布，按 Expected Entropy Reduction 选择原子证据，并在熵低于阈值且 coherence 条件满足时停止。[30] 这是与本方案最直接的工作，排除了“首次在推理时用熵选择搜索证据/停止”的说法。

ECR 同时暴露了可延伸的边界：

1. 它依赖初始有限假设集；原文明确承认真答案不在集合中时可能低熵收敛到错误解释。
2. 实现级 EER proxy 按支持/不支持假设的质量不平衡程度打分，作者明确说明它有意偏离经典偏好平衡切分的 EIG，是低延迟下的 exploitative heuristic。
3. 在 300 题 HotpotQA-style 端到端实验中，ECR 的 EM 为 0.297，relevance baseline 为 0.313，random control 为 0.207；它高于随机选择，但没有在普通相关性问答上证明相对 relevance baseline 的准确率优势。
4. 它选择候选池内的 claim，不估计 DeepWide 结果集之外尚未观察到的实体质量，也没有行/格层级的结构化损失。

这意味着合理路线不是回避 ECR，而是把 ECR 作为必须复现的有限假设基线，并通过开放集 OTHER 状态、unseen-mass posterior 与表级分层损失验证新增机制。

## 5. 开放集合覆盖：为什么 width 不能只是 entropy

Good–Turing 估计用低频事件，尤其 singleton 的比例，推断尚未观察事件的总概率质量。Efron–Thisted 将 unseen-species 思想用于估计 Shakespeare 未见词汇；Chao–Jost 以 sample completeness 而不是 sample size 组织 rarefaction/extrapolation。[31–33] 数据库研究也曾用样本发现频率估计 aggregate query 中 unknown unknowns 的影响。[34]

这些方法不能原样套到网页搜索。经典估计通常假设样本来自稳定分布或可解释的重复捕获过程，而搜索引擎排序、查询改写、站点重复、SEO 与语言过滤都会造成强烈且依赖动作的选择偏差。可行做法是：

- 把不同 query family/source family 当成有记录的采样机制，不把同源镜像当成独立捕获；
- 跟踪实体在查询、来源、语言和时间切片中的 incidence/frequency；
- 用 Good–Turing/coverage 与 capture–recapture 型特征产生**遗漏风险估计**，再在 held-out task 上校准，而不是宣称得到无偏人口规模；
- 对已知有限名录、未知开放集合、网页不稳定三种任务分别报告；
- 用 synthetic hide-and-seek 和已知全集任务检查“预测剩余行数/质量”是否与真实遗漏相关。

最小开放世界信念应为 $M$，表示“下一轮仍能发现的有效实体质量/剩余集合规模”，而不是把 OTHER 粗暴设成一个固定类别。若观测到的新实体都是 singleton，低 anchor/cell entropy 也不能触发停止。

## 6. 跨论文比较与 novelty verdict

| 文献族 | 信念对象 | 作用阶段 | 能否动态选动作 | 是否处理开放集遗漏 | 对本项目的结论 |
|---|---|---|---|---|---|
| Semantic Entropy、SePer | 答案语义类/生成器信念 | 推理评估 | 通常否 | 否 | 语义熵估计器已有 |
| FLARE、Self-RAG、TASR、Know Before You Fetch | 下一 token 或答案正确性 | 推理控制 | 触发/停止/预算档位 | 否 | adaptive retrieval 与校准停止已有 |
| CuriosiTree、C-IP、ECR | 决策/标签/答案假设 | 推理控制 | 是，按 EIG/EER | 通常固定有限集 | EIG 动作选择与熵停止已有 |
| InfoReasoner、IGPO、IG-Search、SIGHT、TEPO、IGRPO | gold-answer、语义答案或 rollout | 训练 | 学习后间接控制 | 否 | IG/entropy 训练奖励已有 |
| TaS、A-MapReduce、Web2BigTable | 行、格、横向子任务 | 推理系统 | 是 | 启发式覆盖 | 表格状态与大规模宽搜已有 |
| WebSwarm、SearchOS | 搜索节点、网页结构、coverage/gaps | 推理系统 | 是 | 定性 open-set / scope audit | 动态 deep/wide 与覆盖驱动调度已有 |
| Good–Turing、coverage、capture–recapture | 未见事件质量/种类数 | 统计估计 | 不直接 | 是 | 提供 width posterior，但需处理搜索偏差 |

### 6.1 不能声称

- 首次把熵或信息增益用于搜索代理、RAG、工具调用、证据选择或停止。
- 首次做 uncertainty-aware web agent、双层不确定性或动态 deep/wide routing。
- 首次把表格、coverage map 或 evidence graph 作为搜索状态。
- 低熵等于正确、完整或有充分证据。
- Good–Turing/capture–recapture 在搜索引擎偏置下自动给出无偏全集估计。
- 控制器“理论最优”，除非明确证明观测模型、校准、损失和 adaptive-submodularity 条件。

### 6.2 可辩护的候选创新

建议将方法暂命名为：

> **Entropy-DeepWide: Calibrated Hierarchical Belief Reduction for Open-World Deep-and-Wide Search**

候选贡献不是使用熵，而是四个必须同时成立的设计：

1. **DeepWide 特有的分层随机变量。** $A$：隐藏 anchor；$M$：未见质量/剩余集合；$R_e$：候选行资格；$Y_{e,c}$：单元格语义值。
2. **开放世界 width。** 将有限候选 anchor/row 分布与 OTHER/unseen-mass posterior 联合，避免低已知行熵造成假完整。
3. **风险与成本耦合。** 动作按期望任务损失下降/成本路由，而不是把所有 entropy bit 等价相加。
4. **校准与可否证验证。** 分别证明各信号能预测 anchor、遗漏、行和格错误，并在同动作空间、同预算下优于 heuristic uncertainty；否则放弃 entropy-controller 的主张。

检索到的文献中，没有一篇同时满足以上四点。但这只是截至检索日的**候选空白**；SearchOS 的 scope audit、ECR 的有限假设 EER、C-IP 的校准与 CuriosiTree 的 EIG/cost 已覆盖其相邻部分。论文必须正面比较这些近邻，不能靠改名构造差异。

## 7. 建议的分层开放世界熵框架

### 7.1 信念状态

在时刻 $t$，维护：

\[
B_t=\{p(A),\ p(M\mid \mathcal D_t),\ p(R_e),\ p(Y_{e,c})\}_{e,c}.
\]

- $p(A)$：多次独立线索解析形成的 anchor 语义假设分布，含 `OTHER/unknown`。
- $p(M\mid \mathcal D_t)$：基于 discovery history 的未见质量或剩余行数后验，输入包括 singleton/doubleton、跨 query/source 重捕获、近期 yield、来源覆盖与查询新颖性。
- $p(R_e)$：候选实体满足所有范围/资格约束的概率，需保留 reject/unknown，而非直接二值化。
- $p(Y_{e,c})$：对 cell 候选值按语义等价聚类后的分布，另含 unknown/contradicted。

不要把四类 entropy 直接相加。一个 anchor 错误会使下游整表失效，一个漏行影响 Row Recall，一个错格影响 Item F1，损失尺度不同。建议通过开发集估计 task-loss surrogate：

\[
L(B_t)=w_A\Pr(A\neq A^*)+w_M\mathbb E[\text{missed mass}]
+\sum_e w_R\Pr(R_e\text{ wrong})
+\sum_{e,c}w_c\Pr(Y_{e,c}\text{ wrong/unsupported}).
\]

权重只能在开发集固定，测试集不得调参。

### 7.2 动作与观测

动作集合至少包含：

- `resolve_anchor`：寻找可区分竞争 anchor 的线索或反证；
- `discover_entities`：扩展新行，改变 $M$ 与候选集合；
- `test_row_constraint(e)`：验证某行是否满足入表约束；
- `fill_cell(e,c)`：获取缺失属性；
- `falsify_cell(e,c)`：寻找否定或冲突来源；
- `audit_scope`：针对潜在名单边界或全集来源做覆盖检查；
- `stop_or_abstain`：生成表格并保留不确定/未证实格。

动作观测不是 Tavily answer/snippet 的文本本身，而是带 URL、页面正文跨度、发布时间、来源类型、抽取命题和 provenance 的 evidence event。重复站点与镜像必须去相关，否则多份复制内容会伪造熵下降。

### 7.3 路由与停止

对候选动作 $a$，通过 posterior sampling 或受控 rollout 近似：

\[
\widehat{a^*}=\arg\max_a
\frac{\widehat{\mathbb E}[L(B_t)-L(B_{t+1})\mid a]}
{\widehat{C}(a)+\epsilon}.
\]

若 EIG 预测代价过高，可以先做可解释的分层近似，但必须记录预测 gain、实际 posterior change、任务损失变化与成本，允许事后检查 proxy 是否有效。

停止至少需要四道门：

1. anchor 风险低且 `OTHER` 质量低；
2. 预测 unseen mass/遗漏风险低，且 scope audit 没发现新范围；
3. 有效行与关键 cell 的错误/无支持风险低，或已显式 abstain；
4. 所有可执行动作的预期任务风险下降/成本低于开发集固定阈值，或预算耗尽。

熵上升不能自动判为坏动作：若新来源揭露矛盾，短期 entropy 上升但 calibration 与最终错误风险可能改善。日志应同时报告 entropy change、Brier/NLL change 和 contradiction discovery。

## 8. 实验必须回答的失败模式

### 8.1 估计器是否可靠

对 anchor、row、cell 分别报告 AUROC/AUPRC、Brier、NLL、ECE 与 risk–coverage；对 $M$ 报告剩余行数/质量误差、row recall calibration、premature-stop rate。比较 semantic entropy、token entropy、margin、verbalized confidence、support count、recent yield、source diversity 与 calibrated ensemble。若 entropy 在相同成本下不能稳定优于简单信号，核心假设应判失败。

### 8.2 controller 是否真的由信号获益

所有 controller 比较必须共享模型、搜索/浏览工具、动作集合、最大 token、tool call、wall-clock 和重试次数。必须包含：当前 retrieve-then-generate、fixed wide→deep、fixed deep→wide、TaS/no-entropy planner、相同 controller 加 heuristic uncertainty、oracle one-step value（仅分析）、WebSwarm/SearchOS/A-MapReduce 系统级比较。只和 ReAct 比不够。

### 8.3 低熵错收敛

构造或标注三类诊断集：真 anchor 不在初始 top-k、重复错误网页占多数、权威反证后到。检查 `OTHER`、hypothesis regeneration 与 falsification 是否能避免低熵错误停止。ECR 是有限假设对照。

### 8.4 开放集遗漏

在已知完整列表、synthetic hide-and-seek 与真实开放列表上分别测试。搜索接口强偏置会破坏经典 unseen-species 假设，因此需要按 query/source family block bootstrap，并报告估计在语言、领域、时间敏感任务上的偏差。

### 8.5 评测污染与 judge 可靠性

Search-Time Contamination 研究指出，联网 agent 可能检索到公开 benchmark 问题或答案，造成分数膨胀。[35] 运行时必须屏蔽 benchmark 名、instance id、gold/evaluation 路径，记录并扫描 URL/页面中的 benchmark 字符串。REFLECT 还报告深度研究 LLM judges 对细粒度失败的准确率不足 55%，尤其不擅长证据验证；因此官方 LLM judge 指标需配合分层人工抽检、双人复核和 judge disagreement 报告。[36]

## 9. 对当前项目的直接诊断

当前仓库已完成的是基线，不是 Entropy-DeepWide：`run_deepwide_smoke.py` 由模型一次生成 6 个搜索 query，每个 query 调 Tavily，`include_raw_content=False`，只保留 Tavily answer/snippet；默认不启用 follow-up；最后把截断 evidence 一次性输入 GPT-5.5 生成表格。系统没有页面正文 reader、持久 table state、anchor hypothesis set、unseen-mass estimator、row/cell belief、反证循环或动态 controller。

官方 evaluator 对现有 220 题单次预测的结果为：SR 2.27%（5/220）、Core Entity Accuracy 67.73%、Row F1 19.48%、Item F1 34.14%、Column F1 41.03%。按 instance-id 前缀做预测后离线分组，Deep2Wide 85 题为 0/85 成功、Entity Accuracy 44.71%、Row F1 4.89%；Wide2Deep 135 题为 5/135 成功、Entity Accuracy 82.22%、Row F1 28.67%。这些值可追溯到 [`results/baseline_gpt55_20260623.json`](results/baseline_gpt55_20260623.json) 及其所列原始输出。该历史 run 未做 search-time contamination 扫描，因此是工程诊断而非投稿级结果。

这个差异支持“anchor 是当前首要瓶颈”的工程优先级，但还不能证明 entropy 能解决它。先做信号验证比直接搭完整 controller 更重要。

泄漏审计还发现，现有 smoke 脚本把生成与本地近似 gold evaluation 放在同一进程，task object 同时携带 `evaluation` 元数据；虽然生成 prompt 实际只使用 `question`，该边界仍不够硬。正式实验必须把 runtime manifest 限制为 `{opaque_id, question}`，预测完成后再由独立 evaluator 读取 evaluation、subset label 和 gold table。

## 10. 结论

信息熵适合作为这项工作的理论主线，但不能作为孤立 novelty。已有文献已经覆盖语义熵、信息增益奖励、EIG 动作选择、熵驱动证据选择、校准停止、表格状态和动态深宽搜索。可辩护的新问题是：DeepWide 的隐藏 anchor 与开放集合遗漏是否需要一个不同于有限答案 QA 的分层信念模型，以及这个模型能否在同预算下比简单 heuristic 更准确地分配搜索。

新的 `plan.md` 因此采用证据门控顺序：先隔离评测与复现基线，再验证四类信号，再验证动作价值预测，最后才实现完整 controller。若 anchor/coverage/cell entropy 不能校准，或同动作空间下不改善任务风险–成本 Pareto，则“熵作为核心创新”应降级为诊断工具，而不是继续包装成主方法。

## 参考文献

1. Lan, T. et al. **DeepWideSearch: Benchmarking Depth and Width in Agentic Information Seeking.** arXiv:2510.20168 (2025). https://arxiv.org/abs/2510.20168
2. Lan, T. et al. **Table-as-Search: Formulate Long-Horizon Agentic Information Seeking as Table Completion.** arXiv:2602.06724 (2026). https://arxiv.org/abs/2602.06724
3. Chen, M. et al. **A-MapReduce: Executing Wide Search via Agentic MapReduce.** arXiv:2602.01331 (2026). https://arxiv.org/abs/2602.01331
4. Huang, Y. et al. **Web2BigTable: A Bi-Level Multi-Agent LLM System for Internet-Scale Information Search and Extraction.** arXiv:2604.27221 (2026). https://arxiv.org/abs/2604.27221
5. Song, X. et al. **WebSwarm: Recursive Multi-Agent Orchestration for Deep-and-Wide Web Search.** arXiv:2607.08662 (2026). https://arxiv.org/abs/2607.08662
6. Zhang, Y. et al. **SearchOS-V1: Towards Robust Open-Domain Information-Seeking Agent Collaboration.** arXiv:2607.15257 (2026). https://arxiv.org/abs/2607.15257
7. Shannon, C. E. **A Mathematical Theory of Communication.** *Bell System Technical Journal* 27, 379–423 (1948). https://doi.org/10.1002/j.1538-7305.1948.tb01338.x
8. Lindley, D. V. **On a Measure of the Information Provided by an Experiment.** *Annals of Mathematical Statistics* 27, 986–1005 (1956). https://doi.org/10.1214/aoms/1177728069
9. MacKay, D. J. C. **Information-Based Objective Functions for Active Data Selection.** *Neural Computation* 4, 590–604 (1992). https://doi.org/10.1162/neco.1992.4.4.590
10. Golovin, D. & Krause, A. **Adaptive Submodularity: Theory and Applications in Active Learning and Stochastic Optimization.** *Journal of Artificial Intelligence Research* 42, 427–486 (2011). https://jair.org/index.php/jair/article/view/10731 (DOI metadata: 10.1613/jair.3278)
11. Kuhn, L., Gal, Y. & Farquhar, S. **Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation.** ICLR (2023); arXiv:2302.09664. https://arxiv.org/abs/2302.09664
12. Farquhar, S., Kossen, J., Kuhn, L. & Gal, Y. **Detecting Hallucinations in Large Language Models Using Semantic Entropy.** *Nature* 630, 625–630 (2024). https://doi.org/10.1038/s41586-024-07421-0
13. Jiang, Z. et al. **Active Retrieval Augmented Generation.** EMNLP (2023); arXiv:2305.06983. https://arxiv.org/abs/2305.06983
14. Asai, A. et al. **Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.** arXiv:2310.11511 (2023). https://arxiv.org/abs/2310.11511
15. Kieback, A. et al. **TASR: Training-Free Adaptive Stopping for Iterative Retrieval.** arXiv:2606.13814 (2026). https://arxiv.org/abs/2606.13814
16. Dong, Z. et al. **Know Before You Fetch: Calibrated Retrieval-Budget Allocation for Retrieval-Augmented Generation.** arXiv:2606.29959 (2026). https://arxiv.org/abs/2606.29959
17. Min, D. et al. **QuCo-RAG: Quantifying Uncertainty from the Pre-training Corpus for Dynamic Retrieval-Augmented Generation.** Findings of ACL (2026); arXiv:2512.19134. https://arxiv.org/abs/2512.19134
18. Pickett, M. et al. **Better RAG using Relevant Information Gain.** arXiv:2407.12101 (2024). https://arxiv.org/abs/2407.12101
19. Dai, L. et al. **SePer: Measure Retrieval Utility Through the Lens of Semantic Perplexity Reduction.** ICLR (2025); arXiv:2503.01478. https://arxiv.org/abs/2503.01478
20. Song, Z. et al. **Less is More for RAG: Information Gain Pruning for Generator-Aligned Reranking and Evidence Selection.** arXiv:2601.17532 (2026). https://arxiv.org/abs/2601.17532
21. Cooper, M. et al. **The Curious Language Model: Strategic Test-Time Information Acquisition.** arXiv:2506.09173 (2025). https://arxiv.org/abs/2506.09173
22. Chan, K. H. R. et al. **Conformal Information Pursuit for Interactively Guiding Large Language Models.** arXiv:2507.03279 (2025). https://arxiv.org/abs/2507.03279
23. Hu, S. et al. **Optimizing Agentic Reasoning with Retrieval via Synthetic Semantic Information Gain Reward.** arXiv:2602.00845 (2026). https://arxiv.org/abs/2602.00845
24. Li, Z. et al. **Rethinking the Role of Entropy in Optimizing Tool-Use Behaviors for Large Language Model Agents.** arXiv:2602.02050 (2026). https://arxiv.org/abs/2602.02050
25. Zhong, W. et al. **SIGHT: Reinforcement Learning with Self-Evidence and Information-Gain Diverse Branching for Search Agent.** arXiv:2602.11551 (2026). https://arxiv.org/abs/2602.11551
26. Wang, G. et al. **Information Gain-based Policy Optimization: A Simple and Effective Approach for Multi-Turn Search Agents.** ICLR (2026); arXiv:2510.14967. https://arxiv.org/abs/2510.14967
27. Zhang, Y. et al. **Information Gain-based Rollout Policy Optimization: An Adaptive Tree-Structured Rollout Approach for Multi-Turn LLM Agents.** arXiv:2607.06223 (2026). https://arxiv.org/abs/2607.06223
28. Hu, Y. et al. **Maximizing Rollout Informativeness under a Fixed Budget: A Submodular View of Tree Search for Tool-Use Agentic Reinforcement Learning.** arXiv:2605.05262 (2026). https://arxiv.org/abs/2605.05262
29. Liang, Z. et al. **IG-Search: Step-Level Information Gain Rewards for Search-Augmented Reasoning.** arXiv:2604.15148 (2026). https://arxiv.org/abs/2604.15148
30. Di Gioia, D. **Entropic Claim Resolution: Uncertainty-Driven Evidence Selection for RAG.** arXiv:2603.28444 (2026). https://arxiv.org/abs/2603.28444
31. Good, I. J. **The Population Frequencies of Species and the Estimation of Population Parameters.** *Biometrika* 40, 237–264 (1953). https://doi.org/10.1093/biomet/40.3-4.237
32. Efron, B. & Thisted, R. **Estimating the Number of Unseen Species: How Many Words Did Shakespeare Know?** *Biometrika* 63, 435–447 (1976). https://doi.org/10.1093/biomet/63.3.435
33. Chao, A. & Jost, L. **Coverage-Based Rarefaction and Extrapolation: Standardizing Samples by Completeness Rather than Size.** *Ecology* 93, 2533–2547 (2012). https://doi.org/10.1890/11-1952.1
34. Chung, Y. et al. **Estimating the Impact of Unknown Unknowns on Aggregate Query Results.** SIGMOD (2016). https://doi.org/10.1145/2882903.2882909
35. Wang, Y. et al. **Search-Time Contamination in Deep Research Agents: Measuring Performance Inflation in Public Benchmark Evaluation.** arXiv:2606.05241 (2026). https://arxiv.org/abs/2606.05241
36. Wang, L. et al. **Time to REFLECT: Can We Trust LLM Judges for Evidence-based Research Agents?** arXiv:2605.19196 (2026). https://arxiv.org/abs/2605.19196
37. Zhang, J. et al. **Agentic Uncertainty Quantification.** arXiv:2601.15703 (2026). https://arxiv.org/abs/2601.15703
38. Zhang, L. et al. **WebUncertainty: Dual-Level Uncertainty Driven Planning and Reasoning for Autonomous Web Agent.** arXiv:2604.17821 (2026). https://arxiv.org/abs/2604.17821
39. Shi, Z. et al. **TreeSeeker: Tree-Structured Trial, Error, and Return in Deep Search.** arXiv:2606.11662 (2026). https://arxiv.org/abs/2606.11662
40. Guo, C., Pleiss, G., Sun, Y. & Weinberger, K. Q. **On Calibration of Modern Neural Networks.** *Proceedings of the 34th International Conference on Machine Learning*, PMLR 70, 1321–1330 (2017). https://proceedings.mlr.press/v70/guo17a.html
