# Entropy-DeepWide：信息熵、信息增益与 Credit Assignment 驱动 Deep-and-Wide Search 文献综述

> 检索截止：2026-07-31；项目证据更新：2026-07-31
>
> 结论强度：这是基于公开文献的 novelty audit，不是“没有任何相关工作”的证明。2026 年文献多为尚未同行评审的 arXiv 预印本，文中将预印本结果视为作者报告，而非独立复现事实。

## 摘要

“把信息熵用于搜索代理”或“给熵降大的步骤更多 credit”都不能作为本项目的核心首创主张。Semantic Entropy 已将自由文本答案聚类为语义等价类并用熵预测错误；FLARE、Self-RAG、TASR 和 Know Before You Fetch 已用置信或校准概率控制检索与停止；CuriosiTree、Conformal Information Pursuit 和 ECR 已用期望信息增益或期望熵下降选择下一动作；InfoReasoner、IGPO、IG-Search、SIGHT、TEPO 和 IGRPO 已把信息量用于搜索代理训练或 rollout 分配。更直接地，ECHO 已把后验收缩称为 epistemic credit，TRACE、LOTAPO、STAMP、RICE-PO 等分别用真值答案似然、删除干预、证据 provenance 和同状态局部分支定位 turn credit。DeepWide 侧也已出现 Table-as-Search、A-MapReduce、Web2BigTable、WebSwarm 与 SearchOS，分别覆盖持久表格状态、横向并行、递归 deep/wide 路由和 coverage-aware 调度。Forage V2 又直接研究完成边界未知时的 denominator blindness，Shared Discovery Paradox 则说明更准确的共享 posterior 若被压成重复的单一动作，可能降低群体发现覆盖。[72,73] 2026 年 7 月下旬的 AREX、Harness-G 与 Baikal 又分别覆盖“已验证约束/未解决约束”驱动的递归跟进、检索等价坍缩与非近视 credit、semantic-region bandit coverage。[76,81,82]

截至 2026-07-31，信息熵作为统一优化目标还有一个更直接的理论反例。Search as Computation Allocation 证明，mutual information 只有在终端决策为概率分布且使用 log loss 时才等于 myopic value of computation；若终端目标是零一损失或 simple regret，动作价值是 posterior best-decision improvement，也就是 knowledge-gradient 型 VOC。该文构造的有限问题中，按信息增益选中的 computation，其 VOC 可以低于最优 computation 的任意给定比例。[83] 因而，本项目更准确的核心是**以四层 DeepWide 终端损失定义 value of computation**。信息熵只在 log-loss 子问题中充当精确短视价值，在一般损失下充当诊断或代理；只有当损失有界且通过目标变量决定时，低 mutual information 才给出 myopic VOC 的单侧上界。它不能单独决定跨动作排序或 credit。

在本次检索范围内，仍有一个可验证、也可被否证的候选缺口：尚未找到工作在 DeepWide 表格任务中同时校准隐藏 anchor、未见结果质量、行资格和格值，并把这四类风险变化与结果对齐的同状态反事实 credit 联合验证。有限候选集上的低 Shannon 熵不代表开放集合完整，甚至可能是在错误 anchor 上过度确信。因此，本综述建议将创新假设收窄为：用校准的四层信念估计任务风险变化；用 evidence-set equivalence 和来源依赖图防止同义查询、镜像页面或同源记录制造虚假宽度；再通过同状态干预和 provenance 判断风险变化是否由该步骤造成、是否支持最终任务。信息量在这里是 epistemic signal，而不是自动成立的 causal credit。V2.42.11 已实现 label-blind 的 entropy/VOC 决策 kernel 和真实 action-to-state runtime bridge，V2.42.12/13 又冻结了 selected-component publisher 与恢复协议；V2.42.16–18 已冻结 paired dev64 package gate、post-gate capacity successor 和 single-owner exact-220 executor，V2.42.19/20 则冻结了污染与来源依赖的 post-terminal audit。所有执行链仍在等待上游，没有运行 paired forward、容量探针、mapping/evaluator 或第二个全集。因此这些实现不能说明该方法有效或提高分数。

V2.42.21 进一步把 CGDP 最接近本项目的 predicate belief 与 programmatic exhaustion 实现为独立、build-only 的 label-blind 强基线。该基线只接收 predicate/action/evidence/source-class 的 SHA-256 投影；`answer_ready` 只表示 required predicates 都有 clean page-backed support，并不表示任务成功或开放集合完整；同一 evidence class 一旦既 clean 又 contradicted 就 fail closed。它没有概率校准、四层开放世界状态、entropy/VOC、来源独立性估计、runtime 接入或 benchmark 权限。因此它只补齐未来对照，不构成四层方法有效、提分或 SOTA 的证据。

2026 年 7 月 29–31 日的增量文献进一步排除了三个宽泛主张。WebSwarm 式递归委派不能推出“更多 agent 更好”：Two Calls Beat Five Agents 与 SKIMIX 都报告了 task-dependent、非单调的 multi-agent scaling，MANTA 又把通信拓扑本身作为推理时动作。[91–93] 相关性或不确定性 score 也不能单独决定工具数；CAM-DF 直接学习“现在停止”与“最佳继续”的 payoff gap，并把异质成本纳入决策。[90] 大的模型分布变化更不自动代表 task credit。CSCR 在相反 outcome 条件下观察到大量同向 token shift，并将其解释为 counterfactual sensitivity 而非可靠的 answer-aligned direction；OVCSD 则要求 state-aligned divergence 和 outcome-verified continuation。[97,98]

同日公开的进一步结果把实验对照收得更紧。Sample More, Reflect Less 在可核验数学题和 1.5B–7B 本地模型上，以每种方法的实际生成 token 匹配重复采样曲线；其结果不支持把该域中的反思、辩论或自选候选收益归因于机制本身，但作者明确不外推到 frontier 模型和开放式任务。[104] BeyondUncertainty 说明口头置信可以有排序价值却仍失校准，而且省检索 passage 不等于省总 token，因为额外 probe 本身有成本。[105] SVR 又表明自验证停止可能保存正确的中间答案，但错误提前停止仍是主要限制。[106] One Human, N Agents 则在受限审计模型与小规模 trace replay 中发现，跨 agent 错误相关性更多由共享题目难度解释，而非简单由模型谱系解释。[107] 这些论文不能直接预测 DeepWideBench 分数，却共同要求任何 swarm、停止或 uncertainty controller 同时报告等预算简单基线、控制分支实际触发率、probe 全成本、错误提前停止和相关失败。

7 月 30 日批次又排除了“用熵决定 width”和“熵变化自动给正 credit”两种表述。SciDataSailor 在科学数据探索的 MCTS 数据合成中，用候选动作 prior entropy 与 step token entropy 动态决定 branching width，高不确定状态展开更多子节点；因此 entropy-adaptive width 已有直接系统近邻。[110] CRPO 比较普通学生上下文与带特权反馈的自教师上下文，按 predictive-entropy difference 把位置分成 reflective-exploration 正对和 exposure-bias 负对，训练方向可以朝向或远离教师；它说明大的 entropy drop 可能恰是路径收敛的负信号。[111] PCD 在多模态蒸馏中只在下游失败与 teacher–student disagreement 两个 witness 同时出现时加强感知 credit，说明层级风险 credit 需要目标层的可纠正性证据，而不是仅凭终局失败或局部不确定性。[112] $\beta$-OPSD 则用 return-to-go 把未来 student–target mismatch 回传给早期 token，形成另一条非短视 credit 基线。[113] 这些论文未在 DeepWideBench 上联合建模四层风险，但使本项目的证明责任更明确：熵只能调节候选动作或 credit 的强度，更新方向必须由 outcome、同状态 continuation 或层级 witness 约束。

本轮对 WebSwarm 邻域的增量核验又分离出训练、上下文和评测三个接口。MAPD 把离线多智能体探索压成带 reasoning plan、抽取式 grounding facts、partial findings 和 answer verification 的结构化协议，再以 outcome RL 约束 privileged distillation；其 task type、ground truth 和 repair diagnosis 只用于离线合成，不能成为 label-blind runtime 路由信号。[121] ACM 让 agent 自主把原始消息外置并按 summary ID 回查，但其 action-timing teacher 同样读取 reference answer，因此本项目只能借用可逆 offload 与 provenance 接口，不能复制其 privileged runtime decision。[122] Silent Failures 则区分 phantom grounding、wrong-evidence-right-answer、over-retrieval laundering 与 provenance hallucination，说明正确答案和大量检索都不能证明步骤获得正 credit。[123] 这三项不产生本项目分数，却要求未来 WebSwarm/no-entropy baseline 与 entropy controller 共用同一 active-evidence ledger、轨迹审计和 failure-as-zero 终局口径。

最后一轮增量核验把四种容易混称为 credit 的机制分开。AdaKP 用候选提示引起的 next-token entropy reduction 选择由 gold solution 抽取的 knowledge points，并在训练前用 leave-one-out answer accuracy 检验排序；它支持“熵差可作便宜 proxy”，但不支持“熵差天然等于 task contribution”。[130] TAPO 用 action-conditioned next-observation prediction 增强 transition representation，MARS-RA 则用多模态模型生成 agent 间 pairwise contribution comparisons，再做 rank aggregation 和 potential shaping。[131,132] 前者是 dynamics auxiliary objective，后者是 agent-level relative allocation；二者都不能替代同一 DeepWide step 的固定 continuation 干预。Self-speculating agent 又预测下一只读工具调用以隐藏等待时间，但论文的离线评测只执行真实 agent call，Hit@1 也不是实际 wall-clock 或质量收益。[133] 因而，未来实验需分别报告 entropy proxy validity、transition prediction、agent-level rank credit 与 read-only latency speculation，不能把它们合并成 OWIC 的单一优势。

2026 年 7 月 31 日的最后一组全文核验又补上九个直接约束。[134–142] *BM25 Wins at Scale* 在 28 个嵌套语料规模上观察到约 10M corpus tokens 后的 lexical crossover；更关键的同一 150 题 full-scale mechanism control 中，raw file agent 为 36.9/895K tokens per query，Agent+BM25 为 69.4/101K。这个受控结果支持“global ranking 后再 agent refinement”，不支持把该分数外推为 DeepWideBench 成绩。[134] MagicSelector 的所谓 counterfactual reward 是 decomposition 前后 tool NDCG 与 target-tool completeness 的增益，依赖 gold target-tool set；它是 privileged decomposition proxy，不是终局任务 credit。[135] TSDS 则联合校准 thought convergence 与 cloud deferral，并明确把 finite-sample guarantee 建立在 calibration/test i.i.d. 上；因此停止与升级不能各自单独调阈值。[136]

其余六项把覆盖、干预与并发边界补齐。多智能体扩展研究的 1/3/5/7-agent 配置在 5-agent 中等复杂度达到峰值，7-agent 受 timeout、错误传播与低一致性影响；Bayesian MAS monitor 又明确要求先校准 log-prob，并承认静态 DAG 不表示完整时序、反馈或反复修订。[137,138] n-Clue 的最强展示配置可在 81.1% 查询找到 gold，却只有 35.8% 达成 complete-first，说明 candidate hit 不能替代合取证据完整性。[139] Auto Research 在 inner search 后冻结候选，再用 outer holdout 验证 intervention transfer；Conformal Cascade 给有限答案集提供 finite-sample defer baseline，但开放生成仍需 answer clustering；MemHarness 则要求历史经验按当前状态重构而非机械 replay。[140–142] 这些近邻仍未联合解决 DeepWide 四层开放世界风险，但已经占据了 global retrieval、joint stop/defer calibration、intervention transfer、finite-set defer、runtime uncertainty propagation 和 state-conditioned memory 的宽泛主张。

对 WebSwarm 邻域的补漏全文核验又加入四个必须控制的机制。[143–146] DivInit 发现并行 rollout 的首轮 query 会发生 anchor collapse，并在五个 open-weight 模型、八个 benchmark 的匹配计算设置中报告 multi-hop QA 平均提高 5–7 点；其主要指标是 pass@k，不能直接替代 DeepWide 的冻结单答案/整表评测。[143] Dr-DCI 将 retrieval 改成动态扩展本地 workspace 的动作，再在已拉取文档上做跨文档搜索和验证；其 BrowseComp-Plus `71.2%`、context reset 后 `73.3%` 及 20M Wiki-18 六基准平均 `63.0` 均是该论文设置内结果。[144] 这两项要求 WebSwarm baseline 同时加入首轮 query diversity/evidence-overlap 诊断，以及 `global retrieval → bounded workspace → local verification` 强对照。

DRNOISE 和 FA-SD 分别收紧可靠性与训练主张。DRNOISE 的 100 个合成 paired tasks 中，一篇直接给出错误答案的普通文档使强 clean agent 准确率下降 66–88 个百分点；oracle full-context 将 GPT-5.4 的 conditional deference 从 retrieval-agent 的 `68/81` 降到 `8/100`，支持“过早停止和未完成证据链”是主要机制，但作者明确指出合成语料不能覆盖 live web 的完整分布。[145] FA-SD 则发现成功 rollout 反馈可让 self-teacher 更强，却可能形成与题目无关的搜索模板、稀疏 KL 信号和 prompt/model inconsistency；fixed-reference 或 EMA teacher 能稳定训练，但没有消除 transfer 问题。[146] 因而，四层风险 controller 必须在矛盾证据下测 complete-route reconciliation，credit-training 还要报告 query/trajectory 对输入的条件依赖、模板重复、有效 distillation-sample ratio 和 teacher drift，不能把表面轨迹差异或 teacher advantage 当成已内化 credit。

最后一次日期窗补漏又找到两个会改变实验合同、但不改变核心缺口判断的近邻。[147,148] SwarmResearch 在开放式代码优化中让 Shepherd 按搜索深度动态选择父分支和并行 Search Agents。其 60-iteration、5-task 固定伸缩对照使用异构 orchestrator/worker，动态伸缩在 4/5 题更优；另一个 15-task 主比较则每题只运行一次。[147] 这使“随深度动态调 width”也不能作为新颖点，却不能外推为网页表格搜索收益。SimpleWikiSearch 则把知识快照、清洗与切块、检索后端、tool schema、observation format 和提交规则都定义为可执行环境合同。[148] 因而，未来全集比较除固定模型和调用预算外，还必须冻结搜索环境指纹；live-web 后端、离线 snapshot 或 tool contract 发生变化时，应视为新的实验条件而非 controller 提升。

最后的引用邻域核验又找到三个直接对照。[149–151] HiMPO 在同一个 compressed pre-write state 下比较旧、新 memory 对 target outcome 的可恢复信息，再用 outcome-conditioned hindsight relevance 抑制 tool/reasoning error 造成的 blame leakage；它已经占据“同状态 memory update credit”，但依赖可靠 target outcome。[149] WikiLoop 用冻结 Navigator 在同一个 pre-edit Wiki 上比较候选编辑前后的 downstream utility，并对 unrelated queries 的负效用、编辑成本和结构退化施加惩罚。[150] 这两篇共同说明，局部信息变化只有在同起点、固定消费者、结果方向与副作用审计下才接近 credit。VecTree-RAG 则把检索分为 corpus-level vector/sparse routing、source-verified document-tree navigation 和 page close reading，补上 Dr-DCI 之外的 structure-aware locate-then-read 基线；其固定科学文献库结果和成本不能横比 live-web DeepWide。[151]

2026-07-31 18:32 UTC 的定向补漏检索发现 SearchSwarm，此前 156 篇清单未收录该工作。[157] 其主代理把 `call_sub_agent` 视为主动上下文管理：子代理在独立 64K context 中执行，只把带引用的压缩报告送回 128K 主 context；成功 harness 轨迹再以 environment-masked next-token SFT 内化何时委派、如何写 brief 和如何整合结果。论文在 200 题 BrowseComp 子集上的 harness 对照为原框架 `47.7`、只暴露 tool schema `50.0`、完整 harness `57.7`，但没有把委派、报告压缩和总计算量分别匹配；主表的外部基线又来自各自技术报告或 model card。它因此占据“训练 delegation intelligence”和“子代理作为 context-management tool”的宽泛主张，却不估计开放集合 unseen mass、四层任务风险或 step credit。后续强对照必须拆成 no-delegation、tool-schema-only、full harness、WebSwarm 和 four-layer VOC，并同时报告主/子上下文 token、摘要遗漏、引用保留、总工具调用与墙钟。

19:03 UTC 的最新分类窗口与 157 篇清单按 arXiv ID 去重后，新增 ConMem。[158] 该文将工业巡检日志分成 evidence units，用训练期下游诊断 utility 的边际变化近似 Shapley contribution，再按 contribution 保留或淘汰记忆。它已经覆盖“按估计贡献选择记忆证据”和“Shapley-style memory valuation”的宽泛主张，却使用固定日志、已知查询分布与后续确认异常，不处理 live-web 动作、开放集合 unseen mass、四层 DeepWide 风险或 label-blind 在线路由。ConMem 因而是 memory-credit 强基线，不是四层开放世界 credit 的替代。WebSwarm 与 SearchSwarm 经官方 arXiv API 复核仍为 v1。

20:16 UTC 的 termination/utility 定向回查又补上两个遗漏的强近邻。[159,160] Choubey 等人的 ACL Industry 2026 系统在执行前为每个 research step 写明 evidence-sufficiency criteria，并用 Plan DAG 限制依赖与上下文流。移除显式 agent-termination criteria 后，作者在 10 个企业 sales-enablement 场景上报告 HAA 从 82.09 降至 73.67、coverage 从 4.31 降至 4.02，public/internal search calls 从 `327/90` 降至 `224/64`；这些数字只说明该论文设置中的提前停止现象，不能外推到 DeepWideBench。[159] ScaffoldAgent 则把 retrieval、outline structure 与 trial-writing quality 合成复合 utility，用于节点选择、outline 扩张/收缩/修订和边际收益停止，但实现仍设置最多 20 轮。[160] 因而，显式证据充分性停止、下游 utility 驱动结构调整和 marginal-utility stopping 均不能作为宽泛首创。仍待检验的差异是这些 proxy 能否被四层校准的 DeepWide 终端风险在同预算、同动作菜单下稳定超越。

21:44 UTC 的来源依赖定向检索又找到两个会直接约束“有效宽度”的近邻。[163,164] CACD 在固定 RAG 索引构建中用 cross-encoder、attention-entropy 派生的 New Information Score 和多候选投票区分真正重复与仅共享主题的 chunk；作者只在 SQuAD 1.1 的 18 个 chunking 配置上验证，并明确把阈值校准、被删除 chunk 的残余信息损失和 cross-encoder 质量列为限制。[163] 它是内容去重强基线，但不表示跨域页面具有独立来源。*The Cost of Consensus* 则在简化的分布式网格搜索中研究 belief fusion：团队可能收敛到一致但错误的 belief，而普通 consensus/Jensen–Shannon 指标无法识别；其 entropy-delta communication gate 属于受控仿真结果，运动策略、观测模型和网络均比 live-web agent 简化。[164] 因而，本项目不能把 attention entropy 去重、entropy-gated 通信或“更多一致 sibling”当作新颖性或正确性证据。强对照必须把文本重复、来源谱系、共享证据、belief alignment 与终局任务正确性分开。

22:01 UTC 的最终补漏检索发现八项此前未进入 164 篇清单、且会改变实验合同的工作。[165–172] CGDP 已把 agentic search 写成带终局 reward 与动作成本的 POMDP，并用 persistent predicate belief 与 programmatic exhaustion gate 控制上下文和停止；因此“首次以 belief-state/POMDP 描述搜索”也不能作为贡献。[165] GDCR/SAPO 用训练期答案节点和 entity–relation graph 的最短路进展给新检索、新引用实体分 step credit；SlimSearcher 以严格正确性 gate 乘相对 tool/token efficiency；SAAS 用 search-enabled/search-disabled rollouts 估计 knowledge/search boundary。[166–168] 三者分别占据 answer-grounded graph credit、outcome-gated efficiency credit 与 search-boundary regularization，但都依赖已知答案、正确性判定或封闭 QA，不等于 label-blind live-web terminal contribution。

并行和评测两端也出现更强对照。AggAgent 把已完成的并行轨迹当作可查询环境，按需读取 solution、关键词命中和原始 step，而不是只投票或压缩摘要；这说明 width 的收益还取决于聚合器，未来 agent-count 曲线必须固定 aggregation rule 并加入 full-trajectory agentic aggregation。[169] LiveBrowseComp 用近 90 天事实削弱 parametric-memory verification，DeepWeb-Bench 则把 8×8 表格的 retrieval、derivation、reasoning、calibration 分开，并记录四级来源 provenance 与跨源一致性。[170,171] R²-Searcher 又显式训练 sufficient/insufficient/mismatched retrieval reflection 和 retrieval–reasoning boundary。[172] 这些工作不联合估计 DeepWide 的 anchor、unseen mass、row eligibility 和 cell value，也没有给出同状态 outcome-verified credit；但它们要求本项目把真实检索、边界判断、跨源调和、推导错误、聚合器收益和最终任务价值分别评测。

22:25 UTC 再次查询官方 arXiv Atom 的 `agentic search`、`deep research`、`multi-agent search`、`information gain` 与 `credit assignment` 日期窗，并按 arXiv ID 与 172 篇清单去重。WebSwarm、SearchSwarm、CGDP、GDCR/SAPO、SlimSearcher、AggAgent、LiveBrowseComp、DeepWeb-Bench 与 R²-Searcher 仍为 v1，SAAS 仍为 v3；本轮没有发现会改变 novelty verdict 或实验合同、且尚未收录的新直接近邻。这个负结果不证明检索穷尽，只说明无需为增加条目数重复收录或把摘要层面的相邻工作冒充新机制。

## 1. 范围、问题与检索方法

### 1.1 研究问题

本综述回答五个问题：

1. DeepWide 搜索系统已经解决了哪些状态管理、深宽路由和覆盖问题？
2. 熵、信息增益与不确定性已经怎样用于 LLM/RAG/搜索代理？
3. 哪些工作与拟议创新直接重叠，哪些缺口仍可辩护？
4. 信息论视角怎样转化为可校准、可比较、可否证的研究计划？
5. 信息增益何时可以作为 credit，何时只是在奖励新奇、噪声或错误自信？

### 1.2 检索过程

主体检索在 2026-07-19 至 2026-07-21 进行，并持续做提交日期增量核验至 2026-07-31，采用三层策略：

- 精确追踪用户给出的 WebSwarm（arXiv:2607.08662），并沿其 related work 核对 DeepWideSearch、Table-as-Search、A-MapReduce、Web2BigTable、SearchOS、TreeSeeker 等系统。
- 在 arXiv API 以 `entropy`、`information gain`、`expected entropy reduction`、`retrieval`、`search agent`、`open set`、`unseen mass`、`capture-recapture` 等组合查询，各抓取按提交日期排序的前 100 条，共 300 条记录、去重后 297 条，再按标题与摘要筛选直接相关工作。
- 针对 credit assignment 追加检索 `epistemic credit`、`entropy reduction + credit assignment`、`information gain + process/turn/step reward`、`causal/counterfactual credit + language agent`，并反向核对 ECHO、TRACE、LOTAPO、STAMP、RICE-PO、CVT-RL、SIOP 等论文的 related work；关键结论以 PDF 公式与 limitation 原文为准。
- 2026-07-20 再检索 `credit assignment AND (information gain OR entropy) AND agent/search` 与 `open world AND uncertainty AND agent/search`，核对新增近邻 PivoARL、InfoPO、AEM、SELAUR、STRIDE 与 APPO；使用 arXiv API 逐条验证标题、作者、版本和摘要。
- 2026-07-21 补充检索 denominator blindness、shared discovery、turn-group information gain 和 uncertainty-guided exploration，核对 Forage V2、Shared Discovery Paradox、A²TGPO 与 T²PO 的 arXiv 元数据与原文。
- 2026-07-21 做提交日期增量检索，并读取 Forage V2、Shared Discovery Paradox 与 A²TGPO 的 PDF。该轮新增了未知 denominator、belief–coverage 分离、gold-conditioned turn IG 和 uncertainty-guided resampling 的直接近邻。[72–75] 截至该范围仍未找到把 DeepWide 的 anchor、未见质量、行资格、单元格值四层同时概率化并用于 task-risk control/credit 的工作，但这只是限定语料与日期下的缺口判断。
- 2026-07-31 对 2026-07-21 至 07-31 的 arXiv 新增记录做增量筛选，并逐页核对 WebSwarm、AREX、Delegation Intelligence、EviBack、RARG、Filesystem-Based Memory、Harness-G、Baikal、Search as Computation Allocation、SearchArt、CAST、AttriMem、MisKnow-Agent 与 FinanceHarness 的 PDF，而非只引用摘要。[5,76–88] 这一轮把 novelty 边界进一步收窄到四层风险的校准与联合验证：递归 follow-up、语义区域覆盖、同义检索去重、结构化非近视 credit、state-value credit 和终端损失下的 metareasoning 都已有直接近邻。
- 2026-07-31 再对 07-28 至 07-31 的 `cs.AI/cs.CL/cs.IR/cs.LG` 记录做 500 条增量召回，并以 web/research/search、swarm/delegation、coverage/evidence、credit/VOC/uncertainty 词族筛选。正文或一手 arXiv 元数据核验了 HiEviDR-Bench、CAM-DF、Two Calls Beat Five Agents、SKIMIX、MANTA、SkillRise、GRSD、TTEL、OVCSD、CSCR、LEDGERMIND、LayerRAG-Bench、Thinking Under Uncertainty、AskChem 与 Selective Credibility-Limited Belief Update。[89–103] `DeepResearch Agent System`（arXiv:2607.27562）虽然声称多项 SOTA 和大幅百分比改进，但正文是 software copyright R&D document，未提供足以复核这些数字的同协议实验链；本综述将其列为已筛选但不承载结论的低可信记录。
- 2026-07-31 对当日最新批次再做题名/摘要筛选，并读取 Sample More, Reflect Less、Beyond Self-Knowledge、SVR、One Human, N Agents、local computer-use inference scaling 与 HYSET 的 PDF 原文。[104–109] 该轮不新增“统一方法”主张，而是增加六个实验约束：等生成 token 的独立采样曲线、probe 输入/输出 token 全计费、自适应路径触发率、premature-stop error、相关失败下的有效独立分支数，以及组合动作的集合级边际价值。数学推理、受控 RAG、agent 审计、computer-use 与 tool retrieval 的结果均只作机制和失败模式近邻，不作 DeepWideBench 横向分数比较。
- 2026-07-31 09:06 UTC 再用 arXiv Atom API 对 07-29 至 07-31 的 `deep research`、`web/deep search agent`、`information gain/entropy/uncertainty` 与 `credit assignment/process reward/turn-level` 做四组日期限定查询，并核对 SciDataSailor、CRPO、PCD、$\beta$-OPSD 与 EMBL AI Librarian 的元数据和 PDF。[110–114] 前四项分别占据 entropy-guided branching、entropy-sign contrast、双 witness 层级 credit 与 return-to-go distillation credit；Librarian 则提供固定七个互补 query、分层去重和 `8 search / 12 fetch` worker pool 的工程对照。它们使用科学数据探索、深搜训练、多模态蒸馏、数学推理或生命科学检索设置，不构成 DeepWideBench 提升证据。
- 2026-07-31 10:02 UTC 以 arXiv Atom API 对 `deep research`、`agentic/web search`、`multi-agent search`、`information gain agent`、`credit assignment agent`、`recursive search` 和 `information seeking` 做八组增量查询，并与既有 116 篇按 arXiv ID 去重。新增精读 Bridge Evidence、CIGPO 与 CHILL-Harness 三篇 PDF，并以一手摘要核验 Think Big, Search Small。[117–120] 这轮不支持新的首创主张，反而新增三项强对照：固定前缀后删除证据并重跑 suffix 的轨迹效用、gold-answer likelihood 的 contextual IG credit，以及干预相对 workflow advantage；层级搜索还需分开扫描 delegation 与 execution 的模型容量。只有前三篇计入 PDF 精读，第四篇的具体数字仍以摘要证据为限。
- 2026-07-31 10:29 UTC 对 07-21 至 07-31 的 `deep research`、`web/agentic search`、`swarm`、`multi-agent`、`delegation` 与 `research/search agent` 做两组更宽的 arXiv Atom 日期查询。与现有 120 篇按 ID 去重后，全文核验 MAPD、ACM 与 Silent Failures 三篇，并以一手摘要筛选 OrchBench、HalluProp、$\Sigma$-Mem、SafeFlow、Context Assembly 与 AgentRadio。[121–129] PDF 精读仍限定为三篇。摘要级条目只用于提出 orchestration plan、传播风险、可靠性记忆和异步通信的对照，不承载数值性主结论。
- 2026-07-31 11:02 UTC 对 07-21 至 07-31 的 agentic search、recursive/parallel search、information gain、entropy、credit assignment 与 process reward 做三组日期限定查询，并对 07-30 至 07-31 的 `cs.AI/cs.CL/cs.IR/cs.LG/cs.MA` 记录追加 500 条召回。与既有 129 篇按 arXiv ID 去重后，全文核验 AdaKP 与 Self-Speculating Agent，以一手摘要核验 TAPO 与 MARS-RA。[130–133] `DeepResearch Agent System` 仍因缺乏可复核的同协议实验链不承载结论，`Hidden APIs` 的 forked-futures 结果面向内部表示接口而非外显搜索动作，也不进入核心矩阵。新增条目只约束 proxy、transition、团队 credit 和延迟实验，不构成本项目质量结果。
- 2026-07-31 11:55 UTC 对最后一批检索结果按 arXiv ID 与版本逐条复核，并全文读取 BM25 scaling、MagicSelector、TSDS、多智能体扩展、Bayesian uncertainty monitor、n-Clue、Auto Research、Conformal Cascade 与 MemHarness。[134–142] 其中 BM25 scaling、MagicSelector、TSDS、MAS scaling 与 Bayesian monitor 的结论来自正文公式、表格或 limitation；n-Clue、Auto Research、Conformal Cascade 与 MemHarness 的主要边界同时由一手摘要和正文定位核对。新增数字只解释各论文内部的 matched control，均不作为 DeepWideBench 横向分数或本项目提升证据。
- 2026-07-31 12:48 UTC 对 WebSwarm 相邻遗漏项做二次去重召回并全文读取 DivInit、Dr-DCI、DRNOISE 与 FA-SD。[143–146] 该轮分别补上首轮 query anchor collapse、retriever-steered dynamic workspace、误导直接证据下的 verification inertia，以及成功轨迹 self-distillation 的 decoding collapse。所有数字均由论文表格或 limitation 定位核对，只用于冻结对照和失败模式，不作为当前项目分数。
- 2026-07-31 12:59 UTC 对 `deep research`、`agentic search`、`web search agent`、`multi-agent search`、`swarm search` 与 `deep-and-wide` 做全月日期窗去重检索，并全文核验 SwarmResearch、SimpleWikiSearch 与 Agent Harness Distillation（arXiv:2607.28147）三篇。[147,148] 前两篇分别补上 depth-varying parallelism 和可执行 search-environment contract；Agent Harness Distillation 主要研究通用 AMAS 的黑盒 harness 提取与 IP 风险，不直接约束 DeepWide 检索或四层 credit，故筛选后不纳入核心清单。本轮 PDF 精读限定为三篇。
- 2026-07-31 13:46 UTC 对 07-28 至 07-31 的 967 条 arXiv 记录及全月按日期排序的前 2,000 条记录做去重筛选，再沿 WebSwarm/SwarmResearch 的引用邻域全文核验 HiMPO、WikiLoop、VecTree-RAG、AGAO、AlloBench、DREvo 与 Living-Harness。[149–155] 前三篇分别补上同状态 memory-write credit、带 unrelated-query guard 的 downstream edit utility 和分层结构检索。AGAO 仅有每套 8 题、每题一次的描述性 pilot；AlloBench 研究可复用工具构建投资；DREvo/Living-Harness 依赖跨题 evaluator feedback 做 harness 自演化，均只保留筛选记录而不进入核心矩阵。本轮也复核 WebSwarm 公开主分支，最新 commit 仍为 2026-07-18 的 `40c9aaca…5717`。
- 2026-07-31 14:39 UTC 对同一日期窗做更窄的 `credit assignment / evidence retrieval / reflective memory / calibrated agent audit` 二次召回，并阅读全文复核 PCD、GRSD、AskChem、EMBL AI Librarian 与 agent-fleet audit-budget allocation，新增 RRM。[95,102,107,112,114,156] PCD 和 audit-budget 工作进入核心 novelty 边界；前者给出 reward-only stage credit 不可识别的反例，后者给出 raw confidence 排序可差于随机的反例。GRSD、RRM、AskChem 与 Librarian 分别约束 group reflection、procedural retrieval memory、claim-level provenance 和 structured live-search evidence layer。WebSwarm 官方仓库再次核验仍为 `40c9aac…5717`，没有晚于 07-18 的公开提交。
- 2026-07-31 16:28 UTC 重新核验 WebSwarm 的 arXiv v1 元数据、全文方法/消融/limitation 与公开主分支。论文标注 `Work in progress`，DeepWideSearch 结果来自 76 题 English subset、两次随机运行均值；GLM-4.5 使用 128K context、每 agent 最多 200 action steps、`entity_collect=3` 并行路径与 2 个 experience scouts，Serper 每 query 返回 top-5，页面经 Jina Reader 获取并由同一 LLM 做目标条件摘要。[5] 同一日期窗的新增标题筛选没有发现比现有 156 篇清单更直接且证据充分的新工作，因此本轮不增加弱相关引用，只收紧 WebSwarm 的复现和同预算消融合同。
- 2026-07-31 18:32 UTC 用 `SearchSwarm / recursive delegation / multi-agent deep research / deep-wide web search` 做定向补漏并全文读取 SearchSwarm v1。[157] 该轮纠正了“156 篇已覆盖所有直接 delegation 近邻”的过强暗示：训练式主代理委派、独立子上下文和 citation-bearing report compression 已有直接工作。新增条目只改变 novelty 边界与对照合同，不产生本项目 benchmark 分数。
- 2026-07-31 19:03 UTC 再拉取 `cs.AI/cs.CL/cs.IR/cs.LG` 最新分类窗口，与 157 篇清单按 arXiv ID 去重。WebSwarm 与 SearchSwarm 的官方元数据仍为 v1；新增的 ConMem v1 进入核心 credit 矩阵。[158] 本轮读取其 Shapley 近似、priority retention、数据与限制，只把作者报告的数字作为该文内部结果，不把它们外推到 DeepWideBench。
- 2026-07-31 20:16 UTC 对 `deep research + termination/evidence sufficiency/coverage`、`web/agentic search + swarm/delegation/parallel` 与 `deep research + information/context/planning/orchestration` 做三组定向回查，全文核验 *Don't Stop Early* 和 ScaffoldAgent。[159,160] 前者的 ACL Anthology、Crossref、arXiv 元数据与 PDF 表 3 相互核对；后者的公式、utility estimators、ablation 和最多 20 轮实现设置均以 PDF 为准。两篇进入核心矩阵，因为它们直接约束停止和动态结构控制；不同任务、模型、judge 与预算下的作者报告不作 DeepWideBench 横向分数。
- 2026-07-31 21:00 UTC 重拉 `deep research` 与 `agentic web search` 的官方 arXiv Atom 最新窗口。WebSwarm、SearchSwarm 与 ScaffoldAgent 仍为 v1；`DeepResearch Agent System` 仍是缺少可复核同协议实验链的低可信记录。沿 context control 与 async search 两个缺口全文核验 AdaCoM 和 SpecHop，并以官方 arXiv 元数据复核作者、版本与日期。[161,162] 两篇只约束 context 与 latency 对照，不产生本项目分数。
- 2026-07-31 21:44 UTC 对 `multi-agent/web search`、`source/evidence dependency`、`duplicate/mirror/redundancy` 做定向增量查询，并用官方 arXiv Atom API 与 HTML 全文核验 CACD 和 *The Cost of Consensus*。[163,164] 前者进入固定语料内容去重基线，后者进入 entropy-gated belief communication 与错误共识压力测试；二者均不承载 DeepWideBench 横向分数，也不证明 live-web 来源独立性。
- 2026-07-31 22:01 UTC 对 `agentic search POMDP/belief/exhaustion`、`step-level credit graph`、`search boundary/efficiency reward`、`parallel trajectory aggregation`、`live search benchmark` 与 `cross-source deep research` 做最终定向补漏。官方 arXiv Atom 元数据与 PDF 正文核验 CGDP、GDCR/SAPO、SlimSearcher、SAAS、AggAgent、LiveBrowseComp、DeepWeb-Bench 和 R²-Searcher。[165–172] 这轮只纳入会改变 novelty 或实验合同的工作；AgentDisCo、KbSD、SwarmX 等经筛选但没有新增超出现有 dynamic outline、privileged teacher 或 serving-capacity 约束的核心机制，故不为扩大清单而纳入。
- 对经典信息论与覆盖估计文献用 Crossref/OpenAlex/DOI 核验元数据；对关键 2023–2026 论文读取 arXiv 原文而不只依赖摘要。

纳入标准是：方法直接控制检索、证据选择、工具调用、搜索树、停止或开放集合覆盖；或者直接定义 DeepWide/table-search 的系统与评测边界。排除纯推荐、视觉检索、物理导航等仅共享“entropy/search”词面但不能约束本研究设计的工作。检索记录的高密度比较版见 [.research/literature_matrix.md](.research/literature_matrix.md)。

### 1.3 证据限制

arXiv 的未来月份编号与当前时间一致，但不代表论文已经同行评审。公开检索不能证明不存在未公开、未索引或术语不同的工作。文献中的系统分数通常使用不同模型、工具、预算和子集，不能横向当作严格排行榜；本综述只在同一论文、同一骨干的受控比较中解释差值。

## 2. DeepWide 系统演进：新方法必须超过什么

DeepWideSearch 将任务分成 Deep2Wide 与 Wide2Deep：前者先从多跳线索识别隐藏核心实体，再围绕它枚举表格；后者先确定范围，再为每一行做深度属性搜索。评测同时要求 Core Entity Accuracy、Row F1、Item F1、Column F1 和整表 Success Rate，因此一个流畅的最终答案无法掩盖错误 anchor 或漏行。[1]

Table-as-Search 把搜索过程外化为表格：行是候选实体，列是约束或目标属性，已填/空单元格分别记录结果与下一步计划。这已经占据了“以表作为搜索状态”的创新位置。[2] A-MapReduce 用任务自适应 MapReduce 和经验记忆横向执行大规模检索，在其 DeepWideSearch 表中，GPT-5-mini 的 Avg@4 CE Accuracy、Column F1、Item F1、Row F1、SR 分别为 79.09、51.78、42.11、26.44、4.43。[3] Web2BigTable 则采用双层多智能体系统面向 internet-scale 大表构建。[4]

2026 年 7 月的 WebSwarm 进一步削弱了“动态深/宽切换”本身的新颖性。它在推理中渐进构造递归委派树，每个节点选择 atom、deep、wide 或 entity_collect 模式；Web-Probing 先判断相关信息在网页上集中还是分散，同质兄弟节点之间复用轨迹经验。在 DeepWideSearch-EN、同为 GLM-4.5 骨干时，WebSwarm 报告 SR 6.58、Row F1 29.64、Item F1 58.40，相对 ReAct 分别提高 2.63、9.56、11.77 个百分点。[5] 这些数字证明的是该论文设置中的受控差值，不能直接与本项目的 GPT-5.5 全量中英混合单次运行比较。

WebSwarm 的公开实现进一步限制了这种比较。2026-07-18 的公开主分支 `40c9aaca...5717` 允许 `all` 或 `en_subset`，但其公开 TaskManager 默认跳过原始 core-entity gate，改用 WideSearch 表格评估；`resume_from` 的语义是重跑并覆盖已存在任务，而不是跳过已完成任务。论文结果又使用 76 题 English subset 和两轮均值，不是完整 220 题的四轮官方协议。因此，后续复现只能移植通用的四模式委派、Web-Probing 和同父 sibling experience，必须继续使用本项目冻结的 official evaluator、exact `52/52/52/64=220`、failure-as-zero、全新目录与 no-resume 合同。任何 benchmark-specific prompt、subset 名称或 evaluator 分支不得进入 forward routing。[5]

停止与结构控制也已有比固定轮数更直接的系统。*Don't Stop Early* 先生成 coverage-driven outline 和 Plan DAG，再为每个 step 预先声明完成所需的数据点、来源、时间范围与排除条件。agent 在自己的局部依赖上下文中继续取证，直到满足这些 criteria。[159] 它没有学习概率 belief、unseen-mass posterior 或 entropy policy，但已经是一个强的 `fixed evidence-sufficiency termination` 基线。其企业消融依赖 10 个客户场景和该文的 coverage/HAA 评测，不能证明同样机制能提高表格任务的 Row F1 或整表成功率。

ScaffoldAgent 把 outline 作为 evidence-indexed tree，并定义 expansion、contraction 和 revision 三类结构动作。[160] 每次动作后的 utility 是 retrieval relevance/novelty、tree coherence/balance/redundancy 和 trial-writing support/coverage/redundancy 的加权和；节点由带探索项的规则选择，最近若干轮的平均边际 utility 小于阈值时停止。这个 utility 是多个 embedding、NLI 和 LLM-judge proxy 的组合，不是 DeepWide 官方终端损失，也没有校准开放集合遗漏。它仍构成 `composite-utility outline control` 强基线，并要求四层 VOC 证明增量来自校准的 task risk，而不是动态 outline、novelty penalty、trial writing 或更长报告。

SearchOS-V1 则把开放域信息搜寻建模为带引用的 relational schema completion，并用 Frontier Task、Evidence Graph、Coverage Map、Failure Memory 和 middleware 管理状态、覆盖与停滞。其案例明确指出“已知行的 cell coverage 达到 100%”仍可能漏掉大量应有行，因此还要独立做 row-scope audit。[6] 这正是本项目需要继承而不是重新宣称的洞见：已知单元格饱和与开放集合完整性是两个问题。

WebSwarm 的消融给出一个直接工程教训。去掉 Web-Probing 后，WideSearch 与 DeepWideSearch 的 Item F1 没有下降，但 web-tool 调用分别从 137.03 增至 239.90、从 203.73 增至 331.39；去掉 sibling experience reuse 才出现较明显的质量下降。[5] 因而，网页结构探测首先应作为成本控制与动作选择基线，不能被当作质量机制本身。我们的 semantic-region 与 evidence-equivalence 诊断也必须分别报告质量和工具成本。

WebSwarm 的复现实验需要拆成可归因的执行臂。最低集合包括 ReAct、去递归委派、全部 deep、全部 wide、去 Web-Probing、去 sibling experience 和完整 WebSwarm，并增加同一动作菜单上的四层 VOC controller。各臂须共享模型、搜索与页面工具、每 query 结果数、page-summary 策略、最大 action steps、总 input/output tokens、web-tool calls、orchestrator 成本和 wall-clock cap。Web-Probing 的主要可见收益是减少重复或错位展开，因而还要报告去重后的 query、URL、正文、source dependency 与 evidence-set coverage；sibling experience 则必须与当前题事实证据物理隔离，并单列错误经验传播率。论文自己的 `6.58/29.64/58.40` SR/Row F1/Item F1 只适用于其 English-subset、GLM-4.5 与两次运行均值，不能作为本项目 exact-220 GPT-5.6 运行的目标值或先验分数。[5]

SearchSwarm 要求把另一个常被混在“swarm 提升”里的机制拆开。[157] 其 main-distributes/sub-executes 架构只让主代理看到 brief 和最终报告，子轨迹的原始网页与中间步骤不会进入主 context；论文也将这种设计明确解释为单模型的 context management，而非必须由不同模型组成的团队。因而，对照不能只比较单 agent 与 full swarm。至少还要固定同一模型与 search/page tools，比较无委派、仅开放委派工具、完整 briefing/citation harness、带训练的委派、WebSwarm 递归路由和四层 VOC；压缩报告必须回链到原始 evidence ID，并单列 load-bearing claim 丢失率。节省主 context token 不能写成总成本下降，除非把所有子代理 token 和工具调用计入。

递归委派还扩大了可靠性边界。FORGE 构造会连续影响后续研究计划的恶意文档链；在 25 个 query 上，五篇注入文档的 Network FORGE 达到 26.4% PRISM，并出现污染从表层 framing 向事实 premise 迁移的 depth migration。在 10-query defense subset 上，把每轮 follow-up 重新绑定 root query 的 RQA 将 PRISM 从 38.5% 降到 18.3%，但没有消除污染。[115] 这些数字只属于该攻击设置，不能外推为 DeepWide 的风险率。它们要求任何 WebSwarm-style child objective 同时保留 root scope、排除条件和 active evidence provenance，并在错误/互相支持的 sibling 组合上报告 branch contamination amplification。

LLM judge 也不能只按一个总体 F1 选择。Citation Verifier 在 624 个 attribution–citation 单元上分别评估 relevance 与 factual support，共 1,248 个经人工复核的判定，其中 378 个为多 judge 分歧后人工裁决的 hard cases。GPT-5-mini 的 relevance pass-class F1 为 0.908、$\kappa=0.636$，但 factual-support 的各 judge 置信区间重叠；相近 F1 的模型仍有不同的 pass-rate drift、FPR 与 FNR。[116] 若把 judge 输出用于 controller gate 或 credit，主报告必须按维度校准并公开方向偏差，否则高 FNR 会系统性少给正确证据 credit，高 FPR 会奖励无支持证据。

SciDataSailor 让“按熵自适应分支宽度”也不再是空白。它在可执行科学数据仓库上用 MCTS 合成轨迹，先以 strategy-level proposals 生成 tool probes，再把候选 prior entropy 与当前 step token entropy 归一化，映射到 $k_{min}$ 与 $k_{max}$ 之间的动态 child 数；token entropy 不可用时退回 prior entropy。[110] 该方法服务于训练数据合成而非 DeepWide 在线表格求解，且论文没有证明 entropy width 优于同预算 terminal-loss VOC。尽管任务不同，本项目必须加入固定 width、random width、SciDataSailor-style entropy width 与四层 VOC width 四个对照，并报告实际生成的分支数和去重后 evidence-set 数。

EMBL AI Librarian 给出一个可直接借鉴、但不占 novelty 的检索工程对照。其单一 LLM 生成七个互补的 Europe PMC fielded lexical queries，search 与 full-text worker pool 分别为 8 和 12，并按 PMID、DOI、title 分层去重，最终返回带 source metadata 与原始 query 的定位证据片段。[114] 它仅做一轮检索，正文也把多跳与“证据不足时是否继续”列为限制。对 DeepWide 而言，这支持把 query diversification、document deduplication、evidence localization 与跨题吞吐并发拆开测量；并发只能作为速度设置，不能获得搜索质量 credit。

AREX 让“递归核对未解决约束”本身也不再是空白。它在内层研究循环之外增加 outer self-improvement loop，以结构化 answer/evidence/confidence 判断 accept、refine 或 restart；`update_context` 保留 verified findings、source IDs、unresolved constraints、rejected candidates 与 next plan。训练阶段又用关键步骤标注给 turn-level advantage 加 bonus。[76] 这与四层概率风险不同，但它是 constraint-wise follow-up、状态压缩和 key-step credit 的强基线。新增方法必须证明校准风险比自报 confidence 或关键步骤标注提供额外预测价值。

Harness-G 从策略—环境接口解释了“query 很多但信息不增”的另一来源：不同自然语言查询逐渐产生高度重叠的累计 evidence set，即 retrieval-equivalence collapse。它把自由查询改成有限菜单，动作是 evidence sentence、entity 或 answer，再用冻结 answer scorer 比较 frontier alternatives，并沿 entity dependency graph 把下游增益回传给使其可达的早期动作。论文在六个 QA 数据集、1.5B 与 3B 模型上报告相对 Graph-R1 的平均 F1 分别提高 10.74 与 3.98；在固定 graph、outcome reward 与训练预算下，菜单相对 free-query 的提升超过 17 F1，而去掉 SNC 在三个多跳数据集上分别下降 3.08、4.55、2.88。[81] 这些是论文设置内的结果，但足以要求本项目加入 evidence-set overlap/query-equivalence 诊断，并把 SNC 纳入 credit 强基线。

GDCR/SAPO 是另一条必须正面对照的 agentic-search credit。[166] 它在训练期为每个 QA pair 构造含答案节点的 entity–relation graph，以新检索或新引用实体到答案节点的最短路衰减值形成 step reward，再和 trajectory outcome advantage 相加。该方法避免逐步 tree sampling，但其 limitation 明确要求 definitive answer 与 answer node，不直接适用于开放式分析或无清晰终点任务；搜索引擎、索引和图构造也影响绝对结果。OWIC 因而只能主张解决不同问题：在 runtime 不读答案图的前提下，用同状态 continuation、终局官方损失与 provenance 验证某步的 signed contribution。实验必须加入 GDCR-style privileged oracle，公开 privileged-information budget，并与 label-blind deployable score 分栏。

Baikal 把 data lake 聚成 semantic regions，并把 region selection 写成有预算的 bandit。它比较 random、LLM policy、Bayesian $\epsilon$-greedy 与 Bayes-UCB，按 finding groundedness、relevance、distinctness 和 utility 更新区域价值。在每个数据湖仅 15 个 query、由 GPT-5-mini 评分的设置下，作者报告最佳配置相对最强基线提高 28% 和 36%；但消融也表明 semantic regions 加随机选择已经贡献大部分收益，且没有 LLM prior 时 $\epsilon$-greedy 的优势消失。[82] 因此 semantic-region coverage 与 UCB 都不是本项目的新颖点。合理扩展是让区域调度接受四层风险和 evidence-equivalence 输入，并用官方表格指标而非仅 LLM rubric 验证。

Search as Computation Allocation 把上述路线放进更严格的决策论边界。其 metalevel state 包含 latent environment、终端决策与损失、可执行 computation、观测 kernel、成本和停止动作。Dynamic VOC 衡量“执行该 computation 后，再最优使用剩余预算”相对立即停止可减少多少终端风险；myopic VOC 只计算一步。论文证明 mutual information 在 log loss 下与 myopic VOC 精确相等，但在 simple regret 下应使用 knowledge gradient，并给出信息增益排序可任意差的构造。[83] 这不仅是相关工作补充，而是方法修正：DeepWide 的 Row/Item/Column/SR 与失败计零不是 log loss，因此主 controller 必须估计 terminal-loss VOC，不能把 EIG/cost 当作普遍正确目标。

CGDP 给出了更贴近 agent loop 的形式化基线。[165] 它把外部 corpus 当隐藏状态、tool call 当动作、retrieved chunk 当观测，并以 success 减动作成本为目标；PBAI 再把 stop、act、observe、belief update 分成显式模块。论文的 predicate belief 最多保留六项，exhaustion gate 依赖动作相似度与观测 novelty，而非校准的任务 posterior。实验只用 GPT-4o-mini、三个 retrieval QA 域，作者也明确没有给出数学界限。因此本项目的差异不能写成“POMDP 或持久 belief”，只能检验四层概率状态、开放集合遗漏和 official terminal loss 是否比 predicate list 与 heuristic exhaustion 更可校准、更能选动作。

R²-Searcher、SAAS 与 SlimSearcher 把检索边界和成本控制推进到训练层。[167,168,172] R²-Searcher 从 query token 抽取事实元素，并在每轮把 evidence 判为 sufficient、insufficient 或 mismatched；SAAS 通过同题 search-enabled/search-disabled rollouts 学习何时调用或停止搜索；SlimSearcher 则只在答案正确后按同组最省 tool/token 的轨迹缩放 reward。它们分别构成 boundary-reflection、search-necessity 与 outcome-gated cost 三个强基线。其训练期 answer/judge 信号不得进入本项目 runtime，且“更短的正确轨迹”仍不等于某一步对开放表格终局风险具有因果贡献。

AggAgent 说明生成宽度和聚合宽度必须拆开。[169] 它保留完整并行轨迹在外部数组中，让聚合 agent 先看 final solutions，再按需搜索或读取原始区段。论文在六个 benchmark、三类模型的 `K∈{1,2,4,8}` 设置内报告相对最强聚合器的平均增益，但使用抽样子集和自己的 agent scaffold。该结果不能横比 DeepWideBench，却要求本项目在 fixed evidence-equivalence/canonical-row reducer 之外加入 voting、solution-only、summary 与 full-trajectory agentic aggregation；否则任一 swarm 增益都无法区分来自搜索 policy 还是 reducer。

SearchArt 与 CAST 又分别收紧了训练和 credit 的主张。SearchArt 用可验证 evidence graph 合成长程任务与轨迹，并组合 outcome、tool-format 和非单调 turn-budget reward训练搜索代理；它说明“可验证任务合成 + process reward + 长程 search harness”已是系统基线，但其 turn reward主要约束整条轨迹长度，不能识别某个 evidence action 的 task contribution。[84] CAST 则直接用 solver cost-to-go 的下降 $N(s_t)-N(s_{t+1})$ 形成 turn signal，并把终局 reward 保留为全局锚；在没有精确 solver 时，它也测试 learned value network。[85] 对本项目而言，四层 risk model 更应被检验为一个近似 state-value/VOC estimator，而不是以 entropy 名义获得特殊地位。

CRPO、PCD 与 $\beta$-OPSD 进一步说明 credit 至少需要“方向、位置、延迟”三个独立判断。CRPO 的 entropy difference 不是奖励本身，而是决定学生是否应接近特权教师；当教师相对学生出现大的熵降时，论文把它解释为可能的 exposure bias，并对该位置施加远离教师的对比方向。[111] PCD 将下游失败与 teacher–student disagreement 相乘，只在二者共同支持“感知层可纠正”时提高该层蒸馏权重，同时保持 reasoning objective 的均值不变。[112] $\beta$-OPSD 的 return-to-go 则累计当前位置之后的 student–target mismatch，让早期 token 对未来偏差负责。[113] 因此，四层风险下降若用于 credit，至少要同时通过 outcome sign、目标层可纠正性和 fixed-continuation delayed effect；单步熵降只能作为调幅特征。

AttriMem 将最终答案的 token-level context attribution 映射回产生 memory record 的操作，再与 outcome reward 联合训练 memory policy。[86] 它并非 web search 方法，但直接覆盖“根据最终答案对中间信息操作分 credit”的相邻空间。OWIC 若加入 source-span attribution，必须把它作为 baseline，并检查长上下文 attribution error、冗余证据和答案生成器依赖，不能把 attribution 当成已识别的因果贡献。

两项可靠性工作给出新的压力测试。MisKnow-Agent 在控制 authority、source style、rank 和 lifecycle stage 的误导文档注入中报告：一篇误导文档把六种 open-source 配置的平均 FCAR 从 0% 提高到 54.7%，pre-synthesis 注入的平均 FCAR 为 85.5%，而 front/spread/back 排名条件只在 66.2%/65.5%/64.5% 间变化；pre/post defense 均未消除采用。[87] 这些数字仅属于其 DeepResearch Bench 设置，但说明来源排名、重复证据或 posterior 变尖都不能替代 evidence truthfulness。FinanceHarness/FinanceGym 则用 per-question point-in-time sandbox 分开 pre-cutoff evidence 与 post-cutoff outcome rubric，并观察到 specialized agent 的 tool-distribution shift。[88] 因而，DeepWide 实验需要连续验证进入 state 的证据、在 synthesis 前再核对 load-bearing claims，并冻结检索截止时间、后端和工具契约。

Forage V2 对开放集合给出更直接的命名：当完成边界没有预先给出时，代理会系统性低估 denominator，并可能对自己发现的小集合报告 100% coverage。它把 Planner 与独立 Evaluator 隔离，让两者分别收集对象和发现“完整意味着什么”，再把 denominator 修订经验跨 run 迁移。[72] 这占据了“首次发现分母盲区”或“首次让代理同时搜索答案和完成边界”的主张。它仍不是本项目拟议的概率层：每个 run 使用自己发现的 denominator，论文明确指出这些 coverage 百分比不能跨 run 直接比较，也没有给出未见质量的校准 posterior。

Shared Discovery Paradox 提供了另一个必要反例。在其有限 Bayesian 搜索模型中，汇总线索提高了最佳单一推荐的准确率，但若八个搜索者都执行该推荐，发现率从去中心化搜索的 0.8322 降到 0.3835；对同一 pooled reports 分配 top-eight posterior portfolio 则达到 0.8594。[73] 这不是 DeepWide 实证结果，却解析性地说明 belief quality 与 coverage policy 是两个变量。即使四层 posterior 完全正确，若 controller 没有对重复动作、来源相关性和边际覆盖去重，信息集中仍可能伤害 width。

由此，当前系统缺口不是“有没有表格状态、coverage map 或 deep/wide routing”，而是这些控制决策是否由一个经过校准、显式包含开放集遗漏质量的信念模型驱动，并在相同动作空间和预算下带来更低任务风险。

两项新近的 multi-agent 结果要求把“并发”与“委派”拆开。Two Calls Beat Five Agents 在一个本地 7B 模型上发现，五角色 pipeline 会因格式和错误累积而落后于两次 self-refinement，且同一 refinement 在直接准确率已经很高的 HumanEval 上反而破坏性能；作者随后用 task-aware gate 才减少该退化。[91] SKIMIX 的摘要同样报告 agent-count scaling 非单调，收益主要集中在第一轮 refinement，且开放式数学与多选任务的方向不同。[92] MANTA 则允许角色、通信边、顺序、信息可见性和验证路径在推理时有界变化。[93] 因而，大并发只能解决吞吐。若把 WebSwarm 或 MANTA 式多 agent 作为质量机制，必须在相同总 token、tool call 与 wall-clock 下报告 agent count、round 和 topology 的完整曲线，并保留单 agent 与两次 refinement 对照。

DivInit 进一步说明名义并行宽度不等于有效宽度。标准 parallel sampling 的首轮查询可能近乎相同，导致后续线程读取重叠文档并相关失败；DivInit 在一次调用中生成 $n$ 个首轮候选，再以 MMR 选出 $k<n$ 个种子，后续轨迹保持不变。[143] 论文报告的 5–7 点提升主要基于 pass@4/pass@k，且 limitation 明确指出它是 thread-pool ceiling，不是部署时单答案准确率。DeepWide 的 `1/2/4/8` agent 消融必须同时比较 independent sampling、DivInit-style first-turn diversification 和 evidence-equivalence-aware routing，并冻结单表聚合规则；query surface、URL、正文与 source dependency 四级 overlap 要与 nominal width 一起报告。

Dr-DCI 提供了比 raw file agent 更贴近工程现实的执行基线。它把 retriever 作为 `pull` 动作，将候选文档加入可持续的 bounded workspace，然后使用本地跨文档操作进行过滤、比较和验证。[144] 这不估计开放集合 unseen mass，也不解决 DeepWide 的四层校准，但占据了“全局候选发现与局部精细验证分层”的宽泛主张。后续应比较 raw web/file exploration、global BM25 ranking、Agent+BM25、Dr-DCI-style dynamic workspace 与 WebSwarm；workspace reset 必须保留原文和 provenance，不能用 context reset 丢失证据依赖。

VecTree-RAG 把这条基线进一步拆成语料级与文档内两层。第一层以 dense/sparse retrieval 排论文和 section entry，第二层暴露 source-verified section tree，再按页读取正文或图像。[151] 它在固定文献库中提高了作者所报的 answer/evidence-localization 指标，但正文同时指出 multi-turn agent 并非在所有基准上比 flat retrieval 更省 query-time tokens，MOSAIC 的 49 题又由模型生成和自动筛选而未经过独立人工 adjudication。DeepWide 因而应加入 `global rank → structural locate → page read` arm，并冻结 index、tree/parser 和 page-store 字节；该 arm 是执行对照，不是 unseen-mass estimator，也不是 live-web 成绩先验。

SwarmResearch 将动态深宽分配扩展到开放式代码发现。它让一个全局 Shepherd 在独立 git 分支上选择 Explorer/Optimizer 的父状态、局部上下文与并行波次；固定伸缩对照保持 60 次 worker iteration，并在五个任务、三次重复中比较不同 width×depth。[147] 该结果说明固定的 `1/2/4/8` 曲线仍不足以证明自适应调度，必须再与同 worker-iteration 的 depth-varying controller 比较。不过论文的主要 15-task 结果每题只有一次长运行，任务有隐藏 evaluator、无互联网，且动态组使用更强 orchestrator。因此它只提供调度机制近邻和方差警告，不是 WebSwarm 或 DeepWideBench 的直接强弱证据。

Sample More, Reflect Less 把这个对照推进到按实际生成 token 匹配的采样曲线。在其 150 题、可自动核验的数学设置中，36 个配对比较没有一个方法可靠优于等成本重复采样；Best-of-N 的相同八个样本由模型自选时，在 1.5B 上比多数计数低 8.0 和 11.3 个点，在 7B 上差值缩至 2.0 和 1.3 个点且区间跨零。[104] 这些数字受模型规模、数学答案可等价计数和只统计生成 token 的限制，不能外推为“WebSwarm 无效”。它们改变的是证明责任：DeepWide 的开放式表格没有天然 majority-vote baseline，但可以对同一预算做独立搜索样本的 evidence-set union、去重后的 candidate/table aggregation 和随机委派对照。所有输入 token、重复上下文、顺序依赖与并行 latency 也必须计入，且要报告 adaptive branch 实际触发比例，避免一个名义 swarm 实际退化成单 agent。

相关失败使名义 agent 数进一步高估有效 width。One Human, N Agents 在一个两层 Gaussian-copula 审计模型和 15-agent trace replay 中报告，跨模型错误相关性主要随共享题目难度变化；五个开源模型的口头置信在其锁定 elicitation 下近乎常数，confidence-ranked audit 接近随机。[107] 这不是搜索委派实验，但提示 DeepWide 不能把四个 sibling 的相似结论当作四份独立证据。下一版应按 query intent、URL/content、source dependency 和 answer/evidence-set overlap 估计 effective independent branches，并与 nominal agent count 一起报告。

CAM-DF 进一步把工具取得写成真正的决策问题，而不是 ranking 后附一个阈值。其监督量是 stop-now 与 best continuation 的离线 payoff gap，符号决定停或继续，幅度表示错误决策的代价，并显式纳入异质工具成本。[90] 这与 terminal-loss VOC 的方向一致，但更接近可训练的停止头。DeepWide controller 必须加入 CAM-DF-lite、固定阈值和 oracle best-prefix 对照，并分别报告 tool ranking quality 与 stop decision regret。

BeyondUncertainty 与 SVR 给这个停止实验补上两个容易遗漏的成本和失败指标。BeyondUncertainty 的口头置信对检索收益只有中等排序能力，绝对校准较差；其路由少取 20.4% passage，却因额外 probe 让总 token 比 always-retrieve 增加 28.2%。[105] SVR 在数学推理中学习 verdict–confidence gate，并在完整系统比较中减少平均 turn；但其主阈值下错误提前停止仍为 29.9% 和 37.0%，阈值过高还会越过正确中间答案并在后续回归。[106] 因而 DeepWide 的 stop head 不能只报少搜了多少或平均轮数。必须把 probe 的全部输入/输出 token 计入，报告 premature-stop、correct-intermediate-overwrite、forced-stop、abstain 和 branch-trigger rate，并与等预算独立搜索/聚合比较。

HYSET 从工具检索侧说明组合价值也不能由逐项分数简单相加。它把一组工具作为 query-conditioned hyperedge，显式建模集合大小和工具兼容性。[109] DeepWide 的 query/agent 组合不是工具集合，但同样存在互补与冗余。四层 risk/VOC controller 应比较单动作评分、greedy marginal gain 与小规模 set-level portfolio；若多个分支落入同一 evidence equivalence class，其组合价值不能按独立增益求和。

HiEviDR-Bench 与 LEDGERMIND 把 evidence state 的要求具体化。HiEviDR-Bench 为每题构造 evidence→intermediate claim→conclusion 的分层图，并用 report quality、traceability、citation、claim verification 与 answer correctness做 progressive gating；其 2,000 题、16 模型实验中，作者报告 evidence identification 与 intermediate claim construction 是早期瓶颈。[89] LEDGERMIND 则要求 reasoning 和 repair 只能引用 active、tool-produced ledger entries，并把 repair 写成不允许无来源内容进入的 typed transition。[99] AskChem 进一步把检索单元从 paper 改成带 DOI、verbatim quote 或 evidence locator 的原子 typed claim，并在 claim store 上同时提供 faceted taxonomy、evidence graph 与 exploratory taxonomy。[102] 这些工作说明 evidence graph、claim ledger 或 provenance-constrained repair 不能作为本项目的独立创新。可比较的新增部分只能是四层风险怎样在这些受约束状态上校准和决策。

LayerRAG-Bench 与 Selective Credibility-Limited Belief Update 又说明“有引用”仍不够。前者把故障分成 evidence、tool contract、authorization 与 session state，作者报告 groundedness-only 评价会把 stale 或 wrong-session evidence 误判为成功。[100] 后者在形式 belief update 中允许每个 source world 只接受 compound input 的一个可信弱化版本，而不是整体纳入。[103] 对 DeepWide 而言，每条观测需拆成可接受的子命题，并记录 source、session、tool contract、被削弱或拒绝的部分。否则一个高相关页面可以在错误会话或过期状态下产生更尖锐却无效的 posterior。

MAPD 给 WebSwarm-style 经验迁移增加了一个训练基线。它不在推理时运行 swarm，而是让离线 Orchestrator、Searcher、Repair 和 Protocolizer 生成结构化 JSON；quality gate 检查 schema、exact-match consistency、抽取式 grounding 和 oracle leakage，学生再用同一模型的 protocol-conditioned branch 做 self-distillation，并保留终局 outcome RL。[121] 论文全文明确把 ground truth、成功标签和 repair diagnosis 限制在 privileged synthesis。DeepWide 若训练 no-entropy 或 entropy controller，必须把 offline privileged protocol、runtime visible state 和 evaluator-only metadata 物理分层；任何 `task_type` 或 success-conditioned protocol 都不得进入同一题的 label-blind forward pass。实验还需比较 raw trajectory imitation、structured protocol、outcome-only RL 和 protocol-plus-outcome 四组，防止把格式蒸馏误写成 entropy credit。

FA-SD 给这个训练对照增加了负向控制。成功 rollout 作为 privileged prompt 可以提高 self-teacher 的即时表现，但 KL 蒸馏仍可能退化为跨问题重复的 reasoning/search 模板；论文把这一现象称为 decoding collapse，并将不稳定性拆为 evolving model inconsistency 与 feedback prompt inconsistency。[146] fixed-reference 和 EMA teacher 改善稳定性，却需要 warm-up，且 feedback-augmented external teacher 仍可能弱于普通 external-teacher OPD。OWIC 训练不能只报 teacher–student KL、表面 trajectory diversity 或最终平均分；必须报告输入条件化的 query/action diversity、有效监督样本比例、teacher drift、warm-up regression，并比较 outcome-only、fixed teacher、EMA teacher 与无 privileged feedback。

RRM 与 GRSD 补上两种经验复用对照。[95,156] RRM 把跨任务 procedural retrieval experience 与当前任务 factual evidence 分开，经验只生成 query-level guidance，最终回答仍只能条件于当前视频新取回的事实；usage、reuse feedback 与 temporal decay 控制经验生命周期。GRSD 则从同 prompt 的 on-policy success/failure rollout group 提取 outcome-discriminative reflection，并用 stop-gradient self-teacher 调幅而不翻转 verifier advantage。DeepWide 若复用 WebSwarm sibling experience 或历史失败记忆，必须保留同样的物理边界：经验可以改变搜索策略，但不能作为当前题的事实证据；其训练还要与 fixed/EMA teacher、raw trajectory imitation 和 outcome-only RL 比较。

ACM 把长程上下文管理写成两个显式动作。`manage_context` 将一段历史总结后把原始消息按 ID 外置，`query_memory` 再针对该 ID 读取原文；工作上下文可以缩短，但原始信息仍可追溯。[122] 这种“lossless”只描述存储可逆性，不保证 summary、召回或后续使用无偏。其 dual-constraint teacher 会查看 reference answer，决定哪里应压缩、继续搜索或作答，因此只可作为离线 privileged action-timing baseline。DeepWide runtime 的 offload 决策必须仅依赖可见 token pressure、重复/死路证据、四层风险和成本；每次 offload 需保留 source/session/provenance，并与同状态 `continue-search`、`answer/abstain` 比较终局损失。

OrchBench 与 AgentRadio 把 orchestration quality 和通信机制拆成两个摘要级候选对照。OrchBench 用带依赖、context limit 和 agent budget 的 DAG，在不调用 worker 的确定性模拟器中比较信息保留、makespan 与 token cost；它提示先评估 plan，再把 worker 能力与工具噪声放回 end-to-end gate。[124] AgentRadio 则让代码 agent 在前台工作时异步收到 peer message，说明同步轮次不是唯一通信接口。[129] 两项都未在 DeepWideBench 上验证。未来 WebSwarm baseline 应先做 content-free orchestration simulation，再在相同总预算下比较 staged handoff、bounded async message 和无 sibling communication；跨题 executor 并发仍须与单题 agent 通信分开。

Self-Speculating Agent 提供了第三类吞吐对照。它让同一模型从 partial trajectory 预测下一 tool name 与完整 arguments，并用当前策略真实 rollout 的下一调用作为训练目标。[133] 该机制只适合 search、retrieval 和 database lookup 等无外部副作用的工具；论文也把可改变环境的 speculative call 列为限制。其评测为保持任务轨迹不变，并未真实预执行预测调用，因此只验证 next-call match 和 policy 兼容性，未验证净 wall-clock、额外请求占用或错误 speculation 的容量代价。DeepWide 若以后加入该基线，必须在容量冻结后单列 hit rate、取消/浪费请求、实际 tail latency 和任务质量，且不得在当前冻结全集中途接线。

AdaCoM 把 context management 从 agent 内部移到一个单独训练的外部 LLM，在每个 agent step 前对历史消息执行保留、删除、重写或合并，而底层 agent 保持冻结。[161] 它直接占据“对冻结 GPT-5.6 学一个外部 context controller”的宽泛主张。论文观察到的 Fidelity–Reliability trade-off 和 capability-near transfer 说明 manager policy 不能假定跨模型通用；其 BrowseComp 训练还用 gold/key-document ID 提供正 process reward，因此只能作为离线 privileged baseline，不能进入 label-blind runtime。DeepWide 的 context 对照应固定 agent、工具和预算，比较 append-only、固定摘要、可逆 offload、AdaCoM-style manager 与四层 VOC，并报告 root constraints、原始 evidence ID、load-bearing claim 与 provenance 的保留率。context 缩短本身不是任务价值，也不能自动获得 entropy credit。

SpecHop 则把 speculative tool use 从 next-call prediction推进到实际异步执行。[162] 快速但不可靠的 speculator 产生后续 sub-answer 和线程，target tool 返回后由规则 verifier 决定 commit 或 rollback；论文中的 web-search setting 在三组多跳 QA 上保持其标准轨迹的 EM/F1 附近，同时用更多并行调用降低 wall-clock。其保证依赖 faster-speculator、可靠 verifier 和可回滚的只读工具，且活动线程越多计算开销越大。它应作为 latency baseline，而不是质量/controller baseline；任何 DeepWide 复现都要同时报告 target/speculator/model 调用、错误分支、取消或浪费请求、tail latency 和最终任务质量。

Silent Failures、HalluProp、$\Sigma$-Mem 与 SafeFlow 共同要求把“agent 说了什么”与“该信息能否传播”分开。Silent Failures 的全文 taxonomy 包括未使用输入模态、无支持引用、错误证据却答对、冗余检索洗白、跨模态矛盾和虚构 provenance；其 fine-grained judge agreement 又明显弱于 answer-correctness agreement，因此这些标签只适合作为分层诊断，不可直接变成未经校准的训练 reward。[123] HalluProp、$\Sigma$-Mem 和 SafeFlow 的一手摘要分别提出交互前传播风险、依赖 post-decision correctness 的 peer-reliability memory，以及沿 collaboration graph 传播 root-request semantic taint。[125–127] 本项目应冻结 child-to-parent envelope，使每条 finding 携带 active evidence、root scope、source dependency、可靠性来源和 taint；post-terminal reliability 可以更新未来任务的 memory，但不得反馈到同一 evaluated forward pass。

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
| CIGPO (2607.16244) | frozen reference 对 gold answer 的逐 turn log-likelihood 增量；与 F1 分开归一并做权重 curriculum | 是 | 否 | contextual IG credit 已有；主要解决 group-relative reward 方差塌缩，不能进入 label-blind runtime [118] |
| Bridge Evidence / CTU (2607.15253) | 删除单篇已读文档、固定此前 prefix 并重跑 suffix；比较终局答案、下一查询检索质量与 turn 成本 | gold evidence 与答案评价用于离线研究 | 相对指定 omission 与 replay policy 的局部效应 | 静态相关性或即时熵降可能漏掉开启下一跳的 bridge evidence；应作为 evidence-step credit 强基线 [117] |
| CHILL-Harness (2607.25825) | factual workflow 与候选 workflow 的干预相对 task/resource advantage | 训练需 paired intervention/effect evidence | 以显式 intervention estimand 学习 | 已把 harness 适配写成 effect estimation→candidate valuation→authorization；OWIC 只能提供特征，不能跳过执行授权门 [119] |
| AdaKP (2607.24833) | gold-solution knowledge point 注入前后的 next-token entropy reduction；LOO answer accuracy 只作预检 | 是，候选提示来自 gold solution，proxy gate 使用 LOO accuracy | 否 | 在该数学提示设置中，entropy reduction 是经过 LOO 排序检验的低成本 selection proxy；它使用冻结 proxy 且不提供开放世界 step contribution [130] |
| TAPO (2607.27973) | rollout 中 action-conditioned next-observation prediction | 否额外 expert data；仍使用环境 rollout 与 task reward | 否 | transition supervision 可作为 dense auxiliary baseline，但预测环境后果不等于给历史步骤分配 task credit [131] |
| MARS-RA (2607.27967) | 多模态模型对协作 agent 的 pairwise contribution comparison 与 rank aggregation | 依赖 multimodal comparison model | agent-level surrogate | 多 agent credit 可比较相对排序而非绝对 scalar；仅适用于 swarm arm，不能代替 temporal step intervention [132] |
| HiMPO (2606.16285) | 同一 compressed pre-write state 下旧/新 memory 的 target-outcome recoverability 差，再以 hindsight relevance 过滤 | 是；需要可靠 target outcome，并以 sibling writes 归一 | 局部 memory-write counterfactual，非完整终局干预 | 已直接处理 memory credit 与 tool/reasoning blame leakage；OWIC 必须比较 HiMPO-style recoverability，并证明四层 task-risk、开放 denominator、bridge-step 与终局 continuation 的额外价值 [149] |
| WikiLoop (2607.26604) | 同一 pre-edit Wiki 上候选 patch 的 frozen-Navigator before/after utility，并惩罚 unrelated-query regression | 是；训练期使用冻结 evaluator、affected/guard query sets | 编辑级同起点 paired utility；隔离 copy，不是 persistent closed-loop effect | downstream utility credit 与 guard 已有；知识/证据写入不能只按 entropy 或绝对 post-state 打分，必须加入固定消费者、负迁移 guard、edit cost 与 moving-evaluator audit [150] |
| ConMem (2607.28126) | 固定日志 evidence unit 在不同 coalition 中对下游诊断 utility 的 Shapley-style 边际贡献；近似排序驱动 memory retention/eviction | 是；utility 由训练期下游诊断与后续确认异常定义 | coalition attribution，非 live-web temporal intervention | 已直接按估计贡献给记忆证据定价；OWIC 必须加入 pruned-Shapley memory baseline，并证明开放 denominator、同状态 action continuation 与 label-blind 四层风险的额外价值 [158] |
| PCD (2607.28336) | 同一 perception prefix 下多 reasoning continuation 的失败率 × perception-span teacher/student KL | 无 perception 标签，但使用终局 verifier 与强 teacher | 否；双 witness soft-AND，只识别 teacher-correctable failure proxy | reward-only PSR 不能区分感知不足与推理困难；DeepWide 必须拆分 evidence acquisition、reasoning、canonicalization 与 renderer credit，并报告 teacher competence 假设 [112] |
| GRSD (2607.28076) | 同一 prompt 的成功/失败 rollout group reflection；self-teacher 调制 outcome advantage | 需要 verifier 标注 group outcome；guidance 为训练期 privileged | 否；保持 verifier 给出的方向 | success/failure group contrast 已有；可作 no-entropy learned-credit baseline，但不能进入同题 label-blind runtime [95] |
| Agent-fleet audit allocation (2607.28317) | agent self-confidence、审计预算与两级相关误差 | replay 使用已记录正确性；在线调度只见 confidence | 否；估计 confidence-ranking 何时劣于随机 | 直接否定“低熵/高置信就优先审计或扩并发”；需 calibration、correlation 与 random/round-robin fallback [107] |

ECHO 的范围最值得正面说明。它在 Clue Selector Game 中有均匀有限候选集、真实 oracle、确定性过滤和精确 posterior，主 reward 是候选集合的分数式收缩；实验只到 1.5B、约 10 turns。论文将近似信念、噪声或对抗来源、开放工具动作和 web search 明确列为未解决限制。[43] 这恰好留下 DeepWide 的工程与统计难点，但不留下“首次提出 epistemic credit”这一概念空白。TRACE、LOTAPO、STAMP、RICE-PO、SIOP、CVT-RL、CRAFT、BiPACE、ACPO、PBSD 和 PiCA 又分别覆盖 gold-readiness TD、删除 attribution、provenance、局部分支、label-free potential、显式干预、sibling counterfactual、state-matched baseline、entropy reweighting 与 privileged likelihood credit。[44–54]

Bridge Evidence 把“眼前有用”与“让后续搜索成为可能”分开测量。作者在 HotpotQA 的 1,000 个开发问题上，对代理实际读取的每篇文档做 omission replay，并在 23,322 个文档观测上报告 Static RAG Utility 与 Counterfactual Trajectory Utility 的 Spearman $\rho=-0.026$；35.7% 的已读文档落入低静态效用、高轨迹效用的 bridge 区域。[117] 这些数值只属于该 ReAct/Wikipedia 设置，且 CTU 仍依赖 gold evidence、组合权重和固定 replay policy。它仍直接否定了“证据没有立即降低答案熵或填格，因此没有 credit”的规则。DeepWide 的离线 audit 应分别保留 terminal-task delta、next-action enablement 与额外成本，不能在采集时先压成一个熵差。

CIGPO 与 CHILL-Harness 从训练和控制两侧进一步占据相邻空间。CIGPO 直接用 frozen reference 对 ground-truth answer 的逐 turn log-likelihood 增量提供 contextual IG reward，以维持 GRPO 的组内奖励方差。[118] 这使“信息增益较大的 turn 多给 credit”本身更难成为创新，而且该信号只能作为训练 oracle。CHILL-Harness 则先估计具体 workflow 相对 factual workflow 的干预效应，再选择候选，最后只有 estimated advantage 超过授权 margin 才真正替换 workflow。[119] 对 OWIC 的含义是：四层风险或 entropy 可以参与 effect predictor，但候选排名与执行授权必须分开；高分不足以自动改变在线搜索拓扑。

2026-07-20 至 21 日的补充检索进一步收紧了 novelty。InfoPO 用 masked-feedback counterfactual 衡量一次用户反馈对后续动作分布的改变，再以 outcome gate 融合任务方向；AEM 在 response 粒度用 uncertainty proxy 重缩放 advantage；SELAUR 将 entropy、least confidence 与 margin 注入失败轨迹奖励。[66–68] STRIDE 把 outcome-discriminative pattern 与 saliency entropy 结合，APPO 则明确报告 token entropy 本身不能可靠定位影响最终结果的决策点。[69,70] PivoARL 从失败轨迹中定位 pivotal turn 并只从该状态重试，以 information-gain 视角解释信号集中。[71] A²TGPO 与 T²PO 又分别把 turn IG 用于归一/clipping，把 uncertainty dynamics 用于 intervention/resampling。[74,75] 因而，“信息增益 + counterfactual + outcome gate”“response-level entropy credit”“pivotal retry”与“uncertainty-guided resampling”均已有直接近邻。可辩护的范围只能落在 DeepWide 的四层开放世界任务变量、未见质量，以及 evidence provenance 与任务风险的联合验证上。

另一些相邻路线不直接用 entropy。GraphGPO 把多条 rollout 聚成状态转移图，以到目标的图距离变化分配 edge credit；ReBel 用 belief consistency 与 belief-aware grouping；OASES 学习一个随 search policy 共同更新、由终局 outcome 对齐的 state evaluator。[58–60] 它们要求 OWIC 证明“信息论表示”比图距离、belief consistency 或 learned progress evaluator 带来额外价值，而不能只证明任何稠密过程信号都比终局 reward 好。

Forage V2 使“未知完成边界”的 novelty 范围进一步收窄。它明确命名 denominator blindness，通过独立 Evaluator/Planner、共演 evaluation 和跨 run 组织记忆学习完成标准。[72] 因此本项目不能声称首次识别开放世界 denominator 问题。它仍留下的可检验差异是：是否能对未见质量与 premature-stop risk 给出校准概率，并与 anchor、row 和 cell 任务损失共同决策，而不是只通过组织审计学习 denominator。

Shared Discovery Paradox 表明“信念更准”与“覆盖更高”可以反向变化。在其可解的 16-box/8-searcher 基准中，pooling 将单个最佳建议的准确率从 0.20 提高到 0.3835，但 8 人重复该动作的群体发现率只有 0.3835，低于分散线索跟随的 0.8322；对 pooled posterior 做 8 动作 portfolio 可达 0.8594。[73] 这些理论数字不是 DeepWide 实验结果，但它们对 controller 提出直接约束：路由器必须联合 posterior、动作组合、来源依赖与多样性，不能将所有 worker 都派到同一个最高 posterior 或最高 entropy 项。

SkillRise、GRSD、TTEL、OVCSD 与 CSCR 把 credit 的邻域继续压缩。SkillRise 将当前任务 outcome 分配给 solving phase，把折扣后的下游任务 outcome 分配给 skill curation，因此“memory 写入对未来任务有用”已有直接的跨任务 credit baseline。[94] GRSD 从同 prompt 的成功/失败 rollout group 提取 outcome-discriminative guidance，但仍保留 verifier 决定的 advantage 方向。[95] TTEL 用 informed feedback 相对 null feedback 的概率差定位失败轨迹的可疑 token，并从该处复用前缀、重生成 suffix；这是一种错误定位，不是正向贡献识别。[96] OVCSD 只在 student-reached state 的首次对齐分岔处蒸馏 outcome-verified teacher continuation。[97] CSCR 则发现大 likelihood shift 常集中在可替换的表面 token，且正确/错误条件可能同向改变，因此将高 sensitivity token 降权。[98] OWIC 必须分别比较 downstream-return、group-contrast、feedback-vs-null、state-aligned continuation 和 opposing-outcome sensitivity；一个步骤改变模型分布的幅度不能替代 task contribution。

AdaKP、TAPO 与 MARS-RA 给这组对照增加了三条不同的非因果路径。[130–132] AdaKP 的 entropy proxy 在其数学提示设置中先用 LOO marginal accuracy 过 Spearman gate，但 knowledge points 来自 gold solutions，proxy 还冻结在初始策略；该结果不能直接迁移成 label-blind web credit。TAPO 从 rollout 复用 next-observation targets，检验的是 transition representation 能否改善 policy。MARS-RA 用 agent 间 pairwise comparison 缓解动态团队规模下绝对分值噪声，检验的是团队成员相对贡献。OWIC 若优于这三类方法，必须分别说明收益来自开放世界 task-risk calibration、temporal intervention，还是多 agent aggregation，不能只报告一个最终平均分。

PCD 把“失败发生在哪一层”写成一个可识别性问题。[112] 对固定 perception $z$ 的多次 reasoning 只估计 $V(z)=\rho(x)q(z)$，其中 $\rho$ 是当前 reasoner 在充分感知下的成功率，$q$ 是 perception 充分概率；相同乘积可由不同的 $\rho,q$ 产生。因此，增加 continuation 数量只能降低这个混杂量的方差，不能识别错误来源。PCD 另加 teacher disagreement 作为第二 witness，并只重分配 perception distillation 权重。这个结果不是 DeepWide 的直接证据，但它要求 OWIC 的 Gate 2B 至少包含 stage-preserving continuations 和双 witness：终局失败不能自动给所有早期 search/evidence step 负 credit，熵降也不能自动把 renderer 或 canonicalization 改进记为搜索 credit。

agent-fleet audit-budget 工作给出另一个校准反例。[107] 在其两级 Gaussian-copula 模型与记录轨迹 replay 中，self-confidence 失校准越过阈值后，confidence-ranked audit 可以比随机抽查更差，且共享任务难度造成的跨模型相关误差不可忽略。该结论不直接决定 DeepWide 的容量档位，但改变了控制合同：entropy/confidence 只能在 held-out calibration 与 correlation stress 通过后参与 audit、defer 或 worker allocation；random、round-robin 和 coverage-diverse allocation 必须保留为强对照。

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
- **终端损失错位。** 即使信息只关于最终最优动作，若不同错误的后果不同，高 entropy bit 也可能几乎不影响任务损失，而低 entropy bit 决定大额 regret。Search as Computation Allocation 证明这种 IG 排序误差可以任意大。[83]
- **bridge evidence 漏记。** 一篇页面可能不改变当前答案分布，却提供下一查询所需的判别实体。若 credit 只测即时熵降或静态相关性，这类步骤会被记成零；Bridge Evidence 的 omission replay 正是针对这种延迟可达性。[117]
- **proxy 验证不可移植。** AdaKP 的 entropy reduction 在 gold-derived knowledge-point pool 上通过 LOO accuracy gate，不能推出同一 proxy 在开放 web、动态 evidence set 或当前策略下仍保持排序。[130]
- **stage attribution 不可识别。** 同一早期 evidence/perception 后的低终局成功率可以来自早期信息不足，也可以来自后续 reasoner 困难；更多相同 prefix continuation 只减少混杂估计方差。PCD 因此另加 teacher disagreement witness。[112]
- **置信排序可能反转。** 当 self-confidence 失校准且 agent 错误相关时，按置信度分配稀缺审计或 worker 预算可劣于随机策略。[107]

这些反例说明，信息 credit 要先回答“关于什么随机变量的信息”“相对于什么任务损失”“在什么干预下有贡献”，不能只计算语言模型输出熵。

HiMPO 与 WikiLoop 还把 memory/knowledge 写入的 credit 边界推进到实现层。[149,150] HiMPO 的局部量比较相同 pre-write state 下旧、新 memory 对 oracle target outcome 的平均 log-likelihood，随后只把经 hindsight relevance 支持的方向施加给 memory tokens。WikiLoop 则让冻结 Navigator 在隔离的 pre-edit Wiki copy 上分别运行 before/after，并把 affected-query utility gain、unrelated-query regression、编辑成本和结构惩罚分开。两者都比裸熵差更接近“该写入是否有用”，但仍依赖 target/evaluator、局部状态与指定消费者；HiMPO 不执行完整 suffix task intervention，WikiLoop 也明确没有优化 persistent write-back 与 moving evaluator 下的历史依赖 credit。它们应作为强对照，而不是被合并成 OWIC 的支持证据。

结构性 credit 还需要处理步骤间协同。若把一组步骤 $S$ 在有效重放下的任务价值写成 $v(S)$，两个步骤的二阶交互为

\[
I_{ij}=v(\{i,j\})-v(\{i\})-v(\{j\})+v(\varnothing).
\]

$I_{ij}>0$ 表示二者共同出现的价值超过各自边际值之和。Shapley value 可通过对所有有效加入顺序的边际贡献取平均来处理顺序依赖，但精确计算随步骤数指数增长，而且网页轨迹中的任意“步骤联盟”常无法形成有效状态。[65] 因此第一版只在高影响 discovery–verification、evidence–synthesis 对上做二阶干预诊断；若交互足够普遍，再评估 permutation-sampling Shapley，而不把全轨迹 Shapley 作为默认组件。

### 5.4 推荐的新主张：开放世界的结果对齐信息 credit

建议把候选方法暂称为 **Open-World Information Credit (OWIC)**。它不是新的 Shannon 公式，而是一套 DeepWide 特有的 credit 约束。名称有意不含 “causal”：AMR-SD 与 PGPO 已把 teacher/student 或有/无视觉条件下的 likelihood/KL 比称为 Causal Information Gain，但这种命名本身不等于干预识别；本项目只有在明确 intervention、固定 continuation、validity/overlap 与识别假设成立的分析中才使用 causal interpretation。[61,62] Search as Computation Allocation 进一步要求把 OWIC 的规范部分写成 terminal task value/VOC；信息量只能解释其中的 epistemic observation，不是独立的终端效用。[83]

1. **四层 credit target。** 分别追踪 anchor $A$、未见质量 $M$、行资格 $R_e$ 和 cell 值 $Y_{e,c}$，禁止用一个答案 entropy 覆盖四类错误。
2. **结果对齐。** 信息信号只有在改善 proper score 或任务风险时才为正。反证即使提高 entropy，只要降低错误风险也应获正 credit。
3. **开放世界。** `OTHER`、新 hypothesis 生成与 unseen-mass posterior 进入状态，避免在错误有限 support 上奖励收缩。
4. **局部反事实。** 对高影响步骤从同一 $h_t$ 执行等成本 sibling action、证据替换或 no-op，并用固定 continuation 比较 task value；不把不同历史的同 turn 当作同状态。
5. **provenance 分工。** 证据图分别记录 discovery、independent verification、contradiction resolution 和 synthesis。STAMP 的 first-exposure credit 是 discovery baseline，不应让后续独立验证永远得零。
6. **成本与伤害。** 无效查询、重复证据、无支持输出、污染来源和成本进入负项。

一个可检验的混合信号为：

\[
c_t = \underbrace{L(B_t)-L(B_{t+1})}_{\text{task-risk change}}
+\lambda\underbrace{\operatorname{RelIG}_t}_{\text{diagnostic / log-loss subvalue}}
+\beta\underbrace{\widehat{\Delta}^{\mathrm{cf}}_t}_{\text{same-state contribution}}
+\rho\underbrace{c_t^{\mathrm{prov}}}_{\text{verified evidence role}}
-\eta\underbrace{C_t}_{\text{cost / harm}}.
\]

其中 $L$ 必须由 dev set 上冻结的 proper scoring rule 或 DeepWide task-risk surrogate 定义，$\operatorname{RelIG}$ 只计算与四层任务变量有关的信息；除非对应子任务明确使用 log loss，否则它不得覆盖 $L$ 或单独决定动作/credit 符号。$\widehat{\Delta}^{\mathrm{cf}}$ 的干预族和 continuation policy 分开报告。为保持策略不被任意 shaping 改写，可把 $\Phi(B)=-L(B)$ 的差分作为 potential-based shaping 分量；Ng 等人的结论只在固定 MDP 与正确 potential 形式下保证 policy invariance，不能为错误 belief 或开放世界 support 提供保护。[42]

### 5.5 新颖性 verdict

| 版本 | 可行性 | 新颖性 | 建议 |
|---|---|---|---|
| token/response entropy 低或熵降大就多给 credit | 中，容易实现 | 很低；EMPG、TEPO、ACPO、AEM、SELAUR 等已覆盖 | 仅作消融 |
| semantic entropy reduction 作为 turn reward | 中 | 很低；InfoReasoner、ECHO 直接覆盖 | 强基线，不作主贡献 |
| gold-answer log-prob gain / TD credit | 高，训练信号稳定 | 低；IGPO、TRACE、PBSD、IG-Search 已密集覆盖 | 训练 oracle baseline |
| leave-one-turn、首次证据或 evidence omission suffix replay | 中高 | 低；LOTAPO、STAMP、Bridge Evidence 已覆盖 | provenance / retrospective/counterfactual baseline |
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
| Evidence-aware termination、ScaffoldAgent | 预声明的证据充分性条件；evidence-indexed outline 与复合 downstream utility | 推理控制 | 是，继续取证或扩张/收缩/修订 outline | 否 | 显式充分性停止、utility-guided structure 与边际收益停止已有；四层方法必须证明校准终端风险的增量 |
| Forage V2、Shared Discovery Paradox | 自发现 denominator；pooled posterior 与动作组合 | 覆盖审计/分配 | 是 | 是，但前者为自定义 denominator，后者为有限原子空间 | 分母盲区和 belief–coverage 分离已有；四层方法还需概率校准与 web 选择偏差验证 |
| InfoReasoner、IGPO、IG-Search、SIGHT、TEPO、IGRPO | gold-answer、语义答案或 rollout | 训练 | 学习后间接控制 | 否 | IG/entropy 训练奖励已有 |
| ECHO、TRACE、SIOP | 显式后验、gold-answer readiness 或自生成 outcome modes | turn-level RL credit | 是 | 否 | epistemic/potential/TD turn credit 已有 |
| LOTAPO、STAMP、RICE-PO、CVT-RL | 删除 attribution、证据 provenance、同状态局部分支或验证后的干预效应 | step/turn credit | 是 | 通常否 | attribution 与 causal baseline 已形成，裸 entropy 不够 |
| CIGPO、Bridge Evidence、CHILL-Harness | gold-conditioned contextual IG、证据 omission suffix replay、workflow intervention advantage | 训练 credit、离线归因、在线 harness 授权 | 是 | 否 | IG credit、bridge-step utility 与干预式 orchestration 均已有；新增方法必须证明四层开放世界变量和官方任务损失的额外价值 |
| HiMPO、WikiLoop、ConMem | 同状态 memory recoverability；冻结消费者下的 guarded before/after utility；coalition-based Shapley memory value | memory/knowledge-write credit 与 retention | 学习后间接控制 | 否 | 局部写入 credit、downstream guard 与 contribution-ranked retention 已有；OWIC 的差异只能来自开放世界四层任务风险、bridge-step、provenance 与终局 continuation |
| InfoPO、AEM、SELAUR、STRIDE、APPO、PivoARL | masked-feedback counterfactual、response entropy、uncertainty reward、outcome-discriminative pattern、pivotal retry | turn/token/response credit 与局部重试 | 是 | 否 | 信息信号与结果门控、反事实或 pivotal state 的组合也已有；四层任务变量才可能构成差异 |
| A²TGPO、T²PO | gold-answer IG 与 token/turn uncertainty dynamics | credit/clipping、intervention/resampling | 是 | 否 | IG/uncertainty 控制训练与探索已有；label-blind 分层 task risk 才可能构成差异 |
| AREX | verified/unresolved constraints、结构化 confidence、context update | 递归 refine/restart 与训练 | 是 | 否 | 约束级 follow-up、状态压缩与 key-step bonus 已有 |
| Harness-G | evidence/entity/answer 菜单、evidence equivalence、dependency graph | 推理接口与非近视 credit | 是 | 否 | 查询等价坍缩与结构化非近视 credit 已有；必须纳入强基线 |
| Baikal | semantic regions 与 finding-quality posterior | 区域 bandit 调度 | 是 | 区域覆盖，但不估计未知结果集质量 | semantic-region coverage、$\epsilon$-greedy 与 UCB 已有 |
| Search as Computation Allocation | terminal decision/loss、computation topology 与 observation kernel | metareasoning、VOC、knowledge gradient | 是 | 依赖问题定义 | IG 只在 log loss 下等于 myopic VOC；主目标必须改为 terminal-loss VOC |
| SearchArt、CAST、AttriMem | 终局 outcome、过程约束、solver state value、answer attribution | 训练与 turn/operation credit | 学习后控制 | 否 | 可验证长程训练、state-value credit 与答案 attribution 已有；必须作为训练/credit 对照 |
| MisKnow-Agent、FinanceHarness | 误导证据采用、lifecycle、PIT corpus 与工具契约 | reliability injection、时间隔离、rubric | 评测/训练 | 固定 corpus | truthfulness、时间污染与 tool shift 必须单列，不能被 entropy/coverage 指标吸收 |
| TaS、A-MapReduce、Web2BigTable、VecTree-RAG | 行、格、横向子任务；语料与文档结构 | 推理系统 | 是 | 启发式或固定语料覆盖 | 表格状态、大规模宽搜与两级结构检索已有 |
| WebSwarm、SearchOS | 搜索节点、网页结构、coverage/gaps | 推理系统 | 是 | 定性 open-set / scope audit | 动态 deep/wide 与覆盖驱动调度已有 |
| Good–Turing、coverage、capture–recapture | 未见事件质量/种类数 | 统计估计 | 不直接 | 是 | 提供 width posterior，但需处理搜索偏差 |

### 7.1 不能声称

- 首次把熵或信息增益用于搜索代理、RAG、工具调用、证据选择或停止。
- 首次用 entropy reduction、posterior contraction 或 gold-answer likelihood 给 turn/tool step 分配 credit。
- 首次提出 epistemic credit、belief-conditioned turn reward、leave-one-turn attribution 或 evidence provenance credit。
- 首次做 uncertainty-aware web agent、双层不确定性或动态 deep/wide routing。
- 首次用 semantic regions、UCB 或 $\epsilon$-greedy 平衡 deep-research coverage。
- 首次发现不同 query 收敛到相同 evidence set，或首次用结构化菜单做 non-myopic search credit。
- 首次用 verified/unresolved constraints 递归 follow-up、压缩研究状态或突出关键步骤训练。
- 首次用 gold-conditioned contextual IG 给 turn 分 credit，或首次用 omission replay/干预相对 advantage 给搜索步骤与 harness workflow 定价。
- 首次在同一 pre-write/pre-edit state 下按可恢复信息或 downstream utility 给 memory/knowledge 写入 credit，或首次加入 unrelated-query regression guard。
- 首次把表格、coverage map 或 evidence graph 作为搜索状态。
- 低熵等于正确、完整或有充分证据。
- Good–Turing/capture–recapture 在搜索引擎偏置下自动给出无偏全集估计。
- 控制器“理论最优”，除非明确证明观测模型、校准、损失和 adaptive-submodularity 条件。

### 7.2 可辩护的候选创新

若论文只做推理时控制，建议改为：

> **Risk-DeepWide: Calibrated Value of Computation for Open-World Deep-and-Wide Search**

若加入训练时 credit assignment，更准确的候选名是：

> **OWIC-DeepWide: Open-World Information Credit for Deep-and-Wide Search**

候选贡献不是使用熵，而是七个必须联合成立的设计：

1. **DeepWide 特有的分层随机变量。** $A$：隐藏 anchor；$M$：未见质量/剩余集合；$R_e$：候选行资格；$Y_{e,c}$：单元格语义值。
2. **开放世界 width。** 将有限候选 anchor/row 分布与 OTHER/unseen-mass posterior 联合，避免低已知行熵造成假完整。
3. **风险与成本耦合。** 动作按期望任务损失下降/成本路由，而不是把所有 entropy bit 等价相加。
4. **校准与可否证验证。** 分别证明各信号能预测 anchor、遗漏、行和格错误，并在同动作空间、同预算下优于 heuristic uncertainty；否则放弃 entropy-controller 的主张。
5. **credit 不等于熵差。** 训练时用 task-risk/proper-score change 确定方向，用同状态 counterfactual 检查任务贡献，用 provenance 区分发现、验证和综合。
6. **证据等价感知。** 对 query intent、URL/claim set 与 source dependency 做等价类聚合；只返回已有证据类的动作不给 discovery credit，并与 Harness-G 的菜单/SNC 做比较。[81]
7. **风险条件化的区域组合。** 以 Baikal 式 semantic region 作为动作先验，再由 anchor/coverage/row/cell 风险分配区域与搜索模式；与 random region、LLM policy、Bayes-UCB 和不分区 controller 做同预算比较。[82]

检索到的文献中，没有一篇同时满足以上七点。但这只是截至检索日的**候选空白**；Forage V2 的 denominator audit、Shared Discovery Paradox 的 belief–coverage 分离、SearchOS 的 scope audit、ECR 的有限假设 EER、C-IP 的校准、CuriosiTree 的 EIG/cost、Search as Computation Allocation 的 terminal-loss VOC、AREX 的递归约束核对、Harness-G 的 evidence-equivalence/SNC、Baikal 的区域 bandit、CAST 的 state-value credit、AttriMem 的答案 attribution、ECHO 的 epistemic credit、HiMPO 的同状态 memory credit、WikiLoop 的 guarded downstream edit utility、STAMP 的 provenance 和 CVT-RL 的反事实贡献已覆盖各个相邻部分。论文必须正面比较这些近邻，不能靠改名构造差异。

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

口头置信还必须经过 allocation-level 检查。除了全局 AUROC/ECE，报告被 controller 实际选择的低置信 tail 中错误率、不同预算下的 calibration、跨 branch 的错误相关矩阵，以及按 source/evidence equivalence 去重后的有效样本数。若置信近乎常数或相关失败使有效样本远少于名义 agent 数，router 应退化到预注册的随机/轮转或相关性-aware baseline，而不是继续用任意 tie-break 制造“自适应”外观。[105,107]

### 9.2 controller 是否真的由信号获益

所有 controller 比较必须共享模型、搜索/浏览工具、动作集合、最大 token、tool call、wall-clock 和重试次数。必须包含：当前 retrieve-then-generate、fixed wide→deep、fixed deep→wide、TaS/no-entropy planner、fixed evidence-sufficiency termination、ScaffoldAgent-style composite-utility outline control、相同 controller 加 heuristic uncertainty、pure RelIG/EIG、myopic task-risk VOC、learned dynamic-VOC approximation、oracle one-step value（仅分析）、WebSwarm/SearchOS/A-MapReduce 系统级比较，以及 Harness-G 式 evidence-equivalence/menu、Baikal 式 random/Bayes-UCB region policy 和 VecTree-RAG 式 `global route → document tree → page read`。credit 实验另含 AREX key-step bonus、SNC、CAST-style learned value delta、AttriMem-style answer attribution、HiMPO-style memory recoverability、WikiLoop-style guarded paired utility 与 ConMem-style pruned Shapley memory valuation。只和 ReAct 比不够。

若 controller 生成额外 probe、critique、verification、sibling message 或候选计划，预算必须计入所有输入/输出 token、search/fetch、串行深度和实际 wall-clock。WebSwarm/MANTA 式协作还要加入等生成 token 的独立搜索采样与去重聚合曲线；开放式表格不能直接多数投票，因此 aggregation rule 必须在结果前冻结。每个 adaptive 方法都报告 branch-trigger/round-engagement rate，防止因自评始终为“完成”而静默退化成更便宜的单调用方法。[104–106]

并发报告必须区分三个量。`executor_concurrency` 是同时运行多少道独立题，只影响吞吐和端口压力；`agent_width` 是同一道题同时展开多少分支，是待检验的协作机制；`effective_evidence_width` 则在 query intent、URL/content、source dependency 与 evidence-set equivalence 去重后计算。只有后两者可能改变单题信息覆盖，且名义 agent 数不能替代有效证据宽度。跨题档位由中性容量阶梯冻结，单题 width 需要同总预算消融。

### 9.3 低熵错收敛

构造或标注四类诊断集：真 anchor 不在初始 top-k、重复错误网页占多数、权威反证后到，以及一篇流畅直接断言与两条间接记录链冲突。检查 `OTHER`、hypothesis regeneration、complete-route reconciliation 与 falsification 是否能避免低熵错误停止。ECR 是有限假设对照，DRNOISE 是误导直接证据压力测试；后者的合成任务结果不能替代 live-web 验证。[145]

### 9.4 开放集遗漏

在已知完整列表、synthetic hide-and-seek 与真实开放列表上分别测试。搜索接口强偏置会破坏经典 unseen-species 假设，因此需要按 query/source family block bootstrap，并报告估计在语言、领域、时间敏感任务上的偏差。

### 9.5 评测污染与 judge 可靠性

Search-Time Contamination 研究把污染分成 BML、QCL 和 EAL。[35] BML 是 URL/metadata 风险信号，QCL 用题面与访问内容的最长连续公共子串衡量，严格 EAL 则要求原题长连续片段和对应 ground-truth answer 明确成对出现。该文没有给出可直接移植到 DeepWide 的 QCL 二元阈值，URL/repository 命中本身也不足以确认答案泄漏。运行时必须屏蔽 benchmark 名、instance id、gold/evaluation 路径；post-terminal scanner 只能在不读 gold 的条件下输出 BML/QCL/EAL candidate，再由隔离的人工或独立审计确认 EAL。官方 primary 仍保留 220 全分母，污染敏感子集只作附加分析。REFLECT 还报告深度研究 LLM judges 对细粒度失败的准确率不足 55%，尤其不擅长证据验证；因此官方 LLM judge 指标需配合分层人工抽检、双人复核和 judge disagreement 报告。[36]

### 9.6 credit assignment 是否定位了真正有贡献的步骤

信号评估不能只看训练后最终分数。应建立带干预的 step-credit audit set：对同一状态执行原动作、等成本 sibling、no-op、证据替换和反证动作，再用固定 continuation 估计最终任务风险差。对 evidence action 另做 Bridge Evidence 式 omission replay，固定干预前 prefix、从干预点重跑 suffix，并将终局 task delta、下一查询或后继动作的 enablement、额外 turn/token/tool cost 分开保存，再预注册是否以及怎样组合成 CTU-like scalar。[117] 对 memory/knowledge write 另存同一 pre-write/pre-edit state 下的旧/新状态，分别计算 HiMPO-style target recoverability、WikiLoop-style frozen-consumer utility、ConMem-style pruned Shapley value、unrelated-query regression 与 edit cost。[149,150,158] 报告 credit 与终局差值的 Spearman、signed accuracy、top-k pivotal-step recall 和 calibration，并单列以下诊断：无关但新奇信息、重复错误来源、先升熵后纠错、延迟显效、bridge evidence、多步骤协同、删除后 OOD、tool-error blame leakage 与 persistent-write drift。比较 raw entropy drop、semantic entropy drop、CIGPO/gold log-score gain、TRACE-style TD、LOTAPO、STAMP、RICE-PO、HiMPO、WikiLoop、ConMem、CTU、CVT-RL-style counterfactual、CHILL-style intervention advantage 和 OWIC。[117–119,149,150,158] 若 OWIC 只与 entropy change、局部 recoverability 或 coalition ranking 相关，却不能预测干预后的 task value 或后续可达性，它不能称为 credit assignment 方法。

### 9.7 信息与任务价值是否错位

构造至少三类 state-matched case：高 IG 但低 terminal-loss reduction、低 IG 但高 regret reduction，以及 myopic value 为零但能开启高价值 descendant computation。比较 RelIG、myopic VOC、learned dynamic VOC 与 oracle rollout value 的排序、top-1 regret 和 calibration。若 pure IG 与 task value 的排序差异没有在真实轨迹或构造反例上复现，论文只能将 VOC 作为理论动机；若复现，则 controller 的主消融必须报告差异来自 terminal loss，而不是换了更多 features。

### 9.8 误导证据、时间污染与工具漂移

对不含 benchmark label/gold 的审计集注入语义相关但受控错误的来源，改变 source dependency、authority-like presentation 和进入 research state 的阶段，并测 false-claim adoption、完整证据链率、四层 risk calibration 与独立验证召回。DRNOISE-style paired clean/noisy 条件还要区分 retrieval miss、truth found but incomplete route、complete-route override 与 reconciliation failure，避免把所有采用错误直接断言都归因于检索。[145] 另做 point-in-time 或固定 snapshot 复现实验，记录知识快照、页面清洗与切块、索引字节、检索/融合后端、tool schema、observation truncation、提交规则和搜索截止时间的环境指纹。SimpleWikiSearch 说明这些变量本身足以改变 agentic-search 结果；任何只在 live web、合成语料、单一 snapshot 或单一后端成立的增益都必须标为环境依赖结果。[87,88,145,148]

### 9.9 自适应机制是否真实执行、且是否优于简单算力分配

对每个名义 adaptive 系统报告实际执行路径。至少记录各 route 的触发频率、每题 agent/round 分布、提前停止中的错误比例、曾出现正确中间态但最终被覆盖的比例，以及按 query、URL/content、evidence set 和 source dependency 修正后的有效独立分支数。主对照加入相同生成 token 的独立搜索样本、DivInit-style first-turn diverse seeds、相同 tool-call 的随机 region/agent allocation 和相同 wall-clock 上限的并行采样。[143] 另加 SwarmResearch-style depth-varying allocation，与相同 worker iteration、总 token、工具调用和 orchestrator 开销的最佳固定 width×depth 比较；它在代码优化上的 4/5 结果只用于预注册该对照，不构成 DeepWide 方向先验。[147] 层级系统还要独立扫描 delegation/planner 与 execution/child 的模型容量，不能默认所有角色使用同一模型最优；Think Big, Search Small 的摘要结果提示容量敏感性可能集中在 delegation，但这一结论仍需在 DeepWide 上按同预算重测。[120] 在线控制采用两段式决策：先按预期 task/resource advantage 排序候选 workflow，再以独立 margin 决定是否替换 factual workflow，防止“best candidate”在所有候选均有害时仍被执行。[119] 若 adaptive 组件很少触发，或其质量–成本点不超过简单采样 Pareto 前沿，结果只能支持“系统可运行”，不能支持 controller 或 swarm 机制有效。[104–109,119,120,143,147]

## 10. 对当前项目的直接诊断

当前 production forward 的已发布基线仍是可恢复 staged runtime，完整 Risk-DeepWide/OWIC-DeepWide 尚未产生质量结果。控制面已推进到 V2.42.20；V2.42.19/20 都只是 post-terminal audit，不改变 V2.42.18 的 forward bytes。V2.42.11 把纯 entropy/VOC kernel 接到三个冻结决策 context 和九个 context–action 组合；action 分支执行真实的两查询 observation、V2.41.22 provenance-preserving state adapter 与有界幂等 restart，stop/abstain 则只写双层 sealed receipt。runtime 构造只接收已绑定的模型、job manifest 和 selected-parent manifest，不读取环境变量、benchmark label 或 evaluator artifact；未发布 package 仍 fail closed。

V2.42.12 publisher 覆盖 18 个 entropy 决策和 14 个唯一 parent byte graph，并为目标 schema 87–100 生成独立 rebase 合同。首次 activation 因 successor 错用了 V2.42.10 的 frozen-false 字段名而 fail closed；它没有打开 selected work order/report/model，没有创建 publication/candidate，没有取得 lease，也没有调用模型、搜索或 evaluator。失败 activation/state 已封存且禁止原协议 restart。V2.42.13 只修正这一字段名，并在新的 protocol、activation、state、publication 与 candidate namespace 中恢复。V2.42.15–17 又依次冻结 joint-package recovery、fresh paired dev64 gate 和 neutral capacity successor。V2.42.18 已冻结并激活唯一 single-owner exact-220 executor，但仍停在 `waiting_for_v24216_package_gate_terminal`。其 execution-start、四个 fresh roots、lease、preflight、forward、mapping/evaluator 和 result 均未出现。

V2.42.19 又冻结了 post-terminal、label-blind contamination scanner。其 protocol/decision/12-file manifest SHA 为 `d7923f65…e0a61 / c5dcbea7…c0c4 / 4784cb91…5737`，activation/wait-audit SHA 为 `3355de78…a8759 / 38f2d222…fbeaa`。watcher PID `3141508` 当前只读 V2.42.18 的 preterminal safe envelope，未打开 task manifest/evidence，未创建 detail/report，也没有 lease、网络、模型、搜索或 evaluator 调用。它扫描的是 runtime 持久化的 query-focused page evidence，不是未保存的整页原文，因此不能证明网页未留存部分不存在污染。这条供应链证明实现边界可审计，不证明 calibration、controller quality、credit validity、污染率或 benchmark 提升。

V2.42.20 在 V2.42.19 之后冻结来源依赖审计。其 protocol/decision/12-file manifest SHA 为 `7297cd10…a6555 / 63e11c55…53290 / 0402f617…7bf7`，activation/wait-audit SHA 为 `cb3dbdc9…744c / e5c5f8c8…fb40`。watcher PID/start ticks `3216528/748157819` 当前只读 V2.42.19 的 preterminal envelope；task evidence、detail/report、网络/API、lease、forward 与分数路径均未打开。该实现把 exact/near-duplicate 和强镜像连成硬簇，对同源、共享 quote、结构化记录与路径镜像另做软折扣；同 host 本身不触发硬合并。它只能给出 dependency-adjusted sensitivity，不能证明页面来源真的独立或支持答案，也不会从官方主分数中删题。

production runtime 只读取 `{opaque_id, question}`，支持 Tavily、Azure hosted 和 Anthropic hosted search、持久 JSON state、开放集 anchor/`OTHER`、scope/candidate discovery、mention recall、逐行/逐格查询、cell-level provenance、行级 quarantine、单位尺度审计和确定性表格渲染。尚缺的关键证据不是更多 controller 代码，而是真实 development calibration bundle、same-state/equal-cost intervention 数据、双父终态选择、joint package regression、dev64 package gate 和 fresh exact-220 结果。开放集合仍只有未校准 proxy，训练时 credit 与 RL pilot 也尚未开始。

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

泄漏审计发现旧 smoke 脚本曾把生成与本地近似 gold evaluation 放在同一进程。新 runtime manifest 已限制为 `{opaque_id, question}`，预测完成后再由独立 evaluator 读取 instance ID、subset label 和 gold table；测试覆盖 manifest 边界、anchor replay provenance、identity support、闭合行域防伪、通用 verifier、Tavily key 轮换、历史迁移版本、evidence continuity、checkpoint drift、evaluator retry、targeted no-op 和并发故障 trace。V2.42.19 另有冻结前 `21/21` 与 post-freeze 可重放 `20/20`，覆盖 CJK/英文连续片段、相似题误报、query 排除、preterminal refusal、symlink/tamper 与 create-exclusive。本地免 key GPT-5.6 proxy 与 Anthropic server-side search 在 V2.26 preflight 均 2/2 成功；正式 run 的 109 次模型调用与 118 次 attempts 也全部完成。Azure hosted search 历史偶发 429。正式投稿仍需等待 V2.42.19 的 exact-220 报告，人工确认 EAL candidates，并补整页 capture/精确 span、跨进程文件权限与未持久化页面盲区审计。

## 11. 结论

信息熵适合作为这项工作的理论主线，但不能作为孤立 novelty。已有文献已经覆盖语义熵、信息增益奖励、EIG 动作选择、熵驱动证据选择、校准停止、显式证据充分性停止、复合 utility 驱动的 outline 调整、表格状态、动态深宽搜索、可训练委派与 delegation-as-context-management、冻结 agent 外的可学习 context manager、经验证与回滚的异步 speculative retrieval、全局排名后 agent refinement、两级结构检索、未知 denominator 审计、belief–coverage 分离、semantic-region bandit、evidence-equivalence control、attention-entropy chunk 去重、entropy-gated belief communication、POMDP/predicate belief、检索边界反思、gold-conditioned contextual-IG credit、answer-graph step credit、同状态 memory recoverability、guarded downstream edit utility、Shapley-style memory valuation、evidence omission suffix replay，以及 intervention-relative harness authorization。可辩护的新问题只剩下：DeepWide 的隐藏 anchor、开放集合遗漏、行资格和格值能否形成一个经校准且不简单相加的任务风险模型；该模型能否在相同动作菜单、区域、预算、证据等价与来源依赖约束下改善完整 all-220；若进一步训练策略，分层风险变化能否在同状态终局 continuation、bridge-step enablement、负迁移 guard 与 provenance 下定位真正改善最终任务的步骤。[149–151,157–172]

新的 `plan.md` 因此采用证据门控顺序：先完成当前 frozen R1 与独立评测，再让 search/Gate-2A 父链自然终态；只有 V2.42.13 发布 selected entropy component、V2.42.15 joint package 和 V2.42.16 paired dev64 package gate 全部通过，V2.42.17 才能在两次 quiet observation 与唯一 lease 后执行中性容量阶梯。容量 freeze 后，已经激活的 V2.42.18 是唯一可执行 fresh exact-220 的 owner，不再创建第二份 activation。V2.42.19/20 只在该结果封印后依次做污染与来源依赖审计。V2.42.11–20 已使 controller runtime、发布边界、package gate、容量接力、全集 executor 与 post-terminal audit 可执行，但真实 calibration、同状态 action-value/credit 数据、污染率、依赖校正结果与线上收益仍为空。若 anchor/coverage/row/cell signal 不能校准，若 step score 不能预测 counterfactual task contribution，或同动作空间下不超过 fixed evidence sufficiency、CACD-style content dedup 和 composite-utility outline control 的任务风险–成本 Pareto，则“熵作为核心创新”应降级为诊断工具。

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
76. Lu, S. et al. **AREX: Towards a Recursively Self-Improving Agent for Deep Research.** arXiv:2607.21461v2 (2026). https://arxiv.org/abs/2607.21461
77. Yao, X. et al. **Delegation Intelligence in Deep Search: A Controllable Framework for Disentangled Capability Diagnosis.** arXiv:2607.23524 (2026). https://arxiv.org/abs/2607.23524
78. Ma, X. et al. **EviBack: Search-Agent Reinforcement Learning via Evidence-Constrained Teacher Backoff.** arXiv:2607.23955v2 (2026). https://arxiv.org/abs/2607.23955
79. Li, J. et al. **A New Role for Relevance: Guiding Corpus Interaction in Agentic Search.** arXiv:2607.24223 (2026). https://arxiv.org/abs/2607.24223
80. Zhou, S. et al. **Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability.** arXiv:2607.26637 (2026). https://arxiv.org/abs/2607.26637
81. Hou, Y. et al. **Harness-G: A Graph-Structured Harness for Search Agents.** arXiv:2607.27652 (2026). https://arxiv.org/abs/2607.27652
82. Agarwal, D. et al. **Baikal: Structured Search for Deep Research over Data Lakes.** arXiv:2607.27726 (2026). https://arxiv.org/abs/2607.27726
83. Tuisov, A. **Search as Computation Allocation.** arXiv:2607.27871 (2026). https://arxiv.org/abs/2607.27871
84. Mei, L. et al. **SearchArt: Training Long-Horizon Search Agent with Scalable Synthetic and Verified Task.** arXiv:2607.24850 (2026). https://arxiv.org/abs/2607.24850
85. Wang, Y. et al. **CAST: Game Solvers as Turn-Level Teachers for LLM Agents.** arXiv:2607.25308 (2026). https://arxiv.org/abs/2607.25308
86. Li, Q. et al. **AttriMem: Attribution-Guided Process Feedback for Agent Memory Learning.** arXiv:2607.21106 (2026). https://arxiv.org/abs/2607.21106
87. Zhu, P. et al. **Is Deep Research Reliable? Misleading Knowledge Induces False Conclusions.** arXiv:2607.20891v2 (2026). https://arxiv.org/abs/2607.20891
88. Xiao, Y. et al. **FinanceHarness: Autonomous Financial Deep Research Framework.** arXiv:2607.27853 (2026). https://arxiv.org/abs/2607.27853
89. Sun, Y. et al. **HiEviDR-Bench: A Benchmark for Hierarchical Evidence Aggregation in Deep Research.** arXiv:2607.25151 (2026). https://arxiv.org/abs/2607.25151
90. Feng, Y., Zhang, Y., Cheng, Y. & Qi, W. **Scores Are Not Decisions: Cost-Aware Stopping for Tool Acquisition in LLM Agents.** arXiv:2607.27083 (2026). https://arxiv.org/abs/2607.27083
91. Prajapati, A. & Mohite, O. **Two Calls Beat Five Agents: Evaluating Multi-Agent Pipelines Against Self-Refinement for Local Language Models.** arXiv:2607.26922 (2026). https://arxiv.org/abs/2607.26922
92. Luo, J. **SKIMIX: Multi-Agent Harness-Time Scaling with Skill Mixture for Dynamic Harness Engineering.** arXiv:2607.27994 (2026). https://arxiv.org/abs/2607.27994
93. Huang, M.-X. et al. **MANTA: Multi-Agent Network Topology Adaptation for Self-Evolving Multi-Agent Systems.** arXiv:2607.28527 (2026). https://arxiv.org/abs/2607.28527
94. Yao, Z. et al. **SkillRise: Agentic Reinforcement Learning for Cross-Task Skill Evolution.** arXiv:2607.26784 (2026). https://arxiv.org/abs/2607.26784
95. Zheng, B. et al. **Group-Reflective Self-Distillation for Agentic Reinforcement Learning.** arXiv:2607.28076 (2026). https://arxiv.org/abs/2607.28076
96. Chitale, R. S. et al. **Test-Time Scaling via Error Localization.** arXiv:2607.21453v2 (2026). https://arxiv.org/abs/2607.21453
97. Xia, X. et al. **From Scoring to Acting: Outcome-Verified Comparative Self-Distillation for LLM Agents.** arXiv:2607.27937 (2026). https://arxiv.org/abs/2607.27937
98. He, Q., Wu, Z. & Wang, Z. **Not All Tokens Deserve Equal Credit: Counterfactual Sensitivity Credit Reallocation for Long-CoT Reasoning.** arXiv:2607.27888 (2026). https://arxiv.org/abs/2607.27888
99. Du, E. et al. **LEDGERMIND: Provenance-Constrained Multimodal Agentic Reasoning with a Structured Evidence Ledger.** arXiv:2607.28374 (2026). https://arxiv.org/abs/2607.28374
100. Shams, M. **LayerRAG-Bench: A Cross-Layer Reliability Benchmark for Agentic Retrieval-Augmented Generation.** arXiv:2607.27353 (2026). https://arxiv.org/abs/2607.27353
101. Xiong, H.-D. et al. **Thinking Under Uncertainty: Evidence Use and Information-Seeking in Language Models.** arXiv:2607.26845 (2026). https://arxiv.org/abs/2607.26845
102. Yan, B., Wolfe, G., Martiniani, S. & Cho, K. **AskChem: Claim-Centered Infrastructure for Chemistry Literature Synthesis.** arXiv:2607.28618 (2026). https://arxiv.org/abs/2607.28618
103. Aravanis, T. & Koutras, C. D. **Selective Credibility-Limited Belief Update.** arXiv:2607.28523 (2026). https://arxiv.org/abs/2607.28523
104. Mirzaei, I. **Sample More, Reflect Less: Self-Refine and Reflexion Lose to Repeated Sampling at Equal Token Cost, from 1.5B to 7B.** arXiv:2607.28576 (2026). https://arxiv.org/abs/2607.28576
105. Sah, C. K., Zhang, L. & Lian, X. **Beyond Self-Knowledge: Propagating Uncertainty Across Reasoning and Retrieval in LLMs.** arXiv:2607.25600v2 (2026). https://arxiv.org/abs/2607.25600
106. Chen, H., Lin, L. & Wang, G. **SVR: Self-Verifying Refinement via Joint Verdict-Confidence Reinforcement Learning for Adaptive Test-Time Compute.** arXiv:2607.28457 (2026). https://arxiv.org/abs/2607.28457
107. Zavattari, C., Tommasi, A. & Prencipe, G. **One Human, N Agents: Audit-Budget Allocation for LLM Agent Fleets under Miscalibrated, Correlated Confidence.** arXiv:2607.28317 (2026). https://arxiv.org/abs/2607.28317
108. Lee, W. & Choi, J. **Rethinking Inference-Time Scaling in Local Computer-Use Agents: Failure Modes and Compute Tradeoffs.** arXiv:2607.28573 (2026). https://arxiv.org/abs/2607.28573
109. Hong, X., Dong, P., Yu, X. & Jiang, B. **Tools Are Not Islands: Set-Level Tool Retrieval for LLM Agents via Query-Conditioned Hyperedge Prediction.** arXiv:2607.25718v2 (2026). https://arxiv.org/abs/2607.25718
110. Rao, J., Qiu, Y., Zhang, C., Song, C. & Zhao, R. **SciDataSailor: Deep Scientific Data Exploring.** arXiv:2607.28098 (2026). https://arxiv.org/abs/2607.28098
111. Wu, X. et al. **Contrastive Reinforced Policy Optimization via Privileged Self-Distillation.** arXiv:2607.28026 (2026). https://arxiv.org/abs/2607.28026
112. Xiong, F., Xue, L. & Lin, H. **Correcting What You Cannot See: Credit Assignment for Perception Distillation in Multimodal Reasoners.** arXiv:2607.28336 (2026). https://arxiv.org/abs/2607.28336
113. Xu, J., Liu, M., Zhang, J., Goldstein, T. & Huang, F. **$\beta$-OPSD: Deriving with Policy Optimization, Training with Self-Distillation.** arXiv:2607.28582 (2026). https://arxiv.org/abs/2607.28582
114. Sigillo, L. et al. **EMBL AI Librarian: Life-Sciences Knowledge Layer for AI Agents.** arXiv:2607.28229 (2026). https://arxiv.org/abs/2607.28229
115. Pan, Y. et al. **FORGE: Research-Trajectory Hijacking Attacks on Deep Research Agents.** arXiv:2607.04718 (2026). https://arxiv.org/abs/2607.04718
116. Leung, E., Lumer, E., Feld, C., Huber, A., Subbiah, V. K. & Paul, K. **Do You Need a Frontier Model as a Citation Verifier? Benchmarking Rubric LLMs for Deep-Research Source Attribution.** arXiv:2607.08700 (2026). https://arxiv.org/abs/2607.08700
117. Mukhopadhyay, D., Ghosh, U. K. & Chatterjee, S. **Bridge Evidence: Static Retrieval Utility Does Not Predict Causal Utility in Multi-Step Agentic Search.** arXiv:2607.15253 (2026). https://arxiv.org/abs/2607.15253
118. Dou, H. **CIGPO: Contextual Information-Gain Policy Optimization for Multi-Turn Evidence-Reading LLM Agents.** arXiv:2607.16244 (2026; first submitted 2026-06-26). https://arxiv.org/abs/2607.16244
119. Fu, J. et al. **CHILL-Harness: Counterfactual Harness Learning for Efficient Reasoning in Long-Horizon Agents.** arXiv:2607.25825 (2026). https://arxiv.org/abs/2607.25825
120. Cai, Q., Zhao, Y. & Li, X. **Think Big, Search Small: Where Capacity Matters in Hierarchical Search Agents?** arXiv:2607.07548 (2026). https://arxiv.org/abs/2607.07548
121. Liu, J. et al. **From Proprietary to Open-Source: Bridging the Distribution Gap via Multi-Agent Protocol Distillation in Agentic Search.** arXiv:2607.24280 (2026). https://arxiv.org/abs/2607.24280
122. Li, X. et al. **ACM: Agentic Context Management for Long Horizon Tasks.** arXiv:2607.23809 (2026). https://arxiv.org/abs/2607.23809
123. Wu, Z., Gao, J. & Yang, K. **Silent Failures in Multimodal Agentic Search: A Diagnostic Taxonomy and Cross-Judge Evaluation.** arXiv:2607.19793 (2026). https://arxiv.org/abs/2607.19793
124. Ren, Z. et al. **OrchBench: Evaluating Multi-Agent Orchestration Plans in Isolation via Deterministic Simulation.** arXiv:2607.25656 (2026). https://arxiv.org/abs/2607.25656
125. Lin, S. et al. **Before Agents Speak: Pre-hoc Failure Risk Inference in Multi-Agent Systems.** arXiv:2607.26836 (2026). https://arxiv.org/abs/2607.26836
126. Feng, P., Yang, S. & Poria, S. **$\Sigma$-Mem: An Online Reliability Memory for LLM-based Multi-Agent Systems.** arXiv:2607.27958 (2026). https://arxiv.org/abs/2607.27958
127. Dai, H. et al. **SafeFlow: Semantic Information-Flow Control for Blocking Malicious Propagation in Multi-Agent Systems.** arXiv:2607.25255v2 (2026). https://arxiv.org/abs/2607.25255
128. Paul, D. **Context Assembly as the Controlled Variable: A Control-Theoretic View of Harness Policies for Frozen LLM Agents.** arXiv:2607.25408 (2026). https://arxiv.org/abs/2607.25408
129. Ren, X. et al. **AgentRadio: Passive Awareness for Long-Horizon Multi-Agent Collaboration.** arXiv:2607.28430 (2026). https://arxiv.org/abs/2607.28430
130. Meng, Z., Zhao, Z. & Run, C. **AdaKP: Online Adaptive Knowledge-Point Selection for Reasoning-Oriented Reinforcement Learning.** arXiv:2607.24833 (2026). https://arxiv.org/abs/2607.24833
131. Li, C. et al. **TAPO: Transition-Aware Policy Optimization for LLM Agents.** arXiv:2607.27973 (2026). https://arxiv.org/abs/2607.27973
132. Wang, D. et al. **MARS-RA: Rank Aggregation for Credit Assignment via Multimodal Comparisons in Embodied Multi-Agent Cooperation.** arXiv:2607.27967 (2026). https://arxiv.org/abs/2607.27967
133. Ji, J. et al. **Speculate While You Reason: Teaching Agents to Predict Their Next Tool Call via Joint Agent-Speculator RL.** arXiv:2607.25816 (2026). https://arxiv.org/abs/2607.25816
134. Wang, P. et al. **BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms.** arXiv:2607.26497v2 (2026). https://arxiv.org/abs/2607.26497
135. HONOR Agentic Search Team et al. **MagicSelector: Joint Optimization for Agent Tool Selection via Counterfactual Decomposition and Progressive Reranking.** arXiv:2607.17751v2 (2026). https://arxiv.org/abs/2607.17751
136. Farzaneh, A. & Simeone, O. **Think Short, Defer Smart, Act, and Repeat: Calibrated Reasoning and Uncertainty-Aware Deferral for Edge LLM Agents.** arXiv:2607.26865 (2026). https://arxiv.org/abs/2607.26865
137. Sander, L. et al. **Scaling LLM-Driven Multi-Agent Systems: Design Principles and Architectural Scalability Analysis.** arXiv:2607.27942 (2026). https://arxiv.org/abs/2607.27942
138. Custers, B. & Aslansefat, K. **Runtime Uncertainty Monitoring for LLM-Based Multi-Agent Systems Using Bayesian Networks.** arXiv:2607.25877 (2026). https://arxiv.org/abs/2607.25877
139. Cha, S. et al. **Do Current Retrievers Cover All the Evidence? A Controlled Study of Conjunctive Cross-Page Retrieval.** arXiv:2607.24165v2 (2026). https://arxiv.org/abs/2607.24165
140. Ning, J. et al. **Auto Research for Materials: Auditable AI-Scientist Workflows with Held-Out Transfer.** arXiv:2607.17100v2 (2026). https://arxiv.org/abs/2607.17100
141. Dou, Y., Lian, S. & Li, S. **Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference.** arXiv:2607.25018v2 (2026). https://arxiv.org/abs/2607.25018
142. Wu, R. et al. **MemHarness: Memory Is Reconstructed, Not Replayed.** arXiv:2607.28272 (2026). https://arxiv.org/abs/2607.28272
143. Murali, S., Coelho, J., Ning, J., Magalhães, J., Martins, B. & Xiong, C. **Beyond Parallel Sampling: Diverse Query Initialization for Agentic Search.** arXiv:2606.17209 (2026). https://arxiv.org/abs/2606.17209
144. Lu, Y. et al. **Dr-DCI: Scaling Direct Corpus Interaction via Dynamic Workspace Expansion.** arXiv:2606.14885 (2026). https://arxiv.org/abs/2606.14885
145. Nie, J. et al. **DRNOISE: Benchmarking Deep Research Agents in Misleading Evidence Environments.** arXiv:2607.17291 (2026). https://arxiv.org/abs/2607.17291
146. Yang, F., Meng, R. & Wen, Y. **Why Does Feedback-Augmented Self-Distillation Fail to Improve Retrieval-Interleaved Search Agents?** arXiv:2607.17558 (2026). https://arxiv.org/abs/2607.17558
147. Virk, Y., Edds, Z., Xia, C. S. & Zhang, L. **SwarmResearch: Orchestrating Coding Agents for Open-Ended Discovery.** arXiv:2607.02807 (2026). https://arxiv.org/abs/2607.02807
148. Xiong, G. & Zhang, P. **SimpleWikiSearch: A Clean Offline Wikipedia Environment for Agentic Search.** arXiv:2607.26070 (2026). https://arxiv.org/abs/2607.26070
149. Yan, J. et al. **HiMPO: Hindsight-Informed Memory Policy Optimization for Less-Entangled Credit in Long-Horizon Agents.** arXiv:2606.16285 (2026). https://arxiv.org/abs/2606.16285
150. Ming, H., Li, F. & Que, W. **WikiLoop: Jointly Learning to Build and Navigate Agent-Native Wikis with Downstream Feedback.** arXiv:2607.26604 (2026). https://arxiv.org/abs/2607.26604
151. Zhong, X., Shi, Y., Wei, Y., Shen, C., Zhou, T. & Wu, Z. **VecTree-RAG: An Agentic Retrieval-Augmented Generation Framework Combining Vector and Tree Retrieval for Efficiency and Accuracy.** arXiv:2607.23006 (2026). https://arxiv.org/abs/2607.23006
152. Fan, M., Xu, S. & Yuan, M. **Focus Is All You Need: Adaptive Goal-aware Attention Orchestration for Multi-Agent Graph Systems.** arXiv:2607.23678 (2026). https://arxiv.org/abs/2607.23678
153. Wang, D. & Xu, A. **AlloBench: Measuring Online Tool Allocation Capability in LLM Agents.** arXiv:2607.23332 (2026). https://arxiv.org/abs/2607.23332
154. Guo, H. et al. **DREvo: Distilling Recalibrated Historical Experience for Harness Self-Evolution.** arXiv:2607.26722 (2026). https://arxiv.org/abs/2607.26722
155. Du, Y. et al. **Living-Harness Is an Interactive-Agent Evolver.** arXiv:2607.26598 (2026). https://arxiv.org/abs/2607.26598
156. Fan, J., Zhuo, J. & Zou, B. **RRM: Experience-Driven Reflective Retrieval Memory for Long-Horizon Multimodal Reasoning.** arXiv:2607.28156 (2026). https://arxiv.org/abs/2607.28156
157. Ning, P. et al. **SearchSwarm: Towards Delegation Intelligence in Agentic LLMs for Long-Horizon Deep Research.** arXiv:2606.09730v1 (2026). https://arxiv.org/abs/2606.09730
158. Liu, B. et al. **ConMem: Contribution-Aware Memory for Long-Horizon Manufacturing Inspection Logs.** arXiv:2607.28126v1 (2026). https://arxiv.org/abs/2607.28126
159. Choubey, P. K. et al. **Don't Stop Early: Scalable Enterprise Deep Research with Controlled Information Flow and Evidence-Aware Termination.** *Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 6: Industry Track)*, 1699–1713 (2026). https://doi.org/10.18653/v1/2026.acl-industry.116 (arXiv:2604.24978v1)
160. Yang, Z. et al. **ScaffoldAgent: Utility-Guided Dynamic Outline Optimization for Open-Ended Deep Research.** arXiv:2606.20122v1 (2026). https://arxiv.org/abs/2606.20122
161. Yi, L. et al. **Learning Agent-Compatible Context Management for Long-Horizon Tasks.** arXiv:2605.30785v1 (2026). https://arxiv.org/abs/2605.30785
162. Saberi, M., Rezaei, K. & Feizi, S. **SpecHop: Continuous Speculation for Accelerating Multi-Hop Retrieval Agents.** arXiv:2605.21965v1 (2026). https://arxiv.org/abs/2605.21965
163. Le Huy, P., Nguyen, N. H. & Dang, Q. V. **Cross-Attention Calibrated Deduplication for Retrieval-Augmented Generation System.** arXiv:2607.24332v1 (2026). https://arxiv.org/abs/2607.24332
164. Farr, D., Cruickshank, I., Starbird, K. & West, J. **The Cost of Consensus: Malignant Epistemic Herding and Adaptive Gating in Distributed Multi-Agent Search.** arXiv:2605.06988v1 (2026). https://arxiv.org/abs/2605.06988
165. Kausik, C., Swaminathan, A. & Kallus, N. **The Context Gathering Decision Process: A POMDP Framework for Agentic Search.** arXiv:2605.07042v1 (2026). https://arxiv.org/abs/2605.07042
166. Liu, Y. et al. **Beyond Trajectory Rewards: Step-level Credit Assignment for Agentic Search via Graph Modeling.** arXiv:2605.29697v1 (2026). https://arxiv.org/abs/2605.29697
167. Xie, Z. et al. **SlimSearcher: Training Efficiency-Aware Web Agents via Adaptive Reward Gating.** arXiv:2606.07074v1 (2026). https://arxiv.org/abs/2606.07074
168. Tang, Y. et al. **SAAS: Self-Aware Reinforcement Learning for Over-Search Mitigation in Agentic Search.** arXiv:2605.29796v3 (2026). https://arxiv.org/abs/2605.29796
169. Lee, Y., Yen, H., Ye, X. & Chen, D. **Agentic Aggregation for Parallel Scaling of Long-Horizon Agentic Tasks.** arXiv:2604.11753v1 (2026). https://arxiv.org/abs/2604.11753
170. Fan, H. et al. **LiveBrowseComp: Are Search Agents Searching, or Just Verifying What They Already Know?** arXiv:2605.28721v1 (2026). https://arxiv.org/abs/2605.28721
171. Xie, S. et al. **DeepWeb-Bench: A Deep Research Benchmark Demanding Massive Cross-Source Evidence and Long-Horizon Derivation.** arXiv:2605.21482v1 (2026). https://arxiv.org/abs/2605.21482
172. Zhang, S. et al. **R²-Searcher: Calibrating Retrieval and Reasoning Boundaries for Agentic Search.** arXiv:2606.28566v1 (2026). https://arxiv.org/abs/2606.28566
