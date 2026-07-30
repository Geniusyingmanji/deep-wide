# Entropy-DeepWide：信息熵、信息增益与 Credit Assignment 驱动 Deep-and-Wide Search 文献综述

> 检索截止：2026-07-21；项目证据更新：2026-07-25
>
> 结论强度：这是基于公开文献的 novelty audit，不是“没有任何相关工作”的证明。2026 年文献多为尚未同行评审的 arXiv 预印本，文中将预印本结果视为作者报告，而非独立复现事实。

## 摘要

“把信息熵用于搜索代理”或“给熵降大的步骤更多 credit”都不能作为本项目的核心首创主张。Semantic Entropy 已将自由文本答案聚类为语义等价类并用熵预测错误；FLARE、Self-RAG、TASR 和 Know Before You Fetch 已用置信或校准概率控制检索与停止；CuriosiTree、Conformal Information Pursuit 和 ECR 已用期望信息增益或期望熵下降选择下一动作；InfoReasoner、IGPO、IG-Search、SIGHT、TEPO 和 IGRPO 已把信息量用于搜索代理训练或 rollout 分配。更直接地，ECHO 已把后验收缩称为 epistemic credit，TRACE、LOTAPO、STAMP、RICE-PO 等分别用真值答案似然、删除干预、证据 provenance 和同状态局部分支定位 turn credit。DeepWide 侧也已出现 Table-as-Search、A-MapReduce、Web2BigTable、WebSwarm 与 SearchOS，分别覆盖持久表格状态、横向并行、递归 deep/wide 路由和 coverage-aware 调度。Forage V2 又直接研究完成边界未知时的 denominator blindness，Shared Discovery Paradox 则证明更准确的共享 posterior 若被压成重复的单一动作，可能降低群体发现覆盖。[72,73]

在本次检索范围内，仍有一个可验证、也可被否证的候选缺口：这些线索尚未在 DeepWide 的**分层开放世界信念**与**结果对齐的反事实 credit**中统一。DeepWide 不只有“最终答案是否确定”，还同时包含隐藏核心实体（anchor）是谁、结果集中还有多少未见质量、候选行是否满足约束、每个单元格的语义值是什么。有限候选集上的低 Shannon 熵不代表开放集合完整，甚至可能是在错误 anchor 上过度确信。因此，本综述建议将创新假设收窄为：用校准的 anchor、unseen-mass、row-eligibility、cell-semantic 四层信念估计任务风险变化，再通过同状态干预和 evidence provenance 判断这次变化是否由该步骤造成、是否支持最终任务。信息量在这里是 epistemic signal，而不是自动成立的 causal credit。当前代码与实验尚未实现或验证这一方法；截至 V2.40.3 的改动仍是 evidence continuity、证据边界、开放集合覆盖、输出契约、列公平查询、alias 呈现、attribute/membership 隔离和失败观测工程，不能归因于 entropy。

## 1. 范围、问题与检索方法

### 1.1 研究问题

本综述回答四个问题：

1. DeepWide 搜索系统已经解决了哪些状态管理、深宽路由和覆盖问题？
2. 熵、信息增益与不确定性已经怎样用于 LLM/RAG/搜索代理？
3. 哪些工作与拟议创新直接重叠，哪些缺口仍可辩护？
4. 信息论视角怎样转化为可校准、可比较、可否证的研究计划？
5. 信息增益何时可以作为 credit，何时只是在奖励新奇、噪声或错误自信？

### 1.2 检索过程

检索在 2026-07-19 至 2026-07-21 进行，采用三层策略：

- 精确追踪用户给出的 WebSwarm（arXiv:2607.08662），并沿其 related work 核对 DeepWideSearch、Table-as-Search、A-MapReduce、Web2BigTable、SearchOS、TreeSeeker 等系统。
- 在 arXiv API 以 `entropy`、`information gain`、`expected entropy reduction`、`retrieval`、`search agent`、`open set`、`unseen mass`、`capture-recapture` 等组合查询，各抓取按提交日期排序的前 100 条，共 300 条记录、去重后 297 条，再按标题与摘要筛选直接相关工作。
- 针对 credit assignment 追加检索 `epistemic credit`、`entropy reduction + credit assignment`、`information gain + process/turn/step reward`、`causal/counterfactual credit + language agent`，并反向核对 ECHO、TRACE、LOTAPO、STAMP、RICE-PO、CVT-RL、SIOP 等论文的 related work；关键结论以 PDF 公式与 limitation 原文为准。
- 2026-07-20 再检索 `credit assignment AND (information gain OR entropy) AND agent/search` 与 `open world AND uncertainty AND agent/search`，核对新增近邻 PivoARL、InfoPO、AEM、SELAUR、STRIDE 与 APPO；使用 arXiv API 逐条验证标题、作者、版本和摘要。
- 2026-07-21 补充检索 denominator blindness、shared discovery、turn-group information gain 和 uncertainty-guided exploration，核对 Forage V2、Shared Discovery Paradox、A²TGPO 与 T²PO 的 arXiv 元数据与原文。
- 2026-07-21 做提交日期增量检索，并读取 Forage V2、Shared Discovery Paradox 与 A²TGPO 的 PDF。该轮新增了未知 denominator、belief–coverage 分离、gold-conditioned turn IG 和 uncertainty-guided resampling 的直接近邻。[72–75] 截至该范围仍未找到把 DeepWide 的 anchor、未见质量、行资格、单元格值四层同时概率化并用于 task-risk control/credit 的工作，但这只是限定语料与日期下的缺口判断。
- 对经典信息论与覆盖估计文献用 Crossref/OpenAlex/DOI 核验元数据；对关键 2023–2026 论文读取 arXiv 原文而不只依赖摘要。

纳入标准是：方法直接控制检索、证据选择、工具调用、搜索树、停止或开放集合覆盖；或者直接定义 DeepWide/table-search 的系统与评测边界。排除纯推荐、视觉检索、物理导航等仅共享“entropy/search”词面但不能约束本研究设计的工作。检索记录的高密度比较版见 [.research/literature_matrix.md](.research/literature_matrix.md)。

### 1.3 证据限制

arXiv 的未来月份编号与当前时间一致，但不代表论文已经同行评审。公开检索不能证明不存在未公开、未索引或术语不同的工作。文献中的系统分数通常使用不同模型、工具、预算和子集，不能横向当作严格排行榜；本综述只在同一论文、同一骨干的受控比较中解释差值。

## 2. DeepWide 系统演进：新方法必须超过什么

DeepWideSearch 将任务分成 Deep2Wide 与 Wide2Deep：前者先从多跳线索识别隐藏核心实体，再围绕它枚举表格；后者先确定范围，再为每一行做深度属性搜索。评测同时要求 Core Entity Accuracy、Row F1、Item F1、Column F1 和整表 Success Rate，因此一个流畅的最终答案无法掩盖错误 anchor 或漏行。[1]

Table-as-Search 把搜索过程外化为表格：行是候选实体，列是约束或目标属性，已填/空单元格分别记录结果与下一步计划。这已经占据了“以表作为搜索状态”的创新位置。[2] A-MapReduce 用任务自适应 MapReduce 和经验记忆横向执行大规模检索，在其 DeepWideSearch 表中，GPT-5-mini 的 Avg@4 CE Accuracy、Column F1、Item F1、Row F1、SR 分别为 79.09、51.78、42.11、26.44、4.43。[3] Web2BigTable 则采用双层多智能体系统面向 internet-scale 大表构建。[4]

2026 年 7 月的 WebSwarm 进一步削弱了“动态深/宽切换”本身的新颖性。它在推理中渐进构造递归委派树，每个节点选择 atom、deep、wide 或 entity_collect 模式；Web-Probing 先判断相关信息在网页上集中还是分散，同质兄弟节点之间复用轨迹经验。在 DeepWideSearch-EN、同为 GLM-4.5 骨干时，WebSwarm 报告 SR 6.58、Row F1 29.64、Item F1 58.40，相对 ReAct 分别提高 2.63、9.56、11.77 个百分点。[5] 这些数字证明的是该论文设置中的受控差值，不能直接与本项目的 GPT-5.5 全量中英混合单次运行比较。

SearchOS-V1 则把开放域信息搜寻建模为带引用的 relational schema completion，并用 Frontier Task、Evidence Graph、Coverage Map、Failure Memory 和 middleware 管理状态、覆盖与停滞。其案例明确指出“已知行的 cell coverage 达到 100%”仍可能漏掉大量应有行，因此还要独立做 row-scope audit。[6] 这正是本项目需要继承而不是重新宣称的洞见：已知单元格饱和与开放集合完整性是两个问题。

Forage V2 对开放集合给出更直接的命名：当完成边界没有预先给出时，代理会系统性低估 denominator，并可能对自己发现的小集合报告 100% coverage。它把 Planner 与独立 Evaluator 隔离，让两者分别收集对象和发现“完整意味着什么”，再把 denominator 修订经验跨 run 迁移。[72] 这占据了“首次发现分母盲区”或“首次让代理同时搜索答案和完成边界”的主张。它仍不是本项目拟议的概率层：每个 run 使用自己发现的 denominator，论文明确指出这些 coverage 百分比不能跨 run 直接比较，也没有给出未见质量的校准 posterior。

Shared Discovery Paradox 提供了另一个必要反例。在其有限 Bayesian 搜索模型中，汇总线索提高了最佳单一推荐的准确率，但若八个搜索者都执行该推荐，发现率从去中心化搜索的 0.8322 降到 0.3835；对同一 pooled reports 分配 top-eight posterior portfolio 则达到 0.8594。[73] 这不是 DeepWide 实证结果，却解析性地说明 belief quality 与 coverage policy 是两个变量。即使四层 posterior 完全正确，若 controller 没有对重复动作、来源相关性和边际覆盖去重，信息集中仍可能伤害 width。

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

A²TGPO 继续使用每 turn 后 ground-truth answer probability 的变化，并把同一 prompt、同一 turn index 的 IG 放在一起归一，再用 IG 调节累计 advantage 与 clipping 范围；论文明确把依赖 ground-truth answer 列为限制。[74] T²PO 则以 token/turn uncertainty dynamics 触发 thinking intervention 和 turn resampling。[75] 因此，“IG 大的 turn 获得更多更新空间”与“低信息 turn 重新采样”也已有方法；本项目只有在 label-blind 的四层 task-risk 信号上优于这些一般 uncertainty/IG baseline，才有新增价值。

IG-Search 的术语尤其值得谨慎。其公式是“真实检索上下文相对随机文档上下文的 gold-answer log-likelihood ratio”；作者脚注明确说明这不是 Shannon information gain，只共享“正值提高 gold-answer confidence”的直觉。[29] 因此，本项目必须把 Shannon entropy、mutual information、pointwise log-likelihood ratio、semantic perplexity reduction 和启发式 utility 分开命名。

### 4.6 推理时 EER：最直接的撞车工作

Entropic Claim Resolution（ECR）在有限竞争答案假设上维护概率分布，按 Expected Entropy Reduction 选择原子证据，并在熵低于阈值且 coherence 条件满足时停止。[30] 这是与本方案最直接的工作，排除了“首次在推理时用熵选择搜索证据/停止”的说法。

ECR 同时暴露了可延伸的边界：

1. 它依赖初始有限假设集；原文明确承认真答案不在集合中时可能低熵收敛到错误解释。
2. 实现级 EER proxy 按支持/不支持假设的质量不平衡程度打分，作者明确说明它有意偏离经典偏好平衡切分的 EIG，是低延迟下的 exploitative heuristic。
3. 在 300 题 HotpotQA-style 端到端实验中，ECR 的 EM 为 0.297，relevance baseline 为 0.313，random control 为 0.207；它高于随机选择，但没有在普通相关性问答上证明相对 relevance baseline 的准确率优势。
4. 它选择候选池内的 claim，不估计 DeepWide 结果集之外尚未观察到的实体质量，也没有行/格层级的结构化损失。

这意味着合理路线不是回避 ECR，而是把 ECR 作为必须复现的有限假设基线，并通过开放集 OTHER 状态、unseen-mass posterior 与表级分层损失验证新增机制。

## 5. 信息增益能否成为 credit assignment：可行，但必须限定含义

### 5.1 先区分五个量

“信息熵增益”不是一个无歧义的 credit。至少有五个不同对象常被写成 information gain：

1. **期望信息增益**用于动作选择。在动作尚未执行时，

   \[
   \operatorname{EIG}_t(a)=H(Z\mid h_t)-
   \mathbb E_{o\sim p(o\mid h_t,a)}H(Z\mid h_t,a,o)
   =I(Z;O\mid h_t,a).
   \]

   它回答“这个动作预计能让代理知道多少”，不是“该动作导致了多少最终回报”。

2. **实现后的熵差**是单条轨迹上的观测量，

   \[
   \Delta H_t=H(b_t)-H(b_{t+1}).
   \]

   它可以为负。高价值反证把一个过度集中的错误信念重新打开时，短期熵会上升。

3. **Bayesian surprise**是

   \[
   S_t=D_{\mathrm{KL}}(b_{t+1}\Vert b_t).
   \]

   它总是非负，衡量信念改变幅度而非方向。无关新奇网页、对抗内容或错误消息也可能产生高 surprise。

4. **结果对齐的对数评分增量**在训练时有真值 $z^*$ 才能计算，

   \[
   c_t^{\log}=\log b_{t+1}(z^*)-\log b_t(z^*).
   \]

   证据把信念推向错误答案时它会给负值。IGPO、InfoReasoner 的实践 reward、TRACE、IG-Search 和 PBSD 都属于这一大族，而不全是 Shannon information gain。[26,23,44,29,53]

5. **任务因果贡献**比较一个步骤存在与被干预后的最终任务价值，

   \[
   c_t^{\mathrm{cf},k}=\mathbb E_{\tau_{>t}\sim\mu}
   [V_{\mathrm{task}}(h_t,a_t,\tau_{>t})-
   V_{\mathrm{task}}(h_t,g_k(a_t),\tau_{>t})].
   \]

   $g_k$ 可以是删除、语义替换、证据替换或工具输出扰动，$\mu$ 是固定 continuation policy。这个量才接近“若没有该步骤，任务是否会变差”，但它仍依赖干预定义、continuation policy、可比性与 overlap 假设。

因此，裸熵降最多是 **epistemic credit**。只有与最终任务价值、有效反事实和可靠证据共同验证后，才能称为 causal/task credit。

经典 credit-assignment 工作也支持这条边界。RUDDER 学习把延迟 return 重新分配到对 return prediction 有贡献的状态—动作；Hindsight Credit Assignment 用未来状态反推早期动作的相对影响；COMA 通过固定其他智能体动作、边际化单个动作构造 counterfactual baseline。[55–57] 三者的共同对象是回报贡献或 advantage，而不是信息量本身。Potential-based shaping 可以在特定形式下保留最优策略，却也不保证一个失校准的 entropy potential 对任务有意义。[42]

### 5.2 直接相关工作已经覆盖到什么程度

| 工作 | credit 单元与信号 | 是否需要 gold/特权信息 | 是否估计因果贡献 | 与本想法的关系 |
|---|---|---:|---:|---|
| TEPO (2602.02050) | 工具调用前后 token-segment entropy 是否下降 | 终局 F1；dense 版由终局正确性门控 | 否 | 已直接奖励 entropy-reducing tool call |
| InfoReasoner (2602.00845) | 语义答案分布的熵差；实践中用 gold-class log-prob gain | 是 | 否 | 已直接把 semantic IG 当检索步骤 credit |
| IGPO (2510.14967) | 相邻 turn 的 gold-answer probability/log-prob 增量 | 是 | 否 | 已把“信息增益大的 turn 多给 credit”实现为 RL 方法 |
| ECHO (2606.29745) | 显式后验上的 candidate elimination / posterior-sensitive turn reward | 训练环境给出可精确更新的有限后验 | 否；论文也承认不同 rollout 的同深度状态不相同 | 最直接术语撞车，已定义 epistemic credit 与 Bayesian advantage |
| SIOP (2605.04984) | 可靠 semantic outcome cluster 的 potential change | 无 gold，但依赖自生成 outcome modes | 否 | 说明无 verifier 时也已有 potential-based 信息 credit |
| TRACE (2607.13988) | frozen reference 下 gold-answer log-prob gap 的 TD 差 | 是 | 否 | telescoping turn credit，适合短且可验证答案 |
| LOTAPO (2607.13501) | 删除整个 turn 后 gold-answer likelihood 的变化 | 是 | 部分；作者明确称非正式识别的 causal effect | 能处理早期证据延迟显效，但删除上下文可能 OOD |
| STAMP (2607.11172) | training-time evidence graph 验证引用，再 credit 首次暴露该文档的步骤 | 是，需要参考 evidence graph | 否 | 深搜最接近；强调 discovery provenance 而非熵 |
| RICE-PO (2605.26352) | 同一 history 的局部 counterfactual retrieval 分支；只在 influence/stability 足够时回传 | 检索指标 | 局部近似 | 给出“同状态比较 + gate”这一必要设计 |
| CVT-RL (2606.05263) | 删除、语义/证据替换、工具扰动后的 verified success | verifier、outcome model、frozen continuation | 是，且列出识别假设；只称 PCCC surrogate | 最明确的干预式 baseline；计算昂贵且非开放世界 DeepWide 专用 |
| CRAFT / BiPACE (2606.29476 / 2606.25556) | sibling rollout 或近似同状态 action-conditioned baseline | 轨迹 outcome | 近似 | 说明 credit 的比较单元应尽量共享状态，而非同一 turn index |
| ACPO (2607.03126) / HAPO (2604.11056) / EMPG (2509.09265) | token entropy 用作可更新容量或不确定性权重 | 终局 outcome | 否 | entropy 在这里决定“哪里可学”，不决定“方向是否正确” [49,63,64] |
| A²TGPO (2605.06200) / T²PO (2605.02178) | gold-answer IG 的 turn-group credit/clipping；token/turn uncertainty progress 的 intervention/resampling | A²TGPO 需 gold；T²PO 用 outcome RL | 否 | IG/uncertainty 已直接控制 credit 与探索强度；不处理开放 denominator [74,75] |

ECHO 的范围最值得正面说明。它在 Clue Selector Game 中有均匀有限候选集、真实 oracle、确定性过滤和精确 posterior，主 reward 是候选集合的分数式收缩；实验只到 1.5B、约 10 turns。论文将近似信念、噪声或对抗来源、开放工具动作和 web search 明确列为未解决限制。[43] 这恰好留下 DeepWide 的工程与统计难点，但不留下“首次提出 epistemic credit”这一概念空白。TRACE、LOTAPO、STAMP、RICE-PO、SIOP、CVT-RL、CRAFT、BiPACE、ACPO、PBSD 和 PiCA 又分别覆盖 gold-readiness TD、删除 attribution、provenance、局部分支、label-free potential、显式干预、sibling counterfactual、state-matched baseline、entropy reweighting 与 privileged likelihood credit。[44–54]

2026-07-20 至 21 日的补充检索进一步收紧了 novelty。InfoPO 用 masked-feedback counterfactual 衡量一次用户反馈对后续动作分布的改变，再以 outcome gate 融合任务方向；AEM 在 response 粒度用 uncertainty proxy 重缩放 advantage；SELAUR 将 entropy、least confidence 与 margin 注入失败轨迹奖励。[66–68] STRIDE 把 outcome-discriminative pattern 与 saliency entropy 结合，APPO 则明确报告 token entropy 本身不能可靠定位影响最终结果的决策点。[69,70] PivoARL 从失败轨迹中定位 pivotal turn 并只从该状态重试，以 information-gain 视角解释信号集中。[71] A²TGPO 与 T²PO 又分别把 turn IG 用于归一/clipping，把 uncertainty dynamics 用于 intervention/resampling。[74,75] 因而，“信息增益 + counterfactual + outcome gate”“response-level entropy credit”“pivotal retry”与“uncertainty-guided resampling”均已有直接近邻。可辩护的范围只能落在 DeepWide 的四层开放世界任务变量、未见质量，以及 evidence provenance 与任务风险的联合验证上。

另一些相邻路线不直接用 entropy。GraphGPO 把多条 rollout 聚成状态转移图，以到目标的图距离变化分配 edge credit；ReBel 用 belief consistency 与 belief-aware grouping；OASES 学习一个随 search policy 共同更新、由终局 outcome 对齐的 state evaluator。[58–60] 它们要求 OWIC 证明“信息论表示”比图距离、belief consistency 或 learned progress evaluator 带来额外价值，而不能只证明任何稠密过程信号都比终局 reward 好。

Forage V2 使“未知完成边界”的 novelty 范围进一步收窄。它明确命名 denominator blindness，通过独立 Evaluator/Planner、共演 evaluation 和跨 run 组织记忆学习完成标准。[72] 因此本项目不能声称首次识别开放世界 denominator 问题。它仍留下的可检验差异是：是否能对未见质量与 premature-stop risk 给出校准概率，并与 anchor、row 和 cell 任务损失共同决策，而不是只通过组织审计学习 denominator。

Shared Discovery Paradox 表明“信念更准”与“覆盖更高”可以反向变化。在其可解的 16-box/8-searcher 基准中，pooling 将单个最佳建议的准确率从 0.20 提高到 0.3835，但 8 人重复该动作的群体发现率只有 0.3835，低于分散线索跟随的 0.8322；对 pooled posterior 做 8 动作 portfolio 可达 0.8594。[73] 这些理论数字不是 DeepWide 实验结果，但它们对 controller 提出直接约束：路由器必须联合 posterior、动作组合、来源依赖与多样性，不能将所有 worker 都派到同一个最高 posterior 或最高 entropy 项。

### 5.3 为什么“熵降越大，credit 越高”不可靠

- **相关性错误。** 一个与任务无关但很新奇的页面可以改变模型分布，却不提高 Row F1、Item F1 或最终成功率。
- **错误自信。** 多个镜像站复制同一错误值会让 posterior 更尖锐。熵下降为正，Brier/NLL 和任务风险反而恶化。
- **反证悖论。** 权威反证揭露原信念错误时，候选分布可能先变平；若只奖熵降，该纠错步骤得到负 credit。
- **假设集遗漏。** 真 anchor 或未发现实体不在当前 support 时，有限集合可以低熵收敛到错误答案。DeepWide 的 `OTHER` 与 unseen mass 不能省略。
- **surprise 陷阱。** KL surprise 奖励“改变大”，没有判定“改变对”。随机、对抗或过时网页都可能得高分。
- **冗余与证据依赖。** 两个同源网页不应各得一份 credit；首次发现、独立验证和最终综合也不是可互换的动作。
- **延迟与协同。** 第一步发现实体、第二步找到关系、第三步综合答案可能缺一不可。单步边际值依赖排列；只做 leave-one-turn 也不识别高阶交互。
- **删除干预失真。** 从已经生成的轨迹删除早期 turn，再保留后续动作，会产生代理在现实中不可能走出的上下文。LOTAPO 因此把自身定义为 attribution 而非已识别因果效应。[45]
- **训练与推理不一致。** gold-answer likelihood 在 RL 训练时可用，在线动作选择和无标签任务中不可用；把它写成 inference-time controller 会发生目标泄漏。
- **信用与探索不同。** VIME 等方法用 dynamics information gain 作 intrinsic exploration reward，但探索更多并不等于对最终任务贡献更大。[41]

这些反例说明，信息 credit 要先回答“关于什么随机变量的信息”“相对于什么任务损失”“在什么干预下有贡献”，不能只计算语言模型输出熵。

结构性 credit 还需要处理步骤间协同。若把一组步骤 $S$ 在有效重放下的任务价值写成 $v(S)$，两个步骤的二阶交互为

\[
I_{ij}=v(\{i,j\})-v(\{i\})-v(\{j\})+v(\varnothing).
\]

$I_{ij}>0$ 表示二者共同出现的价值超过各自边际值之和。Shapley value 可通过对所有有效加入顺序的边际贡献取平均来处理顺序依赖，但精确计算随步骤数指数增长，而且网页轨迹中的任意“步骤联盟”常无法形成有效状态。[65] 因此第一版只在高影响 discovery–verification、evidence–synthesis 对上做二阶干预诊断；若交互足够普遍，再评估 permutation-sampling Shapley，而不把全轨迹 Shapley 作为默认组件。

### 5.4 推荐的新主张：开放世界的结果对齐信息 credit

建议把候选方法暂称为 **Open-World Information Credit (OWIC)**。它不是新的 Shannon 公式，而是一套 DeepWide 特有的 credit 约束。名称有意不含 “causal”：AMR-SD 与 PGPO 已把 teacher/student 或有/无视觉条件下的 likelihood/KL 比称为 Causal Information Gain，但这种命名本身不等于干预识别；本项目只有在明确 intervention、固定 continuation、validity/overlap 与识别假设成立的分析中才使用 causal interpretation。[61,62]

1. **四层 credit target。** 分别追踪 anchor $A$、未见质量 $M$、行资格 $R_e$ 和 cell 值 $Y_{e,c}$，禁止用一个答案 entropy 覆盖四类错误。
2. **结果对齐。** 信息信号只有在改善 proper score 或任务风险时才为正。反证即使提高 entropy，只要降低错误风险也应获正 credit。
3. **开放世界。** `OTHER`、新 hypothesis 生成与 unseen-mass posterior 进入状态，避免在错误有限 support 上奖励收缩。
4. **局部反事实。** 对高影响步骤从同一 $h_t$ 执行等成本 sibling action、证据替换或 no-op，并用固定 continuation 比较 task value；不把不同历史的同 turn 当作同状态。
5. **provenance 分工。** 证据图分别记录 discovery、independent verification、contradiction resolution 和 synthesis。STAMP 的 first-exposure credit 是 discovery baseline，不应让后续独立验证永远得零。
6. **成本与伤害。** 无效查询、重复证据、无支持输出、污染来源和成本进入负项。

一个可检验的混合信号为：

\[
c_t = \underbrace{L(B_t)-L(B_{t+1})}_{\text{task-risk change}}
+\lambda\underbrace{\operatorname{RelIG}_t}_{\text{task-relevant epistemic gain}}
+\beta\underbrace{\widehat{\Delta}^{\mathrm{cf}}_t}_{\text{same-state contribution}}
+\rho\underbrace{c_t^{\mathrm{prov}}}_{\text{verified evidence role}}
-\eta\underbrace{C_t}_{\text{cost / harm}}.
\]

其中 $L$ 必须由 dev set 上冻结的 proper scoring rule 或 DeepWide task-risk surrogate 定义，$\operatorname{RelIG}$ 只计算与四层任务变量有关的信息；$\widehat{\Delta}^{\mathrm{cf}}$ 的干预族和 continuation policy 分开报告。为保持策略不被任意 shaping 改写，可把 $\Phi(B)=-L(B)$ 的差分作为 potential-based shaping 分量；Ng 等人的结论只在固定 MDP 与正确 potential 形式下保证 policy invariance，不能为错误 belief 或开放世界 support 提供保护。[42]

### 5.5 新颖性 verdict

| 版本 | 可行性 | 新颖性 | 建议 |
|---|---|---|---|
| token/response entropy 低或熵降大就多给 credit | 中，容易实现 | 很低；EMPG、TEPO、ACPO、AEM、SELAUR 等已覆盖 | 仅作消融 |
| semantic entropy reduction 作为 turn reward | 中 | 很低；InfoReasoner、ECHO 直接覆盖 | 强基线，不作主贡献 |
| gold-answer log-prob gain / TD credit | 高，训练信号稳定 | 低；IGPO、TRACE、PBSD、IG-Search 已密集覆盖 | 训练 oracle baseline |
| leave-one-turn 或首次证据 attribution | 中高 | 低到中；LOTAPO、STAMP 已覆盖 | provenance / retrospective baseline |
| 四层开放世界 task-risk + 同状态反事实 + provenance | 中，计算和数据要求高 | 截至检索日仍有候选空白 | 值得做，但必须用实验守门 |

最终判断是：**作为辅助 epistemic shaping，信息熵视角可行；作为唯一 credit 不可靠；作为校准、结果对齐、开放世界且经反事实验证的 DeepWide credit，仍有研究空间。**

## 6. 开放集合覆盖：为什么 width 不能只是 entropy

Good–Turing 估计用低频事件，尤其 singleton 的比例，推断尚未观察事件的总概率质量。Efron–Thisted 将 unseen-species 思想用于估计 Shakespeare 未见词汇；Chao–Jost 以 sample completeness 而不是 sample size 组织 rarefaction/extrapolation。[31–33] 数据库研究也曾用样本发现频率估计 aggregate query 中 unknown unknowns 的影响。[34]

Forage V2 进一步表明 denominator 本身可能随定义与证据演化，Shared Discovery Paradox 则表明同一 posterior 下的动作相关性会改变覆盖。[72,73] 因此，coverage 层不只需要一个“还有多少没见”的标量，还需要记录 denominator 定义不确定性、查询/来源依赖和重复动作造成的有效通道数。

这些方法不能原样套到网页搜索。经典估计通常假设样本来自稳定分布或可解释的重复捕获过程，而搜索引擎排序、查询改写、站点重复、SEO 与语言过滤都会造成强烈且依赖动作的选择偏差。可行做法是：

- 把不同 query family/source family 当成有记录的采样机制，不把同源镜像当成独立捕获；
- 跟踪实体在查询、来源、语言和时间切片中的 incidence/frequency；
- 用 Good–Turing/coverage 与 capture–recapture 型特征产生**遗漏风险估计**，再在 held-out task 上校准，而不是宣称得到无偏人口规模；
- 对已知有限名录、未知开放集合、网页不稳定三种任务分别报告；
- 用 synthetic hide-and-seek 和已知全集任务检查“预测剩余行数/质量”是否与真实遗漏相关。

最小开放世界信念应为 $M$，表示“下一轮仍能发现的有效实体质量/剩余集合规模”，而不是把 OTHER 粗暴设成一个固定类别。若观测到的新实体都是 singleton，低 anchor/cell entropy 也不能触发停止；若多个 worker 重复同一高 posterior 动作，名义并行度也不能当作有效覆盖。

## 7. 跨论文比较与 novelty verdict

| 文献族 | 信念对象 | 作用阶段 | 能否动态选动作 | 是否处理开放集遗漏 | 对本项目的结论 |
|---|---|---|---|---|---|
| Semantic Entropy、SePer | 答案语义类/生成器信念 | 推理评估 | 通常否 | 否 | 语义熵估计器已有 |
| FLARE、Self-RAG、TASR、Know Before You Fetch | 下一 token 或答案正确性 | 推理控制 | 触发/停止/预算档位 | 否 | adaptive retrieval 与校准停止已有 |
| CuriosiTree、C-IP、ECR | 决策/标签/答案假设 | 推理控制 | 是，按 EIG/EER | 通常固定有限集 | EIG 动作选择与熵停止已有 |
| Forage V2、Shared Discovery Paradox | 自发现 denominator；pooled posterior 与动作组合 | 覆盖审计/分配 | 是 | 是，但前者为自定义 denominator，后者为有限原子空间 | 分母盲区和 belief–coverage 分离已有；四层方法还需概率校准与 web 选择偏差验证 |
| InfoReasoner、IGPO、IG-Search、SIGHT、TEPO、IGRPO | gold-answer、语义答案或 rollout | 训练 | 学习后间接控制 | 否 | IG/entropy 训练奖励已有 |
| ECHO、TRACE、SIOP | 显式后验、gold-answer readiness 或自生成 outcome modes | turn-level RL credit | 是 | 否 | epistemic/potential/TD turn credit 已有 |
| LOTAPO、STAMP、RICE-PO、CVT-RL | 删除 attribution、证据 provenance、同状态局部分支或验证后的干预效应 | step/turn credit | 是 | 通常否 | attribution 与 causal baseline 已形成，裸 entropy 不够 |
| InfoPO、AEM、SELAUR、STRIDE、APPO、PivoARL | masked-feedback counterfactual、response entropy、uncertainty reward、outcome-discriminative pattern、pivotal retry | turn/token/response credit 与局部重试 | 是 | 否 | 信息信号与结果门控、反事实或 pivotal state 的组合也已有；四层任务变量才可能构成差异 |
| A²TGPO、T²PO | gold-answer IG 与 token/turn uncertainty dynamics | credit/clipping、intervention/resampling | 是 | 否 | IG/uncertainty 控制训练与探索已有；label-blind 分层 task risk 才可能构成差异 |
| TaS、A-MapReduce、Web2BigTable | 行、格、横向子任务 | 推理系统 | 是 | 启发式覆盖 | 表格状态与大规模宽搜已有 |
| WebSwarm、SearchOS | 搜索节点、网页结构、coverage/gaps | 推理系统 | 是 | 定性 open-set / scope audit | 动态 deep/wide 与覆盖驱动调度已有 |
| Good–Turing、coverage、capture–recapture | 未见事件质量/种类数 | 统计估计 | 不直接 | 是 | 提供 width posterior，但需处理搜索偏差 |

### 7.1 不能声称

- 首次把熵或信息增益用于搜索代理、RAG、工具调用、证据选择或停止。
- 首次用 entropy reduction、posterior contraction 或 gold-answer likelihood 给 turn/tool step 分配 credit。
- 首次提出 epistemic credit、belief-conditioned turn reward、leave-one-turn attribution 或 evidence provenance credit。
- 首次做 uncertainty-aware web agent、双层不确定性或动态 deep/wide routing。
- 首次把表格、coverage map 或 evidence graph 作为搜索状态。
- 低熵等于正确、完整或有充分证据。
- Good–Turing/capture–recapture 在搜索引擎偏置下自动给出无偏全集估计。
- 控制器“理论最优”，除非明确证明观测模型、校准、损失和 adaptive-submodularity 条件。

### 7.2 可辩护的候选创新

若论文只做推理时控制，建议沿用：

> **Entropy-DeepWide: Calibrated Hierarchical Belief Reduction for Open-World Deep-and-Wide Search**

若加入训练时 credit assignment，更准确的候选名是：

> **OWIC-DeepWide: Open-World Information Credit for Deep-and-Wide Search**

候选贡献不是使用熵，而是四个必须同时成立的设计：

1. **DeepWide 特有的分层随机变量。** $A$：隐藏 anchor；$M$：未见质量/剩余集合；$R_e$：候选行资格；$Y_{e,c}$：单元格语义值。
2. **开放世界 width。** 将有限候选 anchor/row 分布与 OTHER/unseen-mass posterior 联合，避免低已知行熵造成假完整。
3. **风险与成本耦合。** 动作按期望任务损失下降/成本路由，而不是把所有 entropy bit 等价相加。
4. **校准与可否证验证。** 分别证明各信号能预测 anchor、遗漏、行和格错误，并在同动作空间、同预算下优于 heuristic uncertainty；否则放弃 entropy-controller 的主张。
5. **credit 不等于熵差。** 训练时用 task-risk/proper-score change 确定方向，用同状态 counterfactual 检查任务贡献，用 provenance 区分发现、验证和综合。

检索到的文献中，没有一篇同时满足以上五点。但这只是截至检索日的**候选空白**；Forage V2 的 denominator audit、Shared Discovery Paradox 的 belief–coverage 分离、SearchOS 的 scope audit、ECR 的有限假设 EER、C-IP 的校准、CuriosiTree 的 EIG/cost、ECHO 的 epistemic credit、STAMP 的 provenance 和 CVT-RL 的反事实贡献已覆盖各个相邻部分。论文必须正面比较这些近邻，不能靠改名构造差异。

## 8. 建议的分层开放世界熵框架

### 8.1 信念状态

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

### 8.2 动作与观测

动作集合至少包含：

- `resolve_anchor`：寻找可区分竞争 anchor 的线索或反证；
- `discover_entities`：扩展新行，改变 $M$ 与候选集合；
- `test_row_constraint(e)`：验证某行是否满足入表约束；
- `fill_cell(e,c)`：获取缺失属性；
- `falsify_cell(e,c)`：寻找否定或冲突来源；
- `audit_scope`：针对潜在名单边界或全集来源做覆盖检查；
- `stop_or_abstain`：生成表格并保留不确定/未证实格。

动作观测不是 Tavily answer/snippet 的文本本身，而是带 URL、页面正文跨度、发布时间、来源类型、抽取命题和 provenance 的 evidence event。重复站点与镜像必须去相关，否则多份复制内容会伪造熵下降。

### 8.3 路由与停止

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

## 9. 实验必须回答的失败模式

### 9.1 估计器是否可靠

对 anchor、row、cell 分别报告 AUROC/AUPRC、Brier、NLL、ECE 与 risk–coverage；对 $M$ 报告剩余行数/质量误差、row recall calibration、premature-stop rate。比较 semantic entropy、token entropy、margin、verbalized confidence、support count、recent yield、source diversity 与 calibrated ensemble。若 entropy 在相同成本下不能稳定优于简单信号，核心假设应判失败。

### 9.2 controller 是否真的由信号获益

所有 controller 比较必须共享模型、搜索/浏览工具、动作集合、最大 token、tool call、wall-clock 和重试次数。必须包含：当前 retrieve-then-generate、fixed wide→deep、fixed deep→wide、TaS/no-entropy planner、相同 controller 加 heuristic uncertainty、oracle one-step value（仅分析）、WebSwarm/SearchOS/A-MapReduce 系统级比较。只和 ReAct 比不够。

### 9.3 低熵错收敛

构造或标注三类诊断集：真 anchor 不在初始 top-k、重复错误网页占多数、权威反证后到。检查 `OTHER`、hypothesis regeneration 与 falsification 是否能避免低熵错误停止。ECR 是有限假设对照。

### 9.4 开放集遗漏

在已知完整列表、synthetic hide-and-seek 与真实开放列表上分别测试。搜索接口强偏置会破坏经典 unseen-species 假设，因此需要按 query/source family block bootstrap，并报告估计在语言、领域、时间敏感任务上的偏差。

### 9.5 评测污染与 judge 可靠性

Search-Time Contamination 研究指出，联网 agent 可能检索到公开 benchmark 问题或答案，造成分数膨胀。[35] 运行时必须屏蔽 benchmark 名、instance id、gold/evaluation 路径，记录并扫描 URL/页面中的 benchmark 字符串。REFLECT 还报告深度研究 LLM judges 对细粒度失败的准确率不足 55%，尤其不擅长证据验证；因此官方 LLM judge 指标需配合分层人工抽检、双人复核和 judge disagreement 报告。[36]

### 9.6 credit assignment 是否定位了真正有贡献的步骤

信号评估不能只看训练后最终分数。应建立带干预的 step-credit audit set：对同一状态执行原动作、等成本 sibling、no-op、证据替换和反证动作，再用固定 continuation 估计最终任务风险差。报告 credit 与该差值的 Spearman、signed accuracy、top-k pivotal-step recall 和 calibration，并单列以下诊断：无关但新奇信息、重复错误来源、先升熵后纠错、延迟显效、多步骤协同、删除后 OOD。比较 raw entropy drop、semantic entropy drop、gold log-score gain、TRACE-style TD、LOTAPO、STAMP、RICE-PO、CVT-RL-style counterfactual 和 OWIC。若 OWIC 只与 entropy change 相关、却不能预测干预后的 task value，它不能称为 credit assignment 方法。

## 10. 对当前项目的直接诊断

当前仓库已推进到 V2.39.9 的可恢复 staged runtime，但仍不是完整 Entropy-DeepWide。runtime 只读取 `{opaque_id, question}`，支持 Tavily、Azure hosted 和 Anthropic hosted search、持久 JSON state、开放集 anchor/`OTHER`、scope/candidate discovery、mention recall、逐行/逐格查询、cell-level provenance、行级 quarantine、单位尺度审计和确定性表格渲染。V2.20.1–V2.39.5 逐步加入 anchor evidence、闭合/混合行域、named-node bridge、rank-slot occupant、目录遍历、URL quarantine、日期/人名 canonicalization 与 post-verification publishable coverage。V2.39.6 把 logical request、成功/失败 response 和 HTTP attempt 分开持久化，并将 candidate reservation 从 32K 降到 20K。V2.39.7 又把 launch capacity envelope 改为 400KB UTF-8 bytes×20K，记录无内容的 request-size ledger，增加只改属性不改 membership 的 confirmed-member unknown-cell recovery，并支持公元 1–9999 年和中文事件时间列。V2.39.8 把固定槽位中已有页面证据的实体属性加入后续缺格查询并修正 fixed-row unknown 统计；V2.39.9 收紧目录人口证明、修正中文证据句柄，并在严格 provenance 条件下恢复 reviewer 遗漏序列化的结构化身份边。尚未实现的仍是经过开发集校准的四层概率信念、unseen-mass posterior、entropy/EIG/task-risk controller、同状态干预 credit 和 RL 训练。

V2.31–V2.33 的 validation smoke 依次为 1/2、1/2 和 0/2 completed。V2.32 唯一完成的 50 行任务得到 Entity 1.00、Row F1 0.76、Item F1 0.90、Column F1 1.00，但同批另一题失败且整表 score 为 0；一个完成任务不能支持聚合改进或 SOTA。V2.33 的两个失败分别是 32/60 coverage 与 bridge unresolved。V2.35 consumed-task replay 得到 60/60 rank slots、60/60 query routes 和真实候选页 reserve，但不运行 reviewer、搜索、预测或 evaluator，因此不估计质量。机器证据分别见 [`results/validation_smoke_v232_20260722.json`](results/validation_smoke_v232_20260722.json)、[`results/validation_smoke_v233_20260722.json`](results/validation_smoke_v233_20260722.json) 与 [`results/v235_structural_boundaries_replay_20260722.json`](results/v235_structural_boundaries_replay_20260722.json)。

V2.35 随后的两题 validation cold-start 为 1/2 completed。完成题的固定财政年度行与列结构正确，但 Row F1 为 0、Item F1 为 0.4167，10/10 行至少一格错误；另一题因行级 membership provenance 错误升级成批级异常而失败。保守两题 Item F1 为 0.2083，整表 score 仍为 0。V2.36 随后进行了新的两题严格 cold-start，但为 0/2 completed：一题 post-freeze gold 有 1,037 行，而冻结 runtime 容量仅 250 且只发现 13 行；另一题 bridge confidence 0.68，downstream search 为 0。两题消耗 4,966,036 system tokens、52 次模型调用和 168 次 logical search，搜索 logical failure 为 0。没有表格预测，Entity/Row/Item/Column 指标未定义。V2.37 的 partitioned bulk 与 graph inversion 目前只有 258 项测试证据，尚无 fresh 分数，不能宣称性能改善。机器结果见 [`results/validation_smoke_v235_20260722.json`](results/validation_smoke_v235_20260722.json) 与 [`results/validation_smoke_v236_20260722.json`](results/validation_smoke_v236_20260722.json)。

V2.37 随后的两题 validation cold-start 仍为 0/2 completed。制药题验证了 4 个页面 pivot，但 bridge 仍 unresolved；学科题把真实 55×3=165 行错估为 171，只保留 12 行并触发 coverage gate。两题消耗 4,834,235 system tokens、47 次模型调用和 202 次 logical search。V2.38 在该已消费学科题的离线诊断中从官方目录得到 55 个成员、55/55 成员页和 165/165 rank slots，并把 85 个唯一学校压缩为 43 条属性查询；该结果只验证确定性机制，不估计 F1。V2.38 随后 fresh smoke 为 1/2 completed：完成题 Entity 1.00，但 Row F1 0、Item F1 0.0867、Column F1 0.1786，50 个 gold 实体只匹配 5 个且 cell uncertainty 为 96%；另一题被英文范围 validator 拒绝。V2.39.1 针对这两个通用机制增加英文范围、occupant-first attestation 与独立 post-occupant attribute pass，已有 282 项测试证据但尚无 fresh 分数，不能宣称性能改善或 SOTA。机器结果见 [`results/validation_smoke_v237_20260722.json`](results/validation_smoke_v237_20260722.json) 与 [`results/validation_smoke_v238_20260722.json`](results/validation_smoke_v238_20260722.json)。

V2.39.2 的两题 fresh smoke 为 1/2 completed。失败题以 `28<45` fail closed，运行账本精确一致；完成题输出 25 行但每行都有 unknown，并有 6 组中间名/后缀别名。官方 evaluator 将 25 行多对一映射到 21 个键后返回 Column Recall 1.1905、F1 1.087，严格 wrapper 拒绝该越界结果，因此 `valid_n=0`、质量指标未定义。V2.39.3 的 consumed-task 零调用 replay 把 25 行压到 19 行并重新以 `19<21` fail closed，同时把旧 renderer 的英文日期恢复为题面要求的 ISO。它只验证边界修复，不证明 F1 提升。该结果不是全集、held-out test 或 SOTA 证据。结构证据见 [`results/v2393_visible_format_person_alias_replay_20260723.json`](results/v2393_visible_format_person_alias_replay_20260723.json)。

V2.39.3 随后的两题 fresh smoke 为 0/2 completed：作品枚举止于 `44<54`，国家×年份任务止于 `6<12`。没有可评预测，`valid_n=0`，所有质量指标均为 `null`；57 次模型调用、192 次 logical search、1,629 次 fetch 和 5,469,273 system tokens 的账本完全一致。终态后才确认第二题的 6 行是成员 seed 而非最终成员×年份行。V2.39.4 的零调用 replay 将其展开为 24 行并使结构 coverage 通过，但不能说明值格正确；V2.39.5 的 post-verification gate 进一步防止 unresolved、无 membership evidence 或别名重复行在最终完成度中充数。机器证据见 [`results/validation_smoke_v2393_20260723.json`](results/validation_smoke_v2393_20260723.json) 与 [`results/v2394_mixed_row_domain_replay_20260723.json`](results/v2394_mixed_row_domain_replay_20260723.json)。当前仍无全集、held-out test 或 SOTA 证据。

V2.39.5 随后的两题 fresh cold-start 同样为 0/2 completed，但这次不能归因于 coverage 算法：两个 32K candidate extraction 请求都连续 8 次收到 GPT-5.6 429。短模型 probe 与 Anthropic search probe 启动前均为 2/2，说明短健康检查不能代表大输入/大 output reservation 的真实容量。搜索侧 69 次 logical calls、555 次 fetch 账本一致；模型进程有 20 个成功响应和 60 次 attempts，state 仅保存 18/40，因此 observability 失败。V2.39.6 的 20K candidate cap 基于 735 个历史 trace（p95 7,019，p99 9,902，max 18,134），并新增 120K 字符非 benchmark 输入×20K reservation 的连续容量探针与单 candidate worker。机器证据见 [`results/validation_smoke_v2395_20260723.json`](results/validation_smoke_v2395_20260723.json)。当前仍无全集、held-out test 或 SOTA 证据。

V2.39.6 的两题 fresh cold-start 为 1/2 completed。完成题的 6 个实体全部匹配 gold，官方 Entity 1.00、Row F1 0.6667、Item F1 0.7778、Column F1 1.00，但整表 score 仍为 0；另一题在 belief 请求连续 8 次 429 后失败。运行精确记录 35 个 logical requests = 34 successes + 1 failure、58 HTTP attempts、101 次 logical search、811 次 fetch 与 3,387,703 system tokens，process/task/state 完全相等。该证据支持容量与 failure-observability contract，却仍不支持 entropy、credit、全集或 SOTA 主张。机器证据见 [`results/validation_smoke_v2396_20260723.json`](results/validation_smoke_v2396_20260723.json)。

V2.39.7 的两题 fresh cold-start 均完成，官方 evaluator 为 `valid_n=2, errors=0`。iPhone 题 Entity 1.00、Row F1 0.2703、Item F1 0.7243、Column F1 0.9189；车辆题 Entity 1.00、Row F1 0、Item F1 0.3214、Column F1 1.00；两题均值为 Row F1 0.1351、Item F1 0.5229、Column F1 0.9595，整表成功仍为 0/2。iPhone 题输出 34/40 gold 实体，134/200 个评分格通过、10 行全对；车辆题命中 4/4 实体，却只有 18/56 个评分格通过且没有全对行。91/91 logical model calls、135 HTTP attempts、378 search calls、487 hosted tool calls 和 3,073 fetches 的账本完全一致。该证据说明 completion 与 component metrics 可以同时改善而整表仍失败，也表明 fixed row 的值填充是独立瓶颈；它仍不支持 entropy、credit、全集或 SOTA 主张。机器证据见 [`results/validation_smoke_v2397_20260723.json`](results/validation_smoke_v2397_20260723.json)。

V2.39.8 针对车辆诊断中可见的通用机制，只提升 fixed-membership 行里 `supported/corrected` 且带地址化 evidence ID 的实体属性，使后续缺格查询同时绑定槽位与已验证对象；它不改 row key、`search_identity`、eligibility 或 membership。已消费 state 的零模型、零搜索、零 evaluator 回放生成 38 条查询，38/38 都含相应 make/model/year，并将 V2.39.7 漏报的 fixed unknown 行从 0 重算为 4。随后两题 fresh cold-start 终态为 0/2 completed：一题把 Wikipedia 普通文章的 `/wiki/*` 导航云误当 104 个目录成员并 fail closed；另一题的正确概率 leader 始终是春节联欢晚会，但 reviewer 将 C02/C03/C04 的引证写进 `supported_clues` 而未填 `identity_support`，最终错误候选因残留结构化 edge 占优。11/11 model calls、19 attempts、70 search calls、87 hosted tool calls 和 766 fetches 账本一致；没有预测，官方质量指标为 `null`，不能把保守 failure-as-zero 诊断称作官方分数。机器证据见 [`results/validation_smoke_v2398_20260723.json`](results/validation_smoke_v2398_20260723.json)。

V2.39.9 将这两个失败抽象为通用证据边界。目录 fast path 现在要求独立正行数尺度、源 URL 为成员 URL 的严格祖先，并阻止站点根页借用深层内容流作为人口证明；`E0001直接记载` 这类中文紧邻句柄使用 ASCII 标识符边界解析。若 reviewer 只在 `supported_clues` 声明支持，sanitizer 仅在 clue ID 属于计划中的判别 clue、`E####` 当前 stage 可见并在 candidate direct support 中、且该页真实命名候选或验证别名时恢复结构化 edge。概率、自然语言声明或页面只命名候选均不能单独创造 credit。347/347 tests 与静态审计通过；两个已消费 state 的零模型/搜索/scoring 回放关闭错误目录 fast path，并让终审正确概率 leader 恢复 C02/C03/C04 后由原有 noisy-premise gate 选为 provisional。该 artifact 的 `quality_metrics=null`、`quality_claim_allowed=false`，不证明后续表格完成、F1、held-out 或 SOTA，见 [`results/v2399_boundary_replay_v2398_20260723.json`](results/v2399_boundary_replay_v2398_20260723.json)。

V2.39.9 随后的两题 fresh cold-start 为 1/2 completed。唯一有效预测覆盖 runtime 预期的 35 行，但只有 4 行全格完整，31 行仍有 unknown；released evaluator 得到 Entity 1.00、Row F1 0.0328、Item F1 0.4836、Column F1 0.8197，整表 score 为 0。outer join 中 25 个实体匹配、10 个 gold-only、1 个 prediction-only，144 个评分格通过 59 个且只有 1 行全对；其中英文名称与中文名称各通过 25 格，票房通过 8 格，日期仅通过 1 格。另一题的 candidate response 用满 20K output tokens，两次 repair 又各用满 4K，最终仍为 `JSONDecodeError`。把该 failure 计零的两题保守 Row/Item/Column F1 为 0.0164/0.2418/0.4098，整表成功 0/2。87/87 logical model calls、116 attempts、236 searches、294 hosted tool calls、2,077 fetches和 5,862,488 system tokens 的账本完全一致。该两题结果不支持 entropy、credit、全集或 SOTA 主张，见 [`results/validation_smoke_v2399_20260724.json`](results/validation_smoke_v2399_20260724.json)。

V2.40.0 只针对这次终态后可见的两个通用输出边界。JSON client 现在记录无内容的 `output_truncated` 布尔标记；若且仅若前一响应达到输出上限，下一次 parse repair 才继承原 stage token reservation，普通 malformed JSON 仍保留 4K 上限。日期规范器只从可见的 format token 或紧邻示例识别中文日期约定，并区分 `YYYY年MM月DD日` 与 `xxxx年x月x日`；裸截止日期不会改变默认格式。354/354 freeze tests、静态审计和 GPT-5.6 短请求、400KB×20K capacity、Anthropic 搜索各 2/2 preflight 通过。随后的两个 fresh validation opaque ID 均失败，因此 V2.40.0 没有 completed prediction 或官方质量分数，也不能把 V2.39.9 日期格的离线可修复性当作得分提升。

V2.40.0 的两题 fresh smoke 随后终态为 0/2 completed。中文体育荣誉题已检索到一页包含完整 31 个冠军记录的列表，但该页使用 `男团/男单/男双/混团/世乒赛` 等源 surface，candidate worker 输出规范化后的复合键；现有 gate 要求每个规范化键字段都在 membership page 中精确可见，因此 discovery、recovery 和 final coverage 共隔离大量本可进入 verifier 的行，最终仅 1 行通过且以 `1<30` fail closed。英文职位题形成 5 个候选，官方 DOJ/USAJOBS 页面分别支持 title、control number、appointment type、deadline 等字段，但没有可地址化的跨页 scope-predicate 合取；row verifier 后 5/5 行仍 unresolved，renderer 为 0 行，output contract fail closed。两题共 79/79 logical model calls、83 attempts、223 searches、273 hosted tool calls、1,836 fetches和 6,785,857 system tokens，process/task/trace 账本完全一致。没有 completed prediction，released evaluator 未运行；V2.40.0 没有质量分数，见 [`results/validation_smoke_v2400_20260724.json`](results/validation_smoke_v2400_20260724.json)。

这两个 failure 将下一版的证据边界分成两类。对同页结构化列表，原文 record 与最终 canonical value 必须分开：逐行 ledger 应保存 page ID、verbatim record 和每个 identity column 的 source surface；若 surface 与 canonical value 不同，该行只能以 unresolved 进入 verifier，不能直接获得 eligible membership。对 predicate-defined population，多个页面可以分别支持不同资格条件，但必须先由 visible question 产生结构化 predicate catalog，再逐谓词绑定 page evidence；任一必需谓词缺失时行仍 unresolved。简单把 exact gate 从 `all` 改成 `any` 会允许 sibling borrowing 和泛列表建行，因此不属于可接受修复。

V2.40.1 已把上述设计落实为 schema 58：普通与 bulk candidate 都携带逐行原文 membership record，source surface 与 canonical key 分开；scope 只由可见问题生成 `P01...` catalog，逐行 predicate ledger 可以跨页合取，但每页必须局部包含该行 canonical key 或已验证 source surface，且单隐藏主体必须同页可见。verifier 前保留当前上下文实际可见的 ledger ID，普通 value refinement 后增加 bounded membership-gap recovery；renderer 对缺谓词或零发布行 fail closed。366/366 tests 与已消费 V2.40.0 state 的零调用回放通过。该回放只证明结构机制，没有 fresh 分数，也不能支持 entropy、credit、全集或 SOTA 主张。

V2.40.1 随后的两题 strict cold-start 均在 `row_refinement` 失败。第一题跨 sibling source item 借用 identity surface，并遗漏 record/predicate page IDs 到 membership ledger 的闭合；第二题返回非对象 membership record，把未局部包含精确行身份的同一页面绑定到 P01–P05，并同样遗漏 predicate IDs。两题共 238 次模型调用、259 attempts、344 次搜索、10,514,365 system tokens 与 14,119.09 秒任务墙钟，过程账本全部通过。没有 completed prediction，released evaluator 未运行；保守全零只用于把 forward failure 明确纳入分母，不能称为官方质量结果。该结果支持“refinement 的属性更新权与 membership ledger 必须隔离”这一工程诊断，不支持信息熵或 credit 假设。

V2.40.2（schema 59）据此将普通 refinement 限制为 attribute-only。prompt 不再暴露 membership/identity ledger，越界的 eligibility、membership、predicate 和 alias 输出被丢弃，原 membership ledger 只读保留；record/predicate page IDs 确定性并入 membership/evidence union。malformed record 与非局部 predicate page 仍被严格 validator 拒绝，无效 delta 则逐行 quarantine，保留原 unresolved 行。普通 refinement batch 从 1 提到 4。Python 3.12 共发现 373 项测试，372 通过、1 项因 released evaluator 可选依赖缺失而跳过；compile、diff、secret 与 label-blind audit 通过。

已消费 V2.40.1 两题的 V2.40.2 离线回放没有调用模型、搜索或 evaluator，源 state hash 与调用账本不变。历史 refinement 分别消耗 20 与 135 次模型调用；在所有风险行均可单遍处理的条件下，batch=4 的调用下界为 2 与 13。这个反事实下界没有运行新的模型，也没有观察真实 retry、质量或延迟，因而只能作为机制/成本规划证据，不能写成成本下降或性能改进。后续 V2.40.2 fresh 结果必须与该机制回放分开报告，entropy 与 credit 仍为 shadow-only。

V2.40.2 随后消费了 validation inventory 的最后两个 ID。两题均完成，released evaluator `valid_n=2, errors=0`，但整表 score 都为 0；聚合 Entity Accuracy、Row F1、Item F1、Column F1 为 0.50、0、0.147619、0.50。SIPRI 题的 30 个主键全部匹配，但 210 个评分格只有 62 个通过。国家和年份各贡献 30 格，GDP 贡献 2 格，全球排名、军费、总统、国防部长没有通过格。三轮属性查询几乎都选择 GDP source family，150 个 residual unknown 只恢复 2 个。Fortune 题内部输出 10 行全格完整，但 caption 只显示英文 canonical subject，遗漏 anchor review 已页面验证的中文 alias `世界500强`，官方 entity gate 因此短路为全 0。这个结果说明“正确搜索状态”和“benchmark 可见主体 surface”属于不同的任务风险项，也说明查询数量不等于跨列信息覆盖。权威机器证据为 [`results/validation_smoke_v2402_20260725.json`](results/validation_smoke_v2402_20260725.json)。

V2.40.3 将上述两个边界写成 label-blind 机制。cell template 同时按目标列与行实体排序，最多保留 12 个 planner template；固定行网格超预算时先给每个缺失列预算，再在列内分块行。每条 query 显式写入目标列，并保留精确 `query_to_rows`。可见 caption 只从被选 anchor candidate 的 `verified_aliases` 取与题面语言一致的 surface，canonical subject 仍是内部检索与证据 key。Python 3.12 的 379 项测试中 378 项通过，1 项因 released evaluator 可选依赖缺失而跳过。

已消费状态的 V2.40.3 零调用 replay 将 Fortune caption 变为 `2025 Fortune Global 500（世界500强）`，10 行仍通过输出契约。SIPRI 的 148 个风险 `(row, column)` 在 72-query initial plan 与 96-query refinement plan 中均全覆盖；五列的 query 份额分别为 15/15/14/14/14 与 20/19/19/19/19。这个 artifact 没有调用模型、搜索、mapping 或 evaluator，因此只证明规划与呈现契约，不证明页面 yield、格值正确率、成本下降或 entropy/credit 效果。40/40 validation ID 已消费，后续 V2.40.3 只能先做未消费 public-dev 工程 smoke，不能称为 fresh validation、held-out 或 SOTA。机器证据为 [`results/v2403_column_fair_caption_replay_v2402_20260725.json`](results/v2403_column_fair_caption_replay_v2402_20260725.json)。

V2.24 的两题开发 smoke 已冻结并经官方 evaluator 检查，机器证据见 [`results/dev_smoke_v240_20260721.json`](results/dev_smoke_v240_20260721.json)。一题因 anchor unresolved 失败；完成题的 Entity Accuracy 为 1.0，Row F1 为 0.3636，Item F1 为 0.7078，Column F1 为 0.9610，整表 score 为 0。把失败题计 0 后，两题保守 Entity Accuracy、Row F1、Item F1、Column F1 分别为 0.50、0.1818、0.3539、0.4805。完成题预期 40 行却只输出 37 行，且 row query 丢失逐行年份并错误复用类别模板。V2.25 的无模型、无搜索、无 evaluator 结构回放把 37 行补为 40 行，并让 40/40 行都获得含自身年份和类别的查询；证据见 [`results/v250_closed_domain_replay_zh094_20260721.json`](results/v250_closed_domain_replay_zh094_20260721.json)。该回放只证明结构缺陷被修复，不证明任何线上 F1 或排行榜提升，已看过 gold 的 V2.24 题也不会重跑后冒充 held-out。

V2.25 还在 12 个无历史 forward artifact 的 dev opaque ID 中按字典序盲选了 2 题，选择过程不读问题、instance ID 或 gold。GPT-5.6 与 Anthropic search preflight 均连续 2/2 成功，但正式 cold-start 是 0/2 completed。一题走 open-domain route，在 mention-gap merge 中因决定性行资格缺页面证据而严格失败；另一题 anchor unresolved。总计 308 个 logical search calls、0 search failures、持久化 system-token 合计 5,465,863 与 2,477.414 秒 wall time。进程实际记录 41 次模型调用，task state 却只持久化 24 次，因为失败的并发 worker traces 在 future 抛异常前未合并。因此上述 token 数低估了 17 次失败 worker 调用。没有冻结预测，官方 Entity/Row/Item/Column 指标未定义，不是 0；也不执行选择性 evaluator。机器证据见 [`results/dev_smoke_v250_20260721.json`](results/dev_smoke_v250_20260721.json)。

V2.26 在剩余 10 个无历史 forward artifact 的 dev opaque ID 中继续按字典序盲选 2 题。两题均完成，16 个 targeted mention workers 的真实运行没有再因局部 semantic-invalid output 使整题失败。进程与 task 账本的 109 次模型调用、118 次 attempts 和 token 数逐项相等；运行还使用 751 次 logical search、14,113,270 system tokens 和 7,067.670 秒，search failure 为 0。官方两题均值为 Entity 0.50、Row F1 0.07965、Item F1 0.23009、Column F1 0.28319，SR 0。机器证据见 [`results/dev_smoke_v260_20260721.json`](results/dev_smoke_v260_20260721.json)。

这两题把四层风险的边界显示得更清楚。第一题的 visible row set 没有 anchor 错误，但只输出 34 行；官方 parser 得到 32 行，对 81 个 gold 行漏 50 行。冻结 state 的 final shadow snapshot 同时给出 0.95 的未校准 unseen-mass proxy 和 6 个 missing partitions。这一单题不能校准 posterior，却说明已知行的 cell 状态与开放集 denominator 必须分开。第二题的 anchor review 用 5 条辨识线索验证 Salvador Dalí，scope plan 正确指向西班牙 17 个自治区，但最终表格没有显式“西班牙”，官方 entity gate 因而短路为全 0；同一表格还把 17 个规范行和 17 个 alias/重复行并成 34 行。这不是新的第五层 epistemic uncertainty，而是 belief-to-output contract 与 canonicalization 的接口错误。若不单列该接口损失，训练标签会把 renderer 失败错误归因给 anchor entropy 或搜索步骤。

因此，V2.26 只支持“failure observability 和 completion boundary 生效”。它没有支持 entropy、controller 或 credit，也没有支持扩大运行规模。更具体地，它要求未来 credit audit 区分三类贡献：获取新事实、校正/合并规范身份，以及把已知 scope 正确呈现在最终答案。第三类可能提高官方结果，却没有带来 epistemic information gain；若把它奖励为熵降，会混淆搜索 credit 与输出接口 credit。

官方 evaluator 对现有 220 题单次预测的结果为：SR 2.27%（5/220）、Core Entity Accuracy 67.73%、Row F1 19.48%、Item F1 34.14%、Column F1 41.03%。按 instance-id 前缀做预测后离线分组，Deep2Wide 85 题为 0/85 成功、Entity Accuracy 44.71%、Row F1 4.89%；Wide2Deep 135 题为 5/135 成功、Entity Accuracy 82.22%、Row F1 28.67%。这些值可追溯到 [`results/baseline_gpt55_20260623.json`](results/baseline_gpt55_20260623.json) 及其所列原始输出。该历史 run 未做 search-time contamination 扫描，因此是工程诊断而非投稿级结果。

旧全量差异支持“anchor 是 Deep2Wide 的优先瓶颈”，单个 Wide2Deep 压力题则暴露了候选保留与证据连续性问题。V2.18 真冷启动在 `wide2deep_ws_zh_003` 上输出 41 行，命中 36/60 个 gold 主键，Row F1 为 33.66%，Item F1 为 58.75%；它使用 568 次搜索和 1,075,958 tokens。冻结该预测后的 trace audit 发现，多所实体已经有目标专业、年份和值局部共现的页面，却因 scope adjudicator 保持 unresolved 而在 reducer 被删除；另一些候选的正确页面没有稳定进入后续 bounded verifier prompt。

V2.19 针对这两个 label-blind 机制做了 evidence-continuity 修复。它的 stage-reuse diagnostic 只复用 V2.18 已有 runtime evidence 与 mention adjudication，清空并重跑行级 verifier，本进程新增搜索调用为 0。该诊断输出 44 行，命中 42/60 个 gold 主键，Row F1 为 50.00%，Item F1 为 70.51%，Column F1 为 80.77%。随后从空目录运行的 V2.19 输出 52 行，同样命中 42/60 个 gold 主键，Row F1 为 46.43%，Item F1 为 65.48%，Column F1 为 75.00%；相对 V2.18 cold-start，Row F1 与 Item F1 分别提高 12.77 和 6.73 个绝对点，搜索调用从 568 降到 546。该单题结果只支持进入固定 8 题 pilot；它不能证明跨题泛化、不能当作排行榜成绩，也不能证明 entropy 有效。

固定 8 题 patched pilot 的证据在 [`results/patched_dev8_v2191_20260720.json`](results/patched_dev8_v2191_20260720.json)。其中 7 题是 V2.19 cold-start，1 题是 V2.19.1 的 label-blind checkpoint resume，因此不是完整冷启动榜单。严格把 evaluator-invalid 汽车题计 0 后，SR 为 12.50%，Core Entity Accuracy 37.50%，Row F1 18.53%，Item F1 25.30%，Column F1 28.08%；总成本为 5,273,797 tokens、2,918 次 search calls、112 次 search failures 和 10,762.026 秒累计 wall time。只看 7 个 valid evaluator 任务会得到更高均值，但不能隐藏第八题的 evaluator 缺陷。该结果没有支持扩到 40 题。

两道 Deep2Wide 失败题又进行了四轮 anchor-only stage-reuse。汇总 artifact 为 [`results/anchor_replay_dev2_v2201_v2204_20260721.json`](results/anchor_replay_dev2_v2201_v2204_20260721.json)。V2.20.1–V2.20.4 每轮 Core Entity Accuracy 都是 0/2。V2.20.1、V2.20.2 和 V2.20.4 的 post-search official-candidate recall 是 2/2，V2.20.3 是 1/2；这说明候选可见性通常不是充分条件，合取身份线索的证据绑定和选择仍然失败。V2.20.4 让两题在证据不足时保持 unresolved，阻止错误主体继续扩表，但没有提高准确率。四轮合计 298,303 tokens、24 个新搜索 query、86 次 HTTP search attempts、6 次失败和 509.437 秒。所有 replay 均标为 `cold_start:false`，且这些公开 dev 题的 official entity 已在预测冻结后用于工程诊断；任何后续同题结果都不能当作 held-out 或排行榜证据。

泄漏审计发现旧 smoke 脚本曾把生成与本地近似 gold evaluation 放在同一进程。新 runtime manifest 已限制为 `{opaque_id, question}`，预测完成后再由独立 evaluator 读取 instance ID、subset label 和 gold table；现有 162 项测试包含 manifest 边界、anchor replay provenance、identity support、闭合行域防伪、通用 verifier、Tavily key 轮换、历史迁移版本、evidence continuity、checkpoint drift、evaluator retry、targeted no-op 和并发故障 trace 检查。本地免 key GPT-5.6 proxy 与 Anthropic server-side search 在 V2.26 preflight 均 2/2 成功；正式 run 的 109 次模型调用与 118 次 attempts 也全部完成。Azure hosted search 历史偶发 429。正式投稿仍需补 search-time contamination scanner、精确 span、output-contract tests 和跨进程文件权限审计。

## 11. 结论

信息熵适合作为这项工作的理论主线，但不能作为孤立 novelty。已有文献已经覆盖语义熵、信息增益奖励、EIG 动作选择、熵驱动证据选择、校准停止、表格状态、动态深宽搜索、未知 denominator 审计、belief–coverage 分离，以及 posterior-sensitive turn credit。可辩护的新问题是：DeepWide 的隐藏 anchor、开放集合遗漏、行资格和格值是否需要一个统一但不简单相加的分层信念模型，以及这个模型能否在同预算下比简单 heuristic 更准确地分配搜索；若进一步训练策略，分层风险变化能否在同状态反事实与 evidence provenance 下定位真正改善最终任务的步骤。

新的 `plan.md` 因此采用证据门控顺序：先隔离评测、稳定 evidence pipeline 并复现基线，再验证四类信号和干预式 step credit，再验证动作价值预测，最后才实现完整 controller 或 RL credit。V2.40.2 的 2/2 completion、0/2 整表成功与 V2.40.3 的零调用回放说明项目仍处于第一阶段；completion 和 query-plan coverage 都不能替代值正确率。若 anchor/coverage/row/cell signal 不能校准，若 step score 不能预测 counterfactual task contribution，或同动作空间下不改善任务风险–成本 Pareto，则“熵作为核心创新”应降级为诊断工具。

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
41. Houthooft, R. et al. **VIME: Variational Information Maximizing Exploration.** NeurIPS (2016); arXiv:1605.09674. https://arxiv.org/abs/1605.09674
42. Ng, A. Y., Harada, D. & Russell, S. **Policy Invariance under Reward Transformations: Theory and Application to Reward Shaping.** ICML, 278–287 (1999). https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf
43. Nath, A. & Krishnaswamy, N. **ECHO: Learning Epistemically Adaptive Language Agents with Turn-Level Credit.** arXiv:2606.29745 (2026). https://arxiv.org/abs/2606.29745
44. Tao, L. et al. **TRACE: Turn-level Reward Assignment via Credit Estimation for Long-Horizon Agents.** arXiv:2607.13988 (2026). https://arxiv.org/abs/2607.13988
45. Zhu, Q., Wu, J. & Wang, L. **LOTAPO: Leave-One-Turn Attribution for Self-Generated Process Rewards in Multi-Turn Search Reasoning.** arXiv:2607.13501 (2026). https://arxiv.org/abs/2607.13501
46. Xu, K. et al. **STAMP: Provenance-Guided Credit Assignment for Deep Search Agents.** arXiv:2607.11172 (2026). https://arxiv.org/abs/2607.11172
47. Li, M. et al. **RICE-PO: Turning Retrieval Interactions into Credit Signals for Reasoning Agents.** arXiv:2605.26352 (2026). https://arxiv.org/abs/2605.26352
48. Hu, S. et al. **Self-Induced Outcome Potential: Turn-Level Credit Assignment for Agents without Verifiers.** arXiv:2605.04984 (2026). https://arxiv.org/abs/2605.04984
49. Xie, Z. et al. **ACPO: Adaptive Credit Policy Optimization via Fine-Grained Surrogate Entropy.** arXiv:2607.03126 (2026). https://arxiv.org/abs/2607.03126
50. Meng, R. **Policy-Conditioned Counterfactual Credit for Verifiable Reinforcement Learning of Long-Horizon Language Agents.** arXiv:2606.05263 (2026). https://arxiv.org/abs/2606.05263
51. Meng, Z. & Chen, K. **CRAFT: Counterfactual Credit Assignment from Free Sibling Rollouts for Self-Distilled Agentic Reinforcement Learning.** arXiv:2606.29476 (2026). https://arxiv.org/abs/2606.29476
52. Wang, H. et al. **BiPACE: Bisimulation-Guided Policy Optimization with Action Counterfactual Estimation for LLM Agents.** arXiv:2606.25556 (2026). https://arxiv.org/abs/2606.25556
53. Tian, Y. et al. **PBSD: Privileged Bayesian Self-Distillation for Long-Horizon Credit Assignment.** arXiv:2606.09348 (2026). https://arxiv.org/abs/2606.09348
54. Liu, D. et al. **PiCA: Pivot-Based Credit Assignment for Search Agentic Reinforcement Learning.** arXiv:2605.09287 (2026). https://arxiv.org/abs/2605.09287
55. Arjona-Medina, J. A. et al. **RUDDER: Return Decomposition for Delayed Rewards.** NeurIPS (2019); arXiv:1806.07857. https://arxiv.org/abs/1806.07857
56. Foerster, J. et al. **Counterfactual Multi-Agent Policy Gradients.** AAAI (2018); arXiv:1705.08926. https://arxiv.org/abs/1705.08926
57. Harutyunyan, A. et al. **Hindsight Credit Assignment.** NeurIPS (2019); arXiv:1912.02503. https://arxiv.org/abs/1912.02503
58. Cheng, X. et al. **Beyond Trajectory-Level Attribution: Graph-Based Credit Assignment for Agentic Reinforcement Learning.** arXiv:2605.26684 (2026). https://arxiv.org/abs/2605.26684
59. Tang, W. et al. **Rewarding Beliefs, Not Actions: Consistency-Guided Credit Assignment for Long-Horizon Agents.** arXiv:2605.20061 (2026). https://arxiv.org/abs/2605.20061
60. Zhang, E. et al. **OASES: Outcome-Aligned Search-Evaluation Co-Training for Agentic Search.** arXiv:2604.03675 (2026). https://arxiv.org/abs/2604.03675
61. Wei, Z. et al. **AMR-SD: Asymmetric Meta-Reflective Self-Distillation for Token-Level Credit Assignment.** arXiv:2605.18529 (2026). https://arxiv.org/abs/2605.18529
62. Ye, Z. et al. **Not All Tokens See Equally: Perception-Grounded Policy Optimization for Large Vision-Language Models.** arXiv:2604.01840 (2026). https://arxiv.org/abs/2604.01840
63. He, Y. et al. **Where Hindsight Credit Can Reside: A Signed-Capacity View of Token Updates in RLVR.** arXiv:2604.11056 (2026). https://arxiv.org/abs/2604.11056
64. Wang, J. et al. **Harnessing Uncertainty: Entropy-Modulated Policy Gradients for Long-Horizon LLM Agents.** arXiv:2509.09265 (2025). https://arxiv.org/abs/2509.09265
65. Shapley, L. S. **A Value for n-Person Games.** In *Contributions to the Theory of Games II*, 307–318 (1953). https://doi.org/10.1515/9781400881970-018
66. Kong, F. et al. **InfoPO: Information-Driven Policy Optimization for User-Centric Agents.** arXiv:2603.00656 (2026). https://arxiv.org/abs/2603.00656
67. Zhao, H. et al. **AEM: Adaptive Entropy Modulation for Multi-Turn Agentic Reinforcement Learning.** arXiv:2605.00425 (2026). https://arxiv.org/abs/2605.00425
68. Zhang, D. et al. **SELAUR: Self Evolving LLM Agent via Uncertainty-aware Rewards.** arXiv:2602.21158 (2026). https://arxiv.org/abs/2602.21158
69. Zhao, Q. et al. **STRIDE: Strategic Trajectory Reasoning via Discriminative Estimation for Verifiable Reinforcement Learning.** arXiv:2606.15866 (2026). https://arxiv.org/abs/2606.15866
70. Wang, X. et al. **APPO: Agentic Procedural Policy Optimization.** arXiv:2606.12384 (2026). https://arxiv.org/abs/2606.12384
71. Guo, W. et al. **Agent Reinforcement Learning via Pivotal-Aware Self-Feedback Retry.** arXiv:2607.03702 (2026). https://arxiv.org/abs/2607.03702
72. Xie, H. **Forage V2: Knowledge Evolution and Transfer in Autonomous Agent Organizations.** arXiv:2604.19837 (2026). https://arxiv.org/abs/2604.19837
73. Nakajima, Y. **The Shared Discovery Paradox: How a One-Answer Rule Turns Better Information into Worse Search.** arXiv:2607.18045 (2026). https://arxiv.org/abs/2607.18045
74. Chen, D. et al. **A²TGPO: Agentic Turn-Group Policy Optimization with Adaptive Turn-level Clipping.** arXiv:2605.06200 (2026). https://arxiv.org/abs/2605.06200
75. Wang, H. et al. **T²PO: Uncertainty-Guided Exploration Control for Stable Multi-Turn Agentic Reinforcement Learning.** ICML 2026 Spotlight; arXiv:2605.02178. https://arxiv.org/abs/2605.02178
