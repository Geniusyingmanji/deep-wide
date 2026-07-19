# OWIC-DeepWide 研究与实施计划

> 版本：3.0
>
> 更新：2026-07-19
>
> 状态：**基线与文献审计已完成；controller 与 credit 方法尚未实现；下一阶段是信号和干预式 credit 可行性验证。**
>
> 负责人：待指定（研究负责人、系统实现、实验/统计、人工标注至少明确一名 owner）

## 0. 决策摘要

若只完成推理时 controller，题目暂定为：

> **Entropy-DeepWide: Calibrated Hierarchical Belief Reduction for Open-World Deep-and-Wide Search**

若训练时 credit 通过独立门禁，题目升级为：

> **OWIC-DeepWide: Open-World Information Credit for Deep-and-Wide Search**

中心假设不是“熵可以用于搜索”或“熵降越大 credit 越高”，而是两个需要分开验证的命题：

> DeepWide 的错误来自四个相互依赖、但损失结构不同的信念层：隐藏核心实体 $A$、未见实体质量/剩余集合 $M$、候选行资格 $R_e$、单元格语义值 $Y_{e,c}$。若这些信念可被校准，则按单位成本的期望任务风险下降路由 `resolve_anchor / discover / test_row / fill / falsify / audit / stop`，可能比固定流程、主观 planner 和相同动作空间的 heuristic controller 更有效。

> 对训练时 credit，四层任务风险变化提供方向，task-relevant information gain 提供 epistemic progress，同状态干预估计贡献，evidence provenance 区分发现、验证与综合。只有同时通过结果对齐和干预验证的信息信号，才获得正 credit。

两个命题共享 belief/evidence 基础设施，但证据不能互相替代。controller 提分不能证明 credit 定位正确；credit 与干预贡献相关也不能证明在线路由更好。二者必须分别过 Gate 2A/3A 和 Gate 2B/3B。文献边界、直接近邻和 non-claims 见 [survey.md](survey.md)。

## 1. 当前真实进度

### 1.1 已完成

- Git 仓库、README、忽略规则与原方案 provenance 已建立。
- DeepWideSearch 公开 query JSONL 已纳入仓库；官方答案表与第三方仓库留在 `external/`，不提交。
- `scripts/run_deepwide_smoke.py` 已实现 GPT-5.5 + Tavily 基线：
  - 一次生成 6 个查询；
  - 每个查询取 Tavily answer/snippet；
  - `include_raw_content=False`，没有页面正文阅读；
  - 默认无 follow-up；
  - 最后一次性生成 Markdown 表格。
- `scripts/run_official_eval_local.py` 已把官方 evaluator 接到本地 Azure Responses judge。
- 已完成全量 220 题单次基线与官方评测。
- 已完成截至 2026-07-19 的文献综述和 novelty audit。

### 1.2 已验证的基线结果

可提交的聚合证据为 [`results/baseline_gpt55_20260623.json`](results/baseline_gpt55_20260623.json)；原始证据文件为 `outputs/deepwide_official_eval/full_gpt55_20260623_115822/summary.json` 与同目录 `official_eval_results.jsonl`。该历史 run 尚未做 search-time contamination 扫描，只能作为诊断基线；`outputs/` 被 Git 忽略，正式投稿前仍需冻结主实验 artifact。

| 切分 | N | SR | Core Entity Accuracy | Row F1 | Item F1 | Column F1 |
|---|---:|---:|---:|---:|---:|---:|
| 全量 | 220 | 2.27% (5/220) | 67.73% | 19.48% | 34.14% | 41.03% |
| Deep2Wide | 85 | 0.00% (0/85) | 44.71% | 4.89% | 11.69% | 15.75% |
| Wide2Deep | 135 | 3.70% (5/135) | 82.22% | 28.67% | 48.28% | 56.95% |

分组只在预测完成后按 benchmark `instance_id` 前缀离线计算；该字段未进入生成 prompt。结果支持“Deep2Wide 的 anchor/早期假设错误是当前优先瓶颈”，但**不证明 entropy 能解决该瓶颈**。

### 1.3 尚未实现

- 页面正文 reader 与精确 evidence span。
- runtime/evaluator 进程硬隔离。
- 持久表格、evidence graph、source dependency/dedup。
- anchor hypothesis set 与 `OTHER`。
- unseen-mass/coverage posterior。
- row eligibility 与 cell semantic belief。
- 校准器、EIG 或 task-risk estimator。
- 动态 controller、反证搜索和组合停止规则。
- step-credit estimator、同状态干预 runner、provenance credit 与 RL 训练。
- 与 WebSwarm、SearchOS、A-MapReduce、TaS 的可比实验。

因此，当前项目不可描述为“已经实现 U-DeepWide、Entropy-DeepWide 或 OWIC-DeepWide”。

## 2. 明确不主张什么

除非后续检索或实验证据改变，论文不得声称：

- 首次把 entropy、semantic entropy、information gain 或 EER 用于 RAG/搜索代理；
- 首次按 entropy reduction、posterior contraction 或 gold-answer likelihood 给 tool/turn 分配 credit；
- 首次提出 epistemic credit、belief-conditioned reward、leave-one-turn attribution 或 provenance-guided credit；
- 首次用不确定性控制工具调用、检索预算、证据选择或停止；
- 首次动态切换 deep/wide 搜索；
- 首次把 table、coverage map 或 evidence graph 作为搜索状态；
- 低熵意味着正确、证据充分或集合完整；
- Good–Turing/capture–recapture 在搜索引擎偏置下给出无偏全集估计；
- controller 理论最优或有 adaptive-submodular 保证，除非逐项验证假设并给出证明；
- SOTA，除非在相同 evaluator、模型/预算披露和强基线覆盖下成立。

允许的初始表述是：

> “我们研究 DeepWide 特有的分层开放世界信念，并检验校准后的期望任务风险下降能否改善搜索预算分配。”

credit 分支在 Gate 2B 之前只允许表述为：

> “我们检验四层任务风险、信息增益、反事实贡献和 evidence provenance 能否共同定位有用的 DeepWide 步骤。”

## 3. 研究问题与可否证假设

### RQ1：信号有效性

四层信念信号是否分别预测相应失败？

- $A$：anchor entropy/`OTHER` mass 是否预测核心实体错误？
- $M$：unseen-mass/coverage posterior 是否预测停止时漏行与剩余有效实体？
- $R_e$：row-eligibility uncertainty 是否预测误收/误删行？
- $Y_{e,c}$：cell semantic entropy 是否预测错误、无支持或冲突单元格？

**H1**：经过开发集校准的分层信号，在 held-out test 上优于 verbalized confidence、top-1 margin、support count、recent discovery yield、source count/diversity 和单一 LLM judge。

### RQ2：动作价值

预测的 EIG/task-risk reduction 是否与动作后的真实 loss reduction 相关？

**H2**：在共享候选动作的 counterfactual replay set 上，risk-reduction estimator 对最佳动作的 top-1/top-2 命中率与 Spearman 相关高于 heuristic utility，并在扣除成本后仍成立。

### RQ3：controller 效果

在完全相同的模型、工具、动作空间和预算下，分层控制器是否改善质量–成本 Pareto？

**H3**：推理时分层风险 controller 相对同动作空间 heuristic controller，在预注册主指标上达到统计上与实际意义上都非劣/更优的 Pareto 结果，而不是只比 fixed pipeline 好。

### RQ4：机制与边界

收益来自 anchor、unseen mass、row、cell 哪一层？是否只在 Deep2Wide、未知集合或高行数任务上成立？

**H4**：anchor 模块主要改善 Deep2Wide CE Accuracy；unseen-mass 模块主要改善 Row Recall/停止；cell 模块主要改善 Item Precision 和 risk–coverage。若不出现该机制对应关系，需警惕总体分数由别的系统改动造成。

### RQ5：epistemic signal 是否等于 task credit

步骤的 entropy/log-score 变化是否能预测从同一状态执行干预后的最终任务价值差？

**H5**：校准的四层 task-risk change 比 raw token entropy drop、semantic entropy drop 和 gold-answer log-prob gain 更准确地预测 signed counterfactual contribution；加入 evidence provenance 后，top-k pivotal-step recall 进一步提高。

### RQ6：credit 是否改善训练

在相同 rollout、终局 reward、训练 tokens 和 optimizer 下，OWIC advantage modulation 是否优于 outcome-only 与现有 turn-credit 基线？

**H6**：OWIC 相对 outcome-only GRPO 和最强可复现 turn-credit baseline，提高 held-out DeepWide 质量或降低达到同质量所需训练/推理成本；收益在移除 same-state contribution 或 provenance 后下降。

## 4. 方法定义

### 4.1 分层开放世界信念

时刻 (t) 的状态：

\[
B_t=\{p(A),\ p(M\mid \mathcal D_t),\ p(R_e),\ p(Y_{e,c})\}_{e,c}.
\]

#### Anchor $A$

- 从 $K_A$ 个独立、温度受控的 clue-solving samples 生成候选。
- 用双向 entailment + canonicalization 聚成语义类。
- 保留 `OTHER/unknown`，其质量由未解释线索、候选不一致、open-set detector 和新检索支持共同更新。
- 禁止只在 top-k 候选内归一化后宣称低熵。

#### 未见质量 $M$

- 输入：新实体 yield、singleton/doubleton、实体在 query/source/language/time family 的捕获矩阵、重复率、查询新颖性、权威全集来源是否存在。
- 候选估计器：Good–Turing coverage、Chao 型 lower bound、capture–recapture features、Bayesian count model、学习式 calibration layer。
- 输出至少包括：预测剩余有效行数区间、unseen probability mass、`Pr(row recall < target)`。
- 搜索结果不是 i.i.d.；估计器名称必须写成 “coverage-risk proxy/calibrated posterior”，除非偏置假设得到验证。

#### 行资格 $R_e$

- 对每个约束维护 support / contradict / unknown 命题与来源。
- 资格概率由约束层证据聚合，不由最终生成器一句话自评。
- 行状态：`candidate / eligible / ineligible / unresolved / duplicate`。

#### 单元格 $Y_{e,c}$

- 值候选按语义等价聚类；日期、数值、实体等使用类型化规范化。
- 明确 `unknown`、`not-found`、`conflicted`，不把缺失格强行归到某候选值。
- source independence、authority、recency 与 directness 进入 likelihood/reliability，镜像网页不得重复计票。

### 4.2 任务损失而非熵简单求和

\[
L(B_t)=w_A L_A+w_M L_M+\sum_e w_R L_{R_e}+\sum_{e,c}w_c L_{Y_{e,c}}+w_U L_{unsupported}.
\]

- $L_A$：anchor 错误风险；
- $L_M$：漏行/未见质量风险；
- $L_R$：行资格错误风险；
- $L_Y$：cell 错误风险；
- $L_{unsupported}$：输出无证据命题风险。

权重只在 dev 冻结。至少比较三种选择：benchmark metric sensitivity、均匀权重、通过 dev regression 学得的权重。若权重变化改变主结论，必须报告敏感性而不是挑最好设置。

### 4.3 动作空间

| 动作 | 主要目标信念 | 典型观测 |
|---|---|---|
| `resolve_anchor` | $A$ | 区分候选的线索、权威 bio、反证 |
| `regenerate_hypotheses` | $A$, `OTHER` | 新 anchor 候选 |
| `discover_entities` | $M$ | 新行、重捕获、全集来源 |
| `audit_scope` | $M$ | 预期总量、缺失分段、名单边界 |
| `test_row_constraint(e)` | $R_e$ | 约束支持/否定命题 |
| `fill_cell(e,c)` | $Y_{e,c}$ | 值与直接证据 span |
| `falsify_cell(e,c)` | $Y_{e,c}$ | 否定查询、冲突值 |
| `read_page(url)` | 多层 | 正文、结构化表、上下文 |
| `stop_or_abstain` | 全局 | 最终表与未决标记 |

### 4.4 控制目标

完整形式：

\[
a_t^*=\arg\max_a
\frac{\mathbb E[L(B_t)-L(B_{t+1})\mid a]}
{\mathbb E[C(a)]+\epsilon}.
\]

第一版允许用 Monte Carlo posterior samples + 小规模 action outcome model 估计。必须同时实现一个不含 entropy 的 heuristic controller，共享全部动作与 evidence pipeline：

```text
priority = missing_required_cell
         + recent_new_entity_yield
         + low_support_count
         + source_diversity_gap
         + fixed_cost_penalty
```

只有 Entropy/EIG controller 胜过这个 same-controller heuristic，才支持核心机制。

### 4.5 停止规则

正常停止要求同时满足：

1. `Pr(anchor wrong)` 与 anchor `OTHER` mass 低于 dev 阈值；
2. `Pr(row recall < target)` 低于阈值，并完成至少一次独立 scope audit；
3. 关键行/格风险低，或不确定格显式 abstain；
4. 所有非停止动作的 predicted loss reduction/cost 低于阈值；
5. 证据 provenance 完整且 calibration audit 通过。

预算耗尽是独立的 `forced_stop`，不能与 epistemic sufficiency 合并统计。

### 4.6 Credit 定义：信息量只负责 epistemic 部分

对第 $t$ 个动作同时记录以下信号，禁止把它们都命名为 information gain：

\[
\begin{aligned}
c_t^{H} &= H(B_t)-H(B_{t+1}),\\
c_t^{\log} &= \log p_{t+1}(z^*)-\log p_t(z^*),\\
c_t^{\mathrm{risk}} &= L(B_t)-L(B_{t+1}),\\
c_t^{\mathrm{cf},k} &=
\mathbb E_{\tau_{>t}\sim\mu}[V(h_t,a_t,\tau_{>t})-
V(h_t,g_k(a_t),\tau_{>t})].
\end{aligned}
\]

- $c_t^H$ 是实现后的熵差，可为负；它不是 expected information gain。
- $c_t^{\log}$ 需要训练真值，仅作 supervised credit baseline，禁止进入 label-blind inference。
- $c_t^{\mathrm{risk}}$ 以四层 proper score/task loss 判断方向；反证可以熵升而 risk 降。
- $c_t^{\mathrm{cf},k}$ 分别对 `no_op / equal_cost_sibling / semantic_substitution / evidence_substitution / tool_output_perturbation` 报告，不把不同干预平均后伪装成唯一因果效应。
- continuation policy $\mu$ 固定并记录版本。估计值只解释为相对于该干预和 $\mu$ 的贡献，不声称是未来任意 policy 下的 total causal effect。

第一版 OWIC 为：

\[
c_t^{\mathrm{OWIC}}=
c_t^{\mathrm{risk}}
+\lambda\operatorname{RelIG}_t
+\beta\widehat c_t^{\mathrm{cf}}
+\rho c_t^{\mathrm{prov}}
-\eta C_t.
\]

$\operatorname{RelIG}$ 只计算与 $A,M,R,Y$ 有关的信息，$c_t^{\mathrm{prov}}$ 区分 discovery、independent verification、contradiction resolution 和 synthesis。镜像来源先聚类，不能重复获 credit。

### 4.7 Advantage 注入与安全约束

第一阶段不端到端训练，先离线验证 credit。通过 Gate 2B 后比较两种注入：

1. **Potential shaping**：$\Phi(B)=-L(B)$，使用 $\gamma\Phi(B_{t+1})-\Phi(B_t)$，检查 telescoping 与 policy-invariance 条件。
2. **Sign-preserving modulation**：终局 advantage 决定主方向，OWIC 只在有界范围内放大正轨迹的高贡献步骤、减轻负轨迹中经反事实验证的有用步骤惩罚，参考 STAMP 的安全结构。

不得让 raw entropy bonus 覆盖 terminal task reward。所有 credit 需要 clipping、group normalization audit、effective-step ratio 和 reward-hacking 检查；若 credit 与终局方向冲突，保留原始值用于诊断，但训练是否采用由预注册 gate 决定。

## 5. 数据、隔离与污染控制

### 5.1 三段数据

现有 220 题已经完成过全量基线，研究者可访问 aggregate 与 per-instance 输出，因此它们不能再被描述为 benchmark-naïve test。立即执行以下分层：

- **开发集**：只用于信号设计、校准、阈值和 loss weights。
- **验证集**：只用于 go/no-go 与一次模型选择。
- **future-method holdout**：在任何方法实现前按 hash 锁定，后续不查看中间标签；它检验未来方法改动，但必须披露已存在历史基线暴露。
- **confirmatory set**：新建的私有/时间切片任务，或 benchmark organizer 的隐藏测试；这是最终强主张所需的真正未暴露集合。

若暂时无法获得 confirmatory set，主实验只能称为 public-benchmark held-out/exploratory evaluation，论文相应降低泛化主张。官方 220 题可在所有决策冻结后全量运行以便与文献比较，但用过的 dev/validation 样本不能重新包装成 confirmatory test。固定 split、seed、ids 与访问规则要提交 hash；不得按结果反复换 split。

### 5.2 严格 label-blind runtime

运行时 manifest 只含：

```json
{"opaque_id": "random_uuid", "question": "user-visible query"}
```

不得进入 runtime 的字段：

- `instance_id` 中的答案或方向后缀；
- `evaluation.required`、`unique_columns`；
- `topic`、`language`、Deep2Wide/Wide2Deep label；
- gold CSV、score、judge output、答案 key；
- 同一样本的历史正确性或从 evaluator 产生的 memory。

列名与输出语言必须从用户可见 question 解析。生成进程无权读取 gold root；evaluator 在预测文件关闭后由独立命令运行。新增自动化测试扫描 prompt、trace 和 runtime object，发现禁止字段即终止并将输出移到 `TAINTED_DO_NOT_USE/`。

### 5.3 Search-time contamination

- 查询生成时禁止 benchmark 名、arXiv 论文名、instance id 与原问题长字符串整段复制。
- 对返回 URL/正文扫描 GitHub、HuggingFace、benchmark repo、answer table 和问题文本高重合。
- 命中污染来源的样本保留审计记录但不计主结果；另报 contamination-sensitive analysis。
- 保存完整 URL、query、时间戳、页面 hash 与 evidence span，保证可追溯。

### 5.4 人工标注

从 dev/pilot 分层抽样至少 80 个状态，覆盖：正确/错误 anchor、早停/过搜、冲突 cell、中文/英文、Deep2Wide/Wide2Deep。两名标注员独立标注：

- 当前 top anchor 是否正确、真值是否在候选集；
- 还有无明显漏行/全集来源；
- row 资格；
- cell 是否正确、被支持、被矛盾；
- 下一动作的合理类别。

报告一致性与 adjudication。最终 test 的官方 LLM judge 再做分层人工抽检；考虑 REFLECT 的结果，不允许把单一 LLM judge 当作证据真实性 gold。

## 6. 实验设计

### 6.1 Phase A：基线与基础设施

先实现：

- `runtime/` 与 `evaluation/` 进程隔离；
- Page reader、HTML/PDF/text extraction；
- evidence schema：URL、title、timestamp、span、claim、source family、hash；
- persistent table/evidence state；
- token/tool/page/time/USD cost logger；
- deterministic normalization 与官方 evaluator adapter；
- no-leak tests。

基线至少复现 20 个固定任务两次，输出可逐步重放；若相同 seed/config 无法重放状态转换，不进入 Phase B。

### 6.2 Phase B：离线信号验证

在固定搜索轨迹上每一步保存信念特征，不让信号改变轨迹，避免 selection bias。标签来自最终 gold/人工证据审计。

#### Anchor 指标

- AUROC/AUPRC：anchor error；
- Brier、NLL、ECE；
- top-k coverage 与 `OTHER` recall；
- risk–coverage：按不确定性请求更多搜索/abstain。

#### Coverage 指标

- 预测剩余行数的 MAE、interval coverage；
- 预测 row recall 的 calibration error/Brier；
- premature stop rate；
- over-search calls after last useful discovery；
- hidden-entity mass rank correlation。

#### Row/Cell 指标

- incorrect、unsupported、contradicted 的 AUROC/AUPRC；
- Brier、NLL、ECE；
- selective precision/recall 与 risk–coverage；
- 按 source family、语言、日期/数值/实体列分层。

#### 必较信号

- semantic entropy；
- token/sequence entropy；
- top-1/top-2 margin；
- sample disagreement；
- verbalized confidence；
- calibrated logit margin；
- support/contradiction count；
- unique source count/diversity；
- recent yield、duplicate rate；
- Good–Turing/coverage/capture features；
- 组合模型与单一 LLM judge。

校准器（temperature/isotonic/Platt 等）只在 dev fit；在 validation/test 冻结。用 bootstrap 95% CI 报告 paired difference，不只报单点。

### 6.3 Phase C：动作价值数据集

从 30–50 个任务抽取关键状态，每个状态执行 3–6 个相同预算的候选动作，形成小规模 counterfactual action set。记录：

- action 前后四层 belief；
- gold task-loss change；
- 新证据/新实体/纠错；
- token、tool、page、time、USD；
- 是否出现冲突导致 entropy 上升但错误风险下降。

评测：gain regression MAE、Spearman、best-action accuracy、NDCG@k、regret、gain-per-cost calibration。若 estimator 只会预测“更贵动作 gain 更大”，必须做 cost residual 与等成本分层。

### 6.4 Phase C2：干预式 step-credit audit set

从 Phase C 状态中选择至少 300 个有效步骤，按 `anchor / discover / row-test / fill / falsify / verify / synthesize` 分层。每个步骤保存原始 history，并构造：

- `no_op`；
- 同动作类型、相同 token/tool 预算的 sibling；
- 语义保留但证据不同的 query/action；
- supporting evidence 替换、冲突 evidence 注入；
- tool output perturbation；
- LOTAPO-style `[DELETE]`，仅作 attribution baseline。

每个 intervention 至少用 3 个固定 continuation seeds；记录 intervention validity、state overlap、OOD rate、最终四层 loss、Item/Row/CE 变化和成本。credit baseline 至少包括：

1. raw token/segment entropy drop；
2. semantic entropy drop；
3. gold-class log-score gain；
4. IGPO / TRACE-style forward TD；
5. LOTAPO deletion；
6. STAMP first-exposure provenance；
7. RICE-PO local counterfactual；
8. CVT-RL-style fixed-continuation contribution；
9. OWIC full 与各组件。

主指标是 signed contribution accuracy、Spearman、top-20% pivotal-step recall、AUROC（有益/有害）、Brier/ECE 和单位 counterfactual rollout 成本。单列六类压力样本：无关新奇、重复错误、熵升纠错、延迟显效、两步协同、删除 OOD。

对人工标为“单步不可充分解释”的 discovery–verification 与 evidence–synthesis 对，额外估计

\[
I_{ij}=v(\{i,j\})-v(\{i\})-v(\{j\})+v(\varnothing).
\]

只有当 held-out 样本中显著正/负交互的比例超过 dev 预注册阈值时，下一阶段才加入 permutation-sampling Shapley；精确全轨迹 Shapley 不进入第一版预算。

### 6.5 Phase D1：在线 controller pilot

从 dev/validation 固定 50 题、两个随机 seed；future-method holdout 与 confirmatory set 不参与调参。比较：

1. 当前 6-query retrieve-then-generate；
2. fixed deep→wide；
3. fixed wide→deep；
4. TaS-style table planner，无 uncertainty；
5. same action space + heuristic controller；
6. same action space + entropy only；
7. full hierarchical risk/EIG controller；
8. ECR-style finite-hypothesis controller；
9. TASR-style answer-stability stopping。

只有 Phase D1 过门后才跑 controller 全量。

### 6.6 Phase D2：受控 credit-training pilot

只有 Gate 2B 通过才启动。先在 closed/replay web 环境训练小规模模型，避免 live-web 漂移与训练成本掩盖 credit 机制。所有方法共享初始化、rollouts、terminal reward、batch、optimizer、训练 tokens 和 tool corpus：

1. outcome-only GRPO；
2. uniform turn advantage；
3. TEPO/InfoReasoner-style entropy credit；
4. IGPO 或 TRACE-style gold-log-score credit；
5. STAMP provenance credit；
6. strongest feasible counterfactual baseline；
7. OWIC-risk only；
8. OWIC full；
9. OWIC 去 counterfactual / 去 provenance / 去 unseen mass。

先用 1.5B–4B backbone、固定 20–30K train trajectories、3 seeds 做 pilot。主比较是 OWIC full vs 同训练预算下最强 credit baseline，不允许只和 outcome-only 比。除 held-out task metrics 外，报告训练 sample efficiency、gradient/advantage variance、credit sparsity、effective-step ratio、KL、OOD intervention rate 和 reward hacking。

### 6.7 Phase E：主实验与系统比较

先在锁定的 future-method holdout 运行一次主实验；若可获得，再在 confirmatory set 复核。所有决策冻结后可运行完整 DeepWideSearch 作为 literature-comparability result，并明确其中含已用于 dev/validation 的样本。分别报告 Deep2Wide、Wide2Deep、语言与行数 bins。系统级外部比较至少讨论/复现可用版本：

- Table-as-Search；
- A-MapReduce；
- Web2BigTable；
- WebSwarm；
- SearchOS。

优先在相同骨干、search/page tools、并发、max tool calls、token、wall-clock、attempts 下运行。若官方系统无法复现，分成：

- **controlled internal baselines**：支持因果机制比较；
- **reported external systems**：只提供背景，明确模型/预算不一致，不排序宣称 SOTA。

## 7. 指标与统计

### 7.1 预注册主指标

- **质量**：Item F1、Row F1、Core Entity Accuracy；SR 为严格辅助指标。
- **成本**：search calls、page reads、总 tokens、wall-clock、USD。
- **主效应**：同预算下 Item F1/Row F1 paired difference，以及 quality–cost Pareto hypervolume。

Column F1 易被格式/列解析影响，保留但不作为唯一主指标。

### 7.2 次要指标

- Row Precision/Recall、Item Precision/Recall、SR/Pass@N；
- unsupported/contradicted cell rate；
- evidence coverage 与 citation precision；
- forced-stop、premature-stop、over-search rate；
- anchor recovery after initial miss；
- new valid rows per 1k tokens。

credit 分支另报：signed contribution accuracy、pivotal-step recall、credit calibration、intervention validity/OOD、credit compute overhead、训练 sample efficiency 与 gradient variance。最终任务分数仍是主结果，credit proxy 不能替代它。

### 7.3 统计方案

- 所有内部方法对同一任务、seed、预算配对；
- task-level stratified bootstrap 95% CI；
- 多 seed 报均值、标准差和 task-paired distribution；
- 主比较预先限定为 full vs heuristic controller，避免多重比较挑结果；
- credit 主比较预先限定为 OWIC full vs 最强同预算 credit baseline；controller 与 credit 分支分别校正，不混成一个 family；
- 次要 pairwise tests 做 Holm correction；
- 同时报 effect size 与原始分数，不只报显著性。

### 7.4 Pareto 判定

分别画：

- Item F1 / Row F1 / CE Accuracy vs tokens；
- Item F1 / Row F1 vs tool calls、wall-clock、USD；
- calibration/risk vs retained coverage；
- quality vs predicted/actual loss reduction。

如果 full controller 质量略高但被 heuristic controller 在所有成本上支配，H3 判失败。

## 8. 强制消融与压力测试

### 8.1 组件消融

- 无 anchor `OTHER`；
- 无 unseen-mass，仅 recent yield；
- 无 row eligibility belief；
- 无 cell semantic clustering；
- 无 calibration；
- 无 falsification；
- 无 source-dependency correction；
- Shannon entropy 直接加权和 vs task-loss reduction；
- EIG vs myopic observed entropy drop；
- 无 cost normalization；
- 单一停止阈值 vs 四道停止门。

### 8.2 诊断压力测试

- 真 anchor 不在初始 top-k；
- 多数网页复制同一个错误值；
- 后到权威反证；
- 低已知行 entropy、高 singleton rate；
- 已知完整名单 vs 真开放集合；
- 搜索引擎/语言切换；
- 动态网页与时间窗口；
- 工具失败、页面不可达、成本突增；
- entropy 暂时上升但最终纠错的轨迹。

### 8.3 搜索偏置敏感性

对 coverage estimator 分别用：

- raw result frequency；
- URL-domain dedup；
- source-family block；
- query-family block；
- language/time block；
- block bootstrap。

若估计仅在把镜像当独立样本时成立，判定为伪信号。

### 8.4 Credit 专项消融与反例

- raw entropy drop vs task-risk change；
- expected IG vs realized entropy change vs Bayesian surprise；
- gold log-score vs label-free semantic potential；
- 无 `OTHER` / unseen mass；
- 不做 same-state branching、改为同 turn-index 比较；
- fixed continuation vs current/evolving continuation；
- deletion vs equal-cost sibling vs evidence substitution；
- first exposure only vs discovery + verification + synthesis provenance；
- additive reward vs potential shaping vs sign-preserving modulation；
- 单步 credit vs pairwise interaction credit（选取高协同子集）；
- 无 outcome gate、无 intervention-validity gate、无 source dedup。

任何声称“因果”的结果都必须附 intervention definition、overlap/validity diagnostics 和 continuation-policy scope；否则统一称 attribution 或 credit surrogate。

## 9. Go/No-Go 门禁

阈值在 dev 阶段预注册；下列数值是启动建议，可在第一次 pilot 前修改一次并写入变更日志，之后冻结。

### Gate 0：基础设施与隔离

通过条件：

- runtime 无法读取 gold/evaluation/category/subset；
- no-leak tests、secret scan、trace replay 全部通过；
- 20 题两次基线的 evaluator 结果可复现到确定性归一化误差内；
- 95% 以上使用的 cell claims 有可打开 URL 与正文 span。

失败处理：停止方法实验；先修复数据边界与 evidence pipeline。

### Gate 1：信号

通过条件：

- anchor 或 cell 至少一个核心信号在 validation 的错误检测 AUROC ≥ 0.70，且 95% CI 下界 > 0.50；
- Brier/ECE 经校准改善，不以准确率显著下降换取；
- coverage posterior 相对 recent-yield baseline 在 row-recall Brier 或 premature-stop rate 至少改善 10%（relative）；
- 结论在至少两个领域/两种语言或两个 task family 不反转。

失败处理：

- 若只有 heuristic 有效：项目改为 calibrated heuristic DeepWide controller，不把 entropy 作为主创新；
- 若任何信号都无效：停止 controller 开发，转为 benchmark/failure-analysis 工作。

### Gate 2A：动作价值

通过条件：

- predicted vs actual gain 的 Spearman ≥ 0.30 且 CI 不跨 0；
- best-action top-2 accuracy 显著高于 random/heuristic；
- 等成本分层后仍有效；
- 能识别至少一类“entropy 上升但 task risk 下降”的反证动作。

失败处理：使用规则控制器；EIG 仅作为分析指标，不进入标题。

### Gate 2B：credit 定位

通过条件：

- audit set 至少含 300 个有效步骤，且六类压力样本每类至少 30 个；阈值在 validation 冻结，最终只在 held-out intervention set 评一次；
- OWIC 对 intervention-defined task contribution 的 Spearman ≥ 0.30 且 95% CI 不跨 0；
- signed contribution accuracy ≥ 0.65，且显著高于 raw entropy、gold-log-score 和 deletion baseline；
- top-20% pivotal-step recall 相对最强非反事实 baseline 至少提高 10% relative；
- 在“熵升但纠错”和“重复错误导致熵降”两个压力子集中方向准确率均高于 0.60；
- intervention validity ≥ 90%，OOD rate、overlap 和不同 continuation-policy 敏感性完整报告；invalid intervention 不计主估计但进入失败率，不能静默丢弃；
- gold、reference evidence graph 或 evaluator-only 字段只能用于训练/离线 oracle baseline；所有方法另报 privileged-information budget，确保收益不是更多特权监督造成；
- 去除 counterfactual 或 provenance 至少有一个产生预期方向的显著退化，否则不得把它们写成贡献。

失败处理：不启动 credit RL。若 task-risk change 有效但 causal component 无效，方法降级为 outcome-aligned potential shaping；若只有 entropy 有效，降级为 epistemic diagnostic，不使用 causal/credit 标题。

### Gate 3A：在线 controller pilot

通过条件：

- full controller 在 50 题 paired pilot 中相对 same-action heuristic controller：
  - Item F1 或 Row F1 至少 +3 个绝对点且另一项不下降超过 1 点；或
  - 同质量下总成本至少下降 15%；
- CE Accuracy 不下降超过 1 个点；
- 无新增 contamination/leakage；
- 收益不是单一 seed 或单一 task family 驱动。

失败处理：不跑昂贵全量；检查估计器与 action model，最多允许一次预注册修订。

### Gate 3B：credit-training pilot

通过条件：

- 3-seed closed/replay pilot 中，OWIC full 相对最强同预算 credit baseline 的 held-out Item F1 或 Row F1 平均至少 +2 个绝对点，且 task-cluster bootstrap 95% CI 不支持实质性负效应；或达到同质量所需训练 trajectories 至少减少 15%；seed 只是重复测量，不能把同一任务的多个 seed 当独立样本；
- CE Accuracy 不下降超过 1 个点，unsupported/contradicted rate 不恶化；
- credit overhead 在预注册上限内，且结果不是更多 rollout 或 privileged evidence 单独造成；
- counterfactual/provenance 消融与 RQ5/RQ6 机制预测一致；
- 无 gold/evaluator 信息进入 inference runtime。

失败处理：论文保留 inference controller 分支（若 Gate 3A 通过），credit assignment 降为离线分析或负结果。

### Gate 4：论文主张

通过条件：

- future-method holdout 的主比较 CI 支持预注册 non-inferiority/improvement；强泛化主张还需 confirmatory set 同方向；
- 至少两个机制消融符合 RQ4 预测；
- 人工 evidence audit 不显示 precision 明显恶化；
- 系统级讨论覆盖 WebSwarm、SearchOS、ECR、TaS、A-MapReduce。
- 若标题包含 credit/causal，Gate 2B 与 3B 必须同时通过，且讨论 ECHO、TRACE、LOTAPO、STAMP、RICE-PO、SIOP、CVT-RL。

失败处理：按证据降级为 UQ diagnostic、negative result 或 engineering report；不得保留过强标题/摘要。

## 10. 实施里程碑、负责人和产物

开始每个 milestone 前，把 `Owner`、起止日期、模型/API 预算写实；`TBD` 不得带入正式实验。

| M | 目标 | Owner | 时间 | 预算上限 | 产物 | 状态 |
|---|---|---|---|---:|---|---|
| M0 | 基线、官方评测、文献/novelty audit | 当前会话 + 待确认 PI | 已完成至 2026-07-19 | 已发生，待补账 | `survey.md`、基线 scripts/results | 完成 |
| M1 | 严格 runtime/eval 隔离与正文 evidence pipeline | TBD | 1 周 | TBD | `src/runtime`、`src/evaluation`、no-leak tests | 未开始 |
| M2 | 表格/evidence state 与 replay | TBD | 1 周 | TBD | state schema、20-task replay pack | 未开始 |
| M3 | 四层信号数据与校准 | TBD | 2 周 | TBD | signal dataset、calibration report | 未开始 |
| M4A | Counterfactual action-value pilot | TBD | 1–2 周 | TBD | action set、gain report | 未开始 |
| M4B | Step-credit intervention audit set | TBD | 2 周 | TBD | 300-step interventions、credit report | 未开始 |
| M5A | Heuristic 与 EIG controller | TBD | 1 周 | TBD | controllers、unit tests | 未开始 |
| M5B | OWIC estimator 与 advantage modulation | TBD | 1–2 周 | TBD | credit module、intervention tests | 未开始 |
| M6A | 50-task online controller pilot / Gate 3A | TBD | 1 周 | TBD | paired report、Pareto plots | 未开始 |
| M6B | 3-seed credit-training pilot / Gate 3B | TBD | 2 周 | TBD | checkpoints、learning curves、credit audit | 未开始 |
| M7 | 强基线、消融、全量 test | TBD | 2–3 周 | TBD | frozen runs、aggregate artifacts | 未开始 |
| M8 | 论文写作与审计 | TBD | 1–2 周 | TBD | manuscript、claim/evidence ledger | 未开始 |

### M1 推荐目录

```text
src/entropy_deepwide/
  runtime/
    manifest.py
    search.py
    page_reader.py
    evidence.py
    state.py
    beliefs/
      anchor.py
      coverage.py
      row.py
      cell.py
    actions.py
    controllers/
      fixed.py
      heuristic.py
      entropy.py
    credit/
      signals.py
      interventions.py
      counterfactual.py
      provenance.py
      modulation.py
  evaluation/
    deepwide_official.py
    calibration.py
    action_value.py
    credit_assignment.py
  safety/
    no_leak.py
    contamination.py
configs/
tests/
  test_no_benchmark_leakage.py
  test_evidence_provenance.py
  test_belief_updates.py
  test_stopping.py
  test_intervention_validity.py
  test_credit_telescoping.py
  test_no_gold_at_inference.py
```

## 11. 运行记录与可复现性

每次 run 固化：

```text
outputs/runs/<run_id>/
  frozen_config.yaml
  git_commit.txt
  runtime_manifest.jsonl
  predictions.jsonl
  traces.jsonl
  evidence_manifest.jsonl
  belief_timeseries.jsonl
  action_scores.jsonl
  step_credit.jsonl
  interventions.jsonl
  provenance_roles.jsonl
  costs.json
  contamination_report.json
  metrics.json
  report.md
```

必须记录：模型精确版本、prompt hash、search/page API、日期、并发、seed、token/tool/page/time/USD、每步 belief、候选动作分数、选择原因、forced/normal stop。credit run 另记录每种信号的原始值、干预类型、validity/overlap、continuation checkpoint、终局差值、credit clipping/normalization 与注入后的 advantage。API keys 和原始凭证永不写入 config/trace/Git。

正式结果需导出一个可提交的小型 artifact 到 `results/`：只含 frozen config、aggregate metrics、任务级匿名分数、bootstrap 与图表数据；原始网页内容按版权与隐私规则处理。

## 12. 风险登记

| 风险 | 影响 | 早期检测 | 缓解 |
|---|---|---|---|
| LLM 内部 entropy 失校准 | 低熵错停 | Brier/ECE、QuCo/TASR baseline | 外部统计、校准、`OTHER`、abstain |
| 初始假设漏真值 | ECR 式错误收敛 | top-k coverage、open-set stress | dynamic regeneration、OTHER mass |
| 搜索样本非 i.i.d. | unseen estimator 偏置 | source/query block sensitivity | block capture features + held-out calibration |
| 镜像/SEO 伪多数 | 虚假 entropy drop | content hash/domain graph | source dependence correction |
| 反证使 entropy 上升 | controller 拒绝有益动作 | contradiction stress | 优化 task risk，不要求单调 entropy |
| 无关/对抗内容产生高 surprise | 奖励噪声步骤 | relevance + intervention audit | RelIG、outcome gate、harm penalty |
| 删除 turn 产生 OOD history | 虚假 attribution | intervention validity/OOD | same-state sibling、语义/证据替换、固定 continuation |
| 多步骤协同被单步边际遗漏 | early/verification credit 错配 | pair intervention subset | provenance role + pairwise interaction audit |
| gold-answer credit 泄漏到推理 | test invalid | no-gold inference test | train/runtime 物理隔离、仅训练 oracle baseline |
| credit proxy reward hacking | 分数涨但任务/evidence 变差 | counterfactual outcome + human audit | terminal anchor、sign-preserving modulation、constraints |
| EIG 估计过贵 | 得不偿失 | gain/cost logging | two-stage pruning、cached rollouts、heuristic fallback |
| 强系统已覆盖工程点 | novelty 不足 | 持续更新 survey | 只主张四层开放世界校准机制 |
| benchmark 泄漏/污染 | 分数无效 | no-leak/STC scanner | 进程隔离、污染样本 quarantine |
| LLM judge 不可靠 | 指标偏差 | 人工分层抽检、judge disagreement | 双人审计、规则指标优先 |
| API/网页漂移 | 难复现 | timestamp/hash、replay | 缓存允许的证据元数据、重复运行 |

## 13. 论文贡献判定表

在写摘要前逐项填实：

| 候选贡献 | 所需证据 | 当前状态 |
|---|---|---|
| 四层开放世界 DeepWide belief formulation | 明确定义、与 ECR/SearchOS/WebSwarm 差异 | 理论草案 |
| 校准的 unseen-mass/coverage posterior | Gate 1 coverage 指标 | 无实现 |
| 风险加权 EIG/cost controller | Gate 2A + Gate 3A | 无实现 |
| 同预算质量–成本改进 | 全量 paired test | 无结果 |
| 机制解释 | 对应消融与轨迹案例 | 无结果 |
| 开放世界、结果对齐的 step credit | Gate 2B 干预定位指标 | 无实现 |
| credit 改善训练而非只拟合 proxy | Gate 3B 同预算 3-seed pilot | 无结果 |

在相应证据行未完成前，摘要只能写“we propose/ask/evaluate”，不能写“improves/outperforms/demonstrates”。若 Gate 2B 未过，不得在题目或摘要使用 causal credit。

## 14. 接下来 72 小时的具体任务

1. 从现有 JSONL 生成只含随机 opaque id 与 question 的 runtime manifest；保留映射在 evaluator-only 目录。
2. 把 `run_deepwide_smoke.py` 拆成 generate 与 evaluate 两个不可互读入口；添加禁止字段单测。
3. 实现 page reader 与 evidence span/schema，重新跑 3 个已知任务并人工检查 provenance。
4. 建立最小 persistent state：anchor hypotheses、rows、cells、evidence、operation log、cost。
5. 从现有 220 题结果按“anchor 对/错 × Deep2Wide/Wide2Deep × 中/英”抽取 20–30 题，生成 Phase B 标注清单；不得把 subset label 暴露给 runtime。
6. 先做 anchor semantic entropy + `OTHER` 与 simple baselines 的离线可分性实验；通过小型 sanity 后再做 coverage estimator。
7. 从 10 个可重放任务抽 30–50 个步骤，先做 `original / no-op / equal-cost sibling` 的微型 credit audit；比较 raw entropy、risk change 和 fixed-continuation task contribution。
8. 为 discovery、independent verification、contradiction resolution、synthesis 定义 provenance schema，并人工标 50 步检查一致性。
9. 在完成 M1 和微型 credit sanity 前不实现完整 controller 或 RL credit，不运行新的全量付费实验。

## 15. 完成定义

项目只有在以下条件全部满足时才算完成：

- 方法、代码、数据边界与主张一致；
- 测试集未参与校准/路由，联网污染已审计；
- 四层信号与 controller 均有 same-action、same-budget 对照；
- 若主张 credit，step score 已通过同状态干预审计，并有相同 rollouts/terminal reward/training budget 的强 credit baseline；
- 主结果有 paired uncertainty interval、成本和人工 evidence audit；
- 所有精确数字能追溯到 frozen artifact；
- 文献与 non-claims 覆盖 2026-07-19 的直接近邻，包括 ECHO、TRACE、LOTAPO、STAMP、RICE-PO、SIOP、CVT-RL；
- 失败 gate 被如实报告，标题和摘要按证据强度降级。
