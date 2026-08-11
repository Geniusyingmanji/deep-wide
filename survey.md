# Entropy-DeepWide：信息熵、信息增益与 Credit Assignment 驱动 Deep-and-Wide Search 文献综述

> 检索截止：2026-08-07 14:10 UTC；项目证据更新：2026-08-11 UTC（至 V2.50.63）
>
> 结论强度：这是基于公开文献的 novelty audit，不是“没有任何相关工作”的证明。2026 年文献多为尚未同行评审的 arXiv 预印本，文中将预印本结果视为作者报告，而非独立复现事实。

## 2026-08-11 实验更新：结构化表示收益没有迁移到普通网页或完整 220

V2.50.48 给出了当前最强的表示层正结果，但后续实验限定了它的适用范围。在20个 fresh PyPI任务上，control与candidate逐题共享同一个exact JSON snapshot、问题、12k evidence、GPT-5.6调用次数和arm-balanced顺序。control只接收raw prefix，candidate前置同一current-release record中的project identity、version、earliest upload date与Requires-Python。20/20任务在模型调用前通过parser readiness，candidate改变20/20 prediction。固定20分母的post-freeze评价得到Exact `0→20/20`、Item F1 `0.483333→1.0`和Composite `0.870833→1.0`；Entity、Row与Column均保持1，且两臂均无invalid或fallback。[`results/v25048_atomic_pypi_result_v1_20260811.json`](results/v25048_atomic_pypi_result_v1_20260811.json)与[`results/v25048_atomic_pypi_postresult_audit_v1_20260811.json`](results/v25048_atomic_pypi_postresult_audit_v1_20260811.json)支持“同一结构化authority中的identity/target/value/coherence绑定改善了这组外部任务”，但没有检验普通网页可达性、DeepWideBench迁移或entropy/IG credit。

普通HTML bridge没有复现这一机制。V2.50.50虽然完成20/20 CRAN页面fetch并形成20个identity-bound records和60个bound fields，但parser-ready为0；V2.50.51和V2.50.52分别只有19/20和17/20 ready，均按预注册完整性门停止。V2.50.53保留固定20分母并无条件运行两臂，最终18题ready、2题paired fallback、40个terminal prediction，但prediction change为`0/20`，所以没有开放外部evaluator。[`results/v25053_cran_unconditional_forward_result_v1_20260811.json`](results/v25053_cran_unconditional_forward_result_v1_20260811.json)只支持机制NO-GO。V2.50.54进一步确认V2.50.30的1534个生产页面中，196题在5k prefix以后仍有内容，合计`23,595,703`字符，但旧identity-required projector的natural exposure仍为0。[`results/v25054_representation_opportunity_diagnosis_v1_20260811.json`](results/v25054_representation_opportunity_diagnosis_v1_20260811.json)把剩余瓶颈定位到页面自描述身份与target-field-value record的绑定，而不是简单缺少后缀字符。

V2.50.57随后把page-self representation接到生产fetch seam，并完成一次严格label-blind、固定220分母、failure-as-zero的冷运行。forward得到220/220 terminal predictions，其中214个model-generated、6个fallback，耗时`1058.769355s`；32-worker evaluator对全部220题各评一次，209 valid、11 error-as-zero，耗时`275.247622s`。完整指标为Exact `6/220=2.7273%`、Entity `0.686364`、Row/Item/Column F1 `0.230564/0.398949/0.483962`和Composite `0.449960`。该结果低于V2.50.30的`7/220 / 0.450291`和项目单轮最佳V2.48.57的`9/220 / 0.457249`，也没有Avg@4、leaderboard或SOTA证据。[`results/v25057_page_self_exact220_result_r2_20260811.json`](results/v25057_page_self_exact220_result_r2_20260811.json)与[`results/v25057_page_self_exact220_postresult_audit_r2_20260811.json`](results/v25057_page_self_exact220_postresult_audit_r2_20260811.json)给出结果与闭环审计。

全集运行本身没有触发所测试的表示。1523个投影页面在5k prefix以后共有`30,104,588`字符，但natural mechanism exposure、changed evidence page和positive signed credit均为0，所有页面都精确回退到parent raw prefix。V2.50.57与V2.50.30只有12/220 prediction hash相同，208/220不同；Exact和Composite差值分别为`-1`与`-0.000331233`。由于treatment exposure为0，V2.50.58只能把这些差异归为独立冷搜索与模型rollout变化，不能归因于page-self表示。[`results/v25058_v25057_zero_exposure_diagnosis_v1_20260811.json`](results/v25058_v25057_zero_exposure_diagnosis_v1_20260811.json)因此禁止用同一binding重复220，并要求下一extractor先在全新普通网页外部门证明非零natural exposure、matched prediction change和post-freeze outer utility。

V2.50.59与V2.50.60随后把身份识别面从显式row label扩展为同页共识。V2.50.59要求URL path、title segment和独立正文heading指向唯一同一identity；V2.50.60再允许title/heading写成`<identity> <semantic-version>`或`<identity>-<semantic-version>`，但版本必须在两个独立表面一致，identity仍须是完整URL path component。target field仍要求exact label、唯一安全值、同页完整record，且至少一个完整target observation位于5k之后。开发探针在永久排除的三个crate上观察到2/2 identity binding和1/2完整late record，但该probe没有模型或质量评价，只用于检查新路由是否可能触发。

V2.50.61在20个fresh docs.rs页面上做了固定分母的零模型自然曝光检验。为保证零模型门的能力边界，生产runner改用与V2.50.60逐字段等价、但不导入历史runtime链的纯模块；42/42专项及父链测试通过，forward闭包只有4个文件，privileged、evaluator、credential与model/hosted-search findings均为空。唯一forward用20 workers对每个冻结endpoint请求一次，不redirect、不retry、不替换人口。20/20 fetch成功，20/20形成version-qualified identity，10/20形成完整record，8/20页面超过5k，但只有4/20 target field真正位于5k之后并改变candidate evidence。预注册门要求至少8/20 natural exposure，因此结果为NO-GO；projection failure和positive signed credit均为0。[`results/v25061_docsrs_late_record_forward_result_v1_20260811.json`](results/v25061_docsrs_late_record_forward_result_v1_20260811.json)与[`results/v25061_docsrs_late_record_forward_audit_v1_20260811.json`](results/v25061_docsrs_late_record_forward_audit_v1_20260811.json)记录结果及`findings=[]`的审计。

这一结果把表示路线的瓶颈进一步分解。version-qualified identity在该固定人口上达到20/20，因此不能再把零曝光笼统归因于身份识别失败。完整target record只有10/20，而absolute-late target只有4/20，说明“页面长度超过5k”不等同于“5k之后包含任务所需新字段”。后续应把late-information recovery与salience/atomicity representation分开检验。前者只在prefix之外出现新target时触发；后者可以重排prefix内已经完整绑定的record，但必须在fresh disjoint人口上通过shared-page、matched-budget的prediction-change与post-freeze outer utility门。V2.50.61没有模型、evaluator或DeepWideBench运行，因此不提供质量、SOTA或entropy-credit证据，也不能用20/20 identity或4/20 exposure替代这些证据。

V2.50.62随后独立检验prefix-salience/atomicity，不再把late-information recovery算作同一机制。候选只在identity和全部target field已经位于父5k prefix内时前置一个原子record；任一target位于5k之后就逐字返回父prefix。20个fresh且与V2.50.59–61不交的docs.rs页面全部fetch成功并形成唯一identity，14页超过5k，但只有4页形成完整License record，且4个target全部位于5k之后。因此prefix-complete、candidate change与mechanism exposure均为`0/20`，低于预注册的`8/20`门；capacity、projection与transport failure均为0。[`results/v25062_prefix_salience_forward_result_v1_20260811.json`](results/v25062_prefix_salience_forward_result_v1_20260811.json)和[`results/v25062_prefix_salience_forward_audit_v1_20260811.json`](results/v25062_prefix_salience_forward_audit_v1_20260811.json)记录该NO-GO及`findings=[]`审计。

V2.50.61与V2.50.62使用不同的fresh人口，不能把两轮计数相加或直接解释为同一个处理效应。两轮共同支持的是version-qualified identity route在各自20页上均达到20/20；target completeness与字段位置则明显依赖页面人口。V2.50.61为10个完整record、4个late target，V2.50.62为4个完整record且全部late。因而当前没有证据支持prefix-salience的稳定覆盖，也没有证据把late recovery迁移到DeepWideBench质量。后续不应继续通过更换docs.rs人口追逐覆盖率，而应先检查冻结220输出中的通用、label-blind结构错误，再为确定性变换建立全220开发评价和独立冷运行复现。

V2.50.63对V2.48.57、V2.50.30和V2.50.57三轮冻结全集做了aggregate-only结构诊断。三轮共660份prediction全部各有一个可解析pipe table和至少一条data row，empty cell与malformed-width row均为0。规范化首列identity重复分别出现在`67/65/64`题，额外重复identity行分别为`1696/1793/1476`；完整重复行却只有`38/0/0`。首列重复因而通常对应同一entity下的不同记录，不能作为通用去重键。all-target-Unknown非主键行分别为`185/50/138`，但prediction结构无法判定这些行是无效输出还是任务要求的缺失占位，也不能安全删除。

这些结构信号也没有定位evaluator错误。三轮evaluator error分别为`10/12/11`；duplicate-identity信号组内只有`0/1/1`个error，无该信号组则有`10/11/10`个。因此大多数internal/out-of-range错误不能由首列重复解释。诊断只解码prediction/instance ID与evaluator error状态的白名单字段，其他值以JSON词法边界跳过；结果没有输出逐题内容、score、gold或类别。[`results/v25063_three_run_output_structure_diagnosis_v1_20260811.json`](results/v25063_three_run_output_structure_diagnosis_v1_20260811.json)和[`results/v25063_three_run_output_structure_audit_v1_20260811.json`](results/v25063_three_run_output_structure_audit_v1_20260811.json)支持通用去重与Unknown行删除NO-GO，但不支持任何质量提升主张。

三轮输出结构完整而Exact/Composite仍低，把优化重点重新指向事实选择与记录级grounding。后续候选应在同一source record内绑定row identity、target field与value，再由matched shared-page实验检验prediction和outer utility；不应通过删行或合并首列来提高表面precision。信息熵仍可表示候选证据对cell belief的增量，但signed credit必须来自record-bound intervention和post-freeze utility，而不是重复行计数、Unknown率或evaluator error状态。

这条证据链也收紧了信息熵与credit assignment的主张。结构化记录表示可以得到正的机制级outer credit，但本轮没有让entropy/IG选择动作或分配credit；普通网页和完整220又都没有产生可归因的observation。因而当前entropy/IG signed credit仍为0。下一实验可以用四层开放世界风险或expected information gain预测动作优先级，但credit的正负必须来自同状态删除、替换、suffix intervention，或与开发工件隔离的终局评价。单纯的后缀长度、局部熵下降、parser readiness或prediction change均不足以获得正credit。

## 2026-08-11 实验更新：PyPI 结构化表示通过外部门，但尚未迁移到普通网页

V2.50.47–48 已把 V2.50.46 提出的“改变证据表示而非继续加重 prompt”假设做成完整 matched external gate。20 个 fresh PyPI 任务的两臂共享同一次 exact JSON response、同一问题、GPT-5.6、一次调用、12k evidence 和 arm-balanced order；control 只看 raw prefix，candidate 从完整响应确定性前置 `project identity / current version / current-release earliest upload date / Requires-Python` 的同记录绑定。atomic readiness 在模型前得到 20/20 fetch、20/20 parser-ready、80/80 fields、1 Unknown；之后两臂各 20/20 model success、0 fallback，candidate 自然改变 20/20 prediction，超过预注册 8 题机制门。

prediction freeze 与 content-free audit 推送后，离线 evaluator 只使用同次 forward 后发布并冻结的 public snapshot，不 refetch、不联网、不调用模型或搜索。raw-prefix control 为 Exact `0/20`、Item F1 `0.483333`、Composite `0.870833`；identity-bound candidate 为 Exact `20/20`、Item F1/Composite 均 `1.0`，Exact `+20`、Item F1 `+0.516667`、Composite `+0.129167`，Entity/Row/Column 均保持 `1.0`。post-result audit 为 `audit_valid=true, findings=[]`。初次 audit 曾因 JSONL sort-key 后把对象键序误当 schema 顺序而 fail closed；append-only erratum 改用 exact key set，未改写或重跑预测、snapshot 或 forward，也未提前创建 evaluator。

这给 entropy/credit 主张增加了一个清晰的正例与边界。正例是：当 observation 已经 source/identity/target/coherence-bound，且 representation-only intervention 在 matched cost 下产生 prediction change 和 post-freeze outer utility，它可以获得正的机制级 credit。边界是：本实验没有让 entropy/IG 选择动作或分配 credit，且 PyPI JSON 是稳定结构化 authority；因此不能把结果外推为“熵降越大 credit 越高”，也不能视为 DeepWideBench 提分。下一步需要在 production-isomorphic 普通网页证据上检验通用 record binding 的 natural reachability；在该 bridge gate strict GO 前，不应再次运行公开 220。权威结果与审计为 [`results/v25048_atomic_pypi_result_v1_20260811.json`](results/v25048_atomic_pypi_result_v1_20260811.json) 和 [`results/v25048_atomic_pypi_postresult_audit_v1_20260811.json`](results/v25048_atomic_pypi_postresult_audit_v1_20260811.json)。当前 DeepWideBench 最新完整结果仍为 V2.50.30 Exact `7/220`、Composite `0.450291`；项目单轮最佳仍为 V2.48.57 Exact `9/220`、Composite `0.457249`，未上榜、非 SOTA。

V2.50.43进一步比较了最新V2.50.30与项目最佳V2.48.57的冻结输出形态。V2.50.30总行数多105，Unknown value cell多1,019，但Exact仍从9降到7；两轮只有2题表宽变化。4个Exact loss与2个gain几乎都发生在相同行数和表宽下，因此当前瓶颈主要是同形表格里的事实选择，而不是简单少输出行。这个结果也再次否定“Unknown越少或coverage越满就越好”：强制completion可能把不确定性换成错误事实，不能获得正entropy/task credit。该分析不输出题目、任务身份、prediction、gold或逐题metric，见[`results/v25043_v25030_v24857_output_shape_diagnosis_v1_20260811.json`](results/v25043_v25030_v24857_output_shape_diagnosis_v1_20260811.json)。

V2.50.44–46随后检验了一个预算中性的合成假设。candidate prompt要求每个非Unknown cell由exact row identity、field、value与同一source record联合支持，并禁止把旧版本日期、邻近实体或不同记录拼接为“latest”答案；冲突时保留Unknown。V2.50.45在20个fresh PyPI任务上让两臂共享同一次`2+2`检索、同一187个usable page集合和逐字相同的12k evidence，各只做一次GPT-5.6 synthesis。运行20/20 terminal、0 fallback、无retry或transport failure，但candidate仅改变2/20 prediction，低于预注册4题门，因此没有打开gold/evaluator。

冻结后counts-only诊断显示，这两个变化都只是把一个非Unknown cell改成Unknown；没有行列变化、Unknown→事实或事实→不同事实，candidate模型token还高`1.055678×`。所以更严格的自然语言约束只带来弱abstention，没有形成可识别的fact correction机制。下一步应改变同一页面的证据表示：先确定性构造identity-bound compact record，再让相同模型合成；不能继续把prompt强度、页面数量或主观熵下降当作质量代理。V2.50.45/46工件为[`results/v25045_evidence_constrained_forward_result_v1_20260811.json`](results/v25045_evidence_constrained_forward_result_v1_20260811.json)、[`results/v25045_evidence_constrained_forward_audit_v1_20260811.json`](results/v25045_evidence_constrained_forward_audit_v1_20260811.json)和[`results/v25046_v25045_weak_abstention_diagnosis_v1_20260811.json`](results/v25046_v25045_weak_abstention_diagnosis_v1_20260811.json)。这些结果不是DeepWideBench提分，当前最佳仍是V2.48.57的`9/220 / 0.457249`。

V2.50.42用官方文档和本地零模型审计封闭了两个容易混淆的成本假设。OpenAI的Responses文档说明，`previous_response_id`能延续上下文，但链中历史input tokens仍计费；它不是删除第二次请求历史input的机制。[Conversation state](https://developers.openai.com/api/docs/guides/conversation-state#passing-context-from-the-previous-response) Prompt caching则可降低精确重复prefix的读取成本，但GPT-5.6要求至少1,024-token exact prefix，cache write按uncached input的`1.25×`计，且需要同时报告`cached_tokens`与`cache_write_tokens`才能判断净成本。[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

当前DeepWide search客户端没有设置continuation/cache请求字段，也没有记录cache read/write usage；本地9878的标准OpenAPI与OPTIONS路径均返回404，因此代理能力尚未通过可读schema建立。历史V2.42.79虽记录过`cached_input_tokens`，32个请求合计均为0，但每个请求只有156–212 input tokens，低于官方最低门槛，不能作为cache支持或不支持的有效检验。V2.50.42据此把`previous_response_id`省input判为NO-GO，把本地prompt-cache support与net savings标为未建立，并禁止新的cache effect probe。该审计只发出两个无body schema请求，model/search/fetch/evaluator/benchmark effect为0；工件为[`results/v25042_continuation_cache_capability_audit_v1_20260811.json`](results/v25042_continuation_cache_capability_audit_v1_20260811.json)。

成本路线因此暂时停止，而不是宣称缓存永远无用。对于当前pipeline，更可识别的下一步是固定同一批fetched pages、query/fetch/model/token/wall预算，只改变evidence representation或synthesis/completion，然后在fresh external shared-prefix任务上评价终局表格质量。这个顺序也适用于entropy credit：cache hit、token节省或上下文延续属于资源或执行信号，只有与admissible evidence和post-freeze outer utility结合后才能进入signed task credit。

V2.50.41进一步检验了“在一个hosted-search response内保留适应性”的接口假设。四个历史已消费的中性文档pair各运行一次candidate：先执行两条精确seed query，再要求模型根据首波source title生成并执行两条follow-up。control随后用candidate在内存生成的同四query按`2+2`执行，因此该实验只比较capability、trace与成本，不是质量或随机化因果实验。唯一probe完成4/4题，candidate/control provider calls为`4/8`，0 retry/fetch/transport failure/timeout；candidate产生16条distinct query和8条follow-up，control完整观察8个双query向量。

该接口形式没有通过预注册门。candidate的86个distinct action sources多于control的76个，但首波64个action sources均缺title，所以8条follow-up没有一条可由“首波title中新出现的token”审计支持。模型生成了follow-up不等于已证明它使用了首波可采纳证据。成本也没有下降：candidate/control input与total token比为`1.004633/1.010257×`，略高于control而非预注册的`≤0.85×`。结果因此是capability/cost NO-GO，不授权fresh external、DeepWideBench或evaluator。post-result audit为`audit_valid=true, findings=[]`；证据见[`results/v25041_adaptive_single_request_development_probe_v1_20260811.json`](results/v25041_adaptive_single_request_development_probe_v1_20260811.json)和[`results/v25041_adaptive_single_request_postresult_audit_v1_20260811.json`](results/v25041_adaptive_single_request_postresult_audit_v1_20260811.json)。

V2.50.39与V2.50.41合起来把成本路线限制得更精确。预先可见的static四query可以通过one-shot降低约27% search token，但发生局部字段质量退化；在单response中重新引入适应性则既缺少可审计首波provenance，也未降低token。后续应先确认provider是否支持显式response continuation或cached input，并要求分wave source metadata可验证；若接口不具备这两项能力，就不应继续用prompt技巧逼近adaptive batching。这个结论不否定一般的adaptive search，只否定当前provider接口和提示形式。它也不改变entropy-credit结论：query数量、source数量或生成了follow-up都不能获得正credit，credit符号仍需来自admissible evidence与post-freeze outer utility。

V2.50.39 在20个全新 PyPI 表格任务上比较同一组四条预先可见query的两种物理分组。control按`2+2`发出两次hosted-search请求，candidate把四条query合并为一次请求；两臂共享任务、query向量、deterministic fetch union、12k evidence预算、prompt、GPT-5.6和240秒上限。唯一forward完成20/20题、0 fallback，两臂均观察到`80/80`条exact action query。candidate将provider calls从40降至20，search input与total token降至control的`0.730468/0.730697×`；selected leads均为200、usable pages均为185，raw characters为`0.980566×`。这些直接计数支持“固定query的一次性batch摊薄hosted-search请求成本”，但不涉及V2.50.30根据首波页面生成第二波query的适应性。forward结果与audit见[`results/v25039_batching_external_forward_result_v1_20260810.json`](results/v25039_batching_external_forward_result_v1_20260810.json)和[`results/v25039_batching_external_forward_audit_v1_20260810.json`](results/v25039_batching_external_forward_audit_v1_20260810.json)。

质量结果否定了直接替换。prediction freeze和content-free audit推送后，evaluator对20个固定PyPI endpoint各调用一次；20/20 gold有效，两臂共享同一snapshot，失败按固定20分母计零。`split_2_plus_2`与`one_shot_4`的Exact同为`12/20`，Entity、Row和Column均为`1.0`，但Item F1从`0.816667`降至`0.783333`，Composite从`0.954167`降至`0.945833`。预注册质量门因此为NO-GO，post-result audit为`audit_valid=true, findings=[]`。结果与审计见[`results/v25039_batching_external_result_v1_20260810.json`](results/v25039_batching_external_result_v1_20260810.json)和[`results/v25039_batching_external_postresult_audit_v1_20260810.json`](results/v25039_batching_external_postresult_audit_v1_20260810.json)。

V2.50.40在结果冻结后做了counts-only paired diagnosis。4个prediction-change任务中，one-shot按正确字段数计有1题改善、3题退化；Exact gain/loss均为0，latest version、latest release date和Requires-Python的正确字段数净差分别为`-1/-1/0`。该分析没有重评、搜索或模型调用，也不保存任务身份、prediction、gold value或页面内容。[`results/v25040_v25039_paired_quality_diagnosis_v1_20260811.json`](results/v25040_v25039_paired_quality_diagnosis_v1_20260811.json)限定了可写结论：本次paired run观测到成本下降与局部字段质量退化，但20题和两臂独立生成不足以建立稳定因果效应。

这一结果对信息熵和credit assignment有两个约束。第一，token下降、source数量不退和prediction change都不是正task credit；只有post-freeze outer utility不退时，成本收益才可进入最终decision credit。第二，V2.50.39没有实现或评价hidden anchor、未见实体质量、row eligibility与cell uncertainty四层风险，因此不能作为entropy-credit证据。下一实验应保留evidence-conditioned第二波，只研究如何减少两次hosted-search之间的重复上下文成本；entropy/IG仍只能作为shadow/VOC feature，signed credit保持0。完整DeepWideBench口径仍是最新V2.50.30 Exact `7/220`、Composite `0.450291`，项目单轮最佳V2.48.57 Exact `9/220`、Composite `0.457249`；二者均不是leaderboard或SOTA结果。

## 2026-08-09 实验更新：V2.49.54 完整 220 与机制可迁移性边界

V2.49.54 已完成严格 label-blind、固定 220 分母、failure-as-zero 的一次完整 DeepWideBench rollout。全部预测在 mapping、gold、category、question type、split 与 evaluator 开放前冻结；forward 为 `220/220` model-generated、0 fallback、`756.425535s` 和 `11,269,048` system tokens。固定 32-worker evaluator 对每条冻结预测各评一次，210 valid、10 error-as-zero；Exact `7/220=3.1818%`，Entity `0.695455`，Row/Item/Column F1 `0.214752/0.386390/0.467948`，Composite `0.441136`。结果 seal 与 post-result audit 均通过，`findings=[]`。[`results/v24954_partial_signature_exact220_result_v1_20260809.json`](results/v24954_partial_signature_exact220_result_v1_20260809.json) 和 [`results/v24954_partial_signature_exact220_postresult_audit_v1_20260809.json`](results/v24954_partial_signature_exact220_postresult_audit_v1_20260809.json) 是权威工件。

该结果不支持 mutual-partial signature 提升。220 份 content-free projection receipt 全部有效，但 27 条 partial candidate edge 中有 7 个 header 因竞争关系 fail closed，最终 partial-bound table、schema-bound record 与 admissible observation 均为 0。相对 V2.49.48 的 Exact/Composite 上升只能视为独立 search/model/judge rollout 波动，不能作机制 credit。更广的 36 份合法 fixed-220 结果复核显示，项目单轮观测前沿仍是 V2.48.57：Exact `9/220`、Composite `0.457249`、Entity `0.713636`、Row/Item/Column F1 `0.229739/0.400228/0.485392`。这仍不是 leaderboard、Avg@4 或 SOTA 证据。

这个失败对文献与方法设计有直接含义。World Bank/ROR 等预构造表格上的 matched shared-prefix GO 只能证明 parser 在对应 layout 上有效，不能证明 live search 会返回同类页面；“外部机制 GO→公开全集零触发”已在 compact ledger、full signature 和 mutual-partial signature 三条链重复出现。后续必须在答案生成前冻结一个不含 query/URL/page text/prediction/score 的 live structural-exposure receipt，并把自然触发当作进入质量门的必要条件。信息熵也必须位于 `admissible observation → calibrated belief change → provenance/source-dependence → same-state outer utility` 之后；零触发的规则不能获得正 credit，熵下降更不能替代 task utility。

## 2026-08-08 V2.48.50：完整复现再次确认单 rollout 方差，未刷新前沿

V2.48.50 使用与 V2.48.00 相同的 220 题向量、GPT-5.6、Tavily URL-lead transport、prompt、fixed-full-budget controller、hard caps 与并发，只更换全新的 create-only 执行和评测表面。forward 仍严格只读 `{opaque_id, question}`；`220/220` prediction 在 mapping、gold 与 evaluator 开放前冻结，219 个表由模型生成、1 个为预注册 fallback，前向耗时 `726.77s`。prediction freeze 与 forward audit 提交推送后，32-worker evaluator exactly-once 覆盖全部 220，210 valid、10 error 按固定规则计零。

完整结果为 whole-table `7/220`、Entity `0.681818`、Row/Item/Column F1 `0.225550/0.390296/0.471082`、Composite `0.442187`。相对 V2.48.00，exact 少1、Composite 低 `0.014647`；相对 V2.48.48，exact 多2、Composite 高 `0.005544`。同一 V2.48.00 policy 的三次完整运行 V2.48.00/07/50 因而为 exact `8/8/7`、Composite `0.456834/0.438248/0.442187`。V2.48.00 仍是 observed single-rollout internal peak，但 V2.48.50 没有刷新 benchmark 前沿，也没有 leaderboard、Avg@4 或 SOTA 证据。权威结果和审计分别为 [`results/v24850_v24800_replication_exact220_result_v1_20260808.json`](results/v24850_v24800_replication_exact220_result_v1_20260808.json) 与 [`results/v24850_v24800_replication_exact220_postresult_audit_v1_20260808.json`](results/v24850_v24800_replication_exact220_postresult_audit_v1_20260808.json)。

这一复现进一步限制 entropy/credit 的经验主张：同一无熵 fixed-full-budget policy 本身已有可观 rollout 波动，因此独立全集间的得分差不能识别 evidence selector、entropy 或 credit 的因果作用。后续必须共享 prefix、冻结 admissible action set 与成本，或进行预注册的独立重复；历史公开题的分数、正确性和 evaluator bin 不得进入 runtime route。entropy/IG 只能先作为动作价值或不确定性 feature，credit 的符号仍须由同状态 intervention 或 terminal outer utility 给出。

## 2026-08-07 V2.48.07/08：完整重复运行否定了单轮前沿的稳定性假设

V2.48.07 在与 V2.48.00 相同的 forward 算法、任务向量、模型、搜索、hard caps 与并发下，从全新输出面完成第二次完整 220。forward 为 `220/220`、0 fallback、`778.15s`；预测冻结后 32-worker evaluator 得到 whole-table `8/220`、Entity `0.681818`、Row/Item/Column F1 `0.216028/0.384515/0.470633`、Composite `0.438248`，209 valid、11 error-as-zero。它没有复现 V2.48.00 的 Composite `0.456834`，但 Whole-table 同为8。因此新结果不是提升，更不是 SOTA。

V2.48.08 对两次冻结结果做 aggregate-only 配对复核。220 题中仅10题的 prediction hash 完全一致，210题发生字节变化；Whole-table 有6题两轮均成功、2题失→得、2题得→失，净差0。任务级 Composite 差为 `-0.018585`，20,000次 task-bootstrap 95%区间约 `[-0.049316, 0.011677]`，覆盖0。即使只看两轮 evaluator 都有效的203题，Entity、Row、Item、Column仍全部为负差。因而 V2.48.00 只能称为 observed single-rollout internal reference；它不能证明 fixed-full-budget 优于 adaptive admission，也不能证明 entropy/VOC 无效。今后候选必须同时相对两轮报告，并优先采用 shared-prefix 或多次独立重复，而不是追逐一次随机前沿。

评分器本身也有结构性噪声。两轮 evaluator-invalid 分别为13和11，交集7、并集17。日志把主要 internal error 追到 released evaluator：当规范化主键没有交集时，`df_inner` 为空，Pandas `DataFrame.apply(axis=1)` 返回 DataFrame，随后被赋给一个 score column 而抛异常。另一个失败面是多对多主键规范化让 unique-column true positives 超过 ground-truth 行数，产生 recall/F1 大于1。当前 official 结果继续严格 error-as-zero，不能选择性重评；未来兼容修复只能预注册后用于新协议，并同时公开 official 与 repaired sensitivity，不能回写这两次分数。

## 2026-08-07 当前结论：V2.48.00 建立单轮内部前沿，但没有识别固定预算或熵策略的因果效应

V2.48.00 已完成严格 label-blind、固定 220 分母、failure-as-zero 的单次完整运行。forward 在全部预测冻结前只接收 `{opaque_id, question}`，之后才开放 mapping 与 official evaluator。结果为 whole-table `8/220 = 3.6364%`、Entity `0.700000`、Row F1 `0.228723`、Item F1 `0.406003`、Column F1 `0.492610` 和 Composite `0.456834`。207 题得到有效 evaluator 输出，13 个 evaluator error 按零计入固定分母。forward 与 32-worker evaluator 分别耗时 `779.65s` 和 `208.50s`，系统 token 总量为 `3,786,108`。这一个版本同时超过此前仓库内的 whole-table 与 Composite 前沿，因此是当前内部单轮参考；它没有 leaderboard 提交、Avg@4 或同协议外部 SOTA 证据。[`results/v24800_exact220_result_v1_20260807.json`](results/v24800_exact220_result_v1_20260807.json) 与 [`results/v24800_exact220_postresult_audit_v1_20260807.json`](results/v24800_exact220_postresult_audit_v1_20260807.json) 给出结果和审计链。

V2.48.01 的冻结后配对诊断限制了可写成论文结论的范围。相对 V2.47.98，V2.48.00 的 whole-table 从 `6` 增到 `8`，Composite 增加 `0.014684`，Row、Item 与 Column F1 分别增加 `0.014146`、`0.016983` 与 `0.018518`；代价是 token 从 `2,687,861` 增至 `3,786,108`，比例为 `1.4086×`，有效 evaluator 行从 `209` 降至 `207`。任务级 Composite 为 83 题提高、82 题持平、55 题下降，20,000 次 task-bootstrap 的 95% 区间为 `[-0.013787, 0.043379]`，跨越 0。whole-table 有 3 题 failure→success、1 题 success→failure。增益主要出现在旧 controller 判为 `first_wave_sufficient` 的 192 题，但两次运行没有共享随机前缀，也不是随机化或 matched-cost 对照。因此，当前证据支持“固定 full budget 在这一次公开 220 运行中刷新内部前沿”，不支持“固定预算普遍优于 adaptive early stop”，更不支持“entropy/VOC controller 有负因果效应”。权威聚合为 [`results/v24801_v24798_v24800_paired_postresult_diagnosis_v1_20260807.json`](results/v24801_v24798_v24800_paired_postresult_diagnosis_v1_20260807.json)。

## 与 WebSwarm 的精确 76-task manifest 对照

WebSwarm v1 使用递归 `atom/deep/wide/entity_collect` 节点、Web-Probing 和同质 sibling 的 process-experience reuse。[5] 论文只报告 DeepWideSearch 的 76 题子集，而非 220 题全集；其 GLM-4.5 结果为 SR `6.58%`、Row F1 `29.64%`、Item F1 `58.40%`，未报告 Entity、Column 或本文使用的四项 Composite。论文消融中，移除 Web-Probing 后 Item F1 从 `58.40%` 略升为 `58.93%`，平均 web-tool calls 却从 `203.73` 增至 `331.39`，因此该消融主要支持效率解释；移除 sibling experience 后 Item F1 降到 `55.48%`，平均调用为 `220.07`。这些结果没有 entropy、information-gain 或 step-credit 机制。

V2.48.02 在 V2.48.00 的 220 个预测与评价全部终态后，使用 WebSwarm repo commit `40c9aac…5717` 的精确 76-task manifest 做 aggregate-only join。V2.48.00 在同一任务集合上为 whole-table `5/76 = 6.5789%`、Row F1 `33.0718%`、Item F1 `54.8945%`、Entity `80.2632%`、Column F1 `64.3464%`，其中 72 行 evaluator 有效、4 行按零计。相对论文的四舍五入值，SR 在两位百分比精度上相同，Row F1 高 `3.4318` 点，Item F1 低 `3.5055` 点。公开文件名为 `en_subset`，但其 `language` 字段实际为 `75 en + 1 zh`，所以“76 个 English tasks”与当前仓库 manifest 不完全一致。

上述 76 题数字只能作描述性同集合对照。两边 backbone、agent、prompt、search/page 工具、action cap、evaluator 实现与 web-tool call 定义均不相同，也没有随机化或 matched-cost 设计；任何一边都不能据此宣称在公平设置下胜过另一边。V2.48.00 在该子集累计 `327` 次 search、`690` 次 fetch 与 `820,655` system tokens，这些计数也不能与 WebSwarm 的递归 web-tool calls 直接相除比较。可复验的聚合与全部限制见 [`results/v24802_v24800_webswarm76_postfreeze_aggregate_v1_20260807.json`](results/v24802_v24800_webswarm76_postfreeze_aggregate_v1_20260807.json)。该 subset membership 不得反馈未来公开 DeepWideBench 的 runtime routing。

## 2026-08 新增 credit-assignment 工作对信息熵主张的约束

| 工作 | credit 信号 | 与本项目最接近之处 | 尚未覆盖的边界 |
|---|---|---|---|
| ABSeeker / ABC [186] | 用 verified answer 回溯 clue，再按 clue 对每一步打分 | 搜索步骤的 dense signed supervision | 训练时依赖 ground-truth answer，不能作为 label-blind runtime credit；不估计开放集合风险 |
| TreeCredit [187] | 从同一中间 state 展开 operators，以 terminal correctness 和 suffix cost 排序 | shared-prefix、state-matched downstream utility | 面向多智能体推理 operator，不建模 anchor、开放集合、行资格或格值风险 |
| TCPO [188] | best-prior score delta、delayed hindsight 与 high-surprisal fixed-history counterfactual | verifier score-to-credit 与选择性同历史干预 | surprisal 只决定精细评估对象，不等于 task credit；依赖 verifier-guided refinement |
| BiCAA [189] | forward solvability gain 与 hindsight success criticality | 同时衡量局部进展和终局必要性 | 未处理来源依赖、错误证据使 posterior 变尖或开放集合遗漏 |
| AgentOPSD [190] | teacher–student log-probability gap 的递归 Bayesian log-odds 更新与边际 belief revision | belief delta 形成 turn credit | belief 是 teacher-relative proxy，不是经过校准的四层任务损失，也没有 source/identity gate |
| TurnSight [191] | execution-conditioned multi-horizon hindsight，经 sibling normalization 后只调节原 advantage 幅度 | state-aligned hindsight 与 sign-preserving credit | 不估计网页证据的开放集合覆盖或 target–value provenance |

这六项工作使三个宽泛主张不再成立。shared-prefix credit、belief revision credit，以及用 surprisal 选择 counterfactual 都已有直接近邻；单独把“熵降大的步骤给更多 credit”也会把错误来源导致的过度确信、重复证据与无终局作用的局部变化记成正贡献。当前仍可检验的组合是四层开放世界风险，即 hidden anchor、未见实体质量、row eligibility 与 cell value uncertainty，经校准后投影到 terminal task loss；每个 observation 还必须先通过 primary-identity、target–value 与 source-dependency gate。entropy 或 expected information gain 可以预测动作排序和 credit 幅度，但 credit 的正负应来自同状态 suffix/deletion/replacement，或 artifact-disjoint outer utility。限定到本综述当前核验的 191 篇公开工作，没有发现同时实现这四层风险、上述证据门和 terminal-utility signed credit 的系统；这仍是检索范围内的 gap，而不是不存在相关工作的证明。

以下各节按日期保留历史证据。凡与本节当前分数、版本或下一实验授权冲突的旧陈述，均由 V2.48.00–02 覆盖。

V2.47.80 又提供了一个 acquisition 与 evidence admission 分离的负结果。唯一一次 fresh 8-task 外部门在 `48.561393s` 内完成 `8/8` valid task 和 `16/16` terminal arm predictions。64 次 initial fetch 得到 47 页，13 次 reserve fetch 得到 10 页；reserve 使 4 个 entity slot 从不足双源变为至少双源，最终 19 个 slot 有至少两个可用 identity source。尽管 acquisition treatment 自然触发，projection-backed support set、changed task 和 changed cell 都是 0。content-free audit 因而判定 forward health GO、mechanism NO-GO，并在 private truth/quality surface 前停止。权威证据为 [`results/v24780_staged_fallback_forward_result_v1_20260807.json`](results/v24780_staged_fallback_forward_result_v1_20260807.json) 与 [`results/v24780_staged_fallback_forward_audit_v1_20260807.json`](results/v24780_staged_fallback_forward_audit_v1_20260807.json)。

这个结果不支持“增加可用页面即可提高表格质量”，也不能据此判断现有 projector 的哪一条内容规则过严。审计没有打开 prediction JSONL、task result、页面内容或 evaluator，只能把剩余瓶颈定位到从 usable identity page 到 target–field–value support 的转换区间。后续实验应在全新人口上预注册更细的 content-free funnel，并只改变一个 projector 或 normalization treatment；同一 V2.47.80 人口不得重跑、补请求或事后查看页面来选择规则。V2.47.80 没有产生 DeepWideBench 分数，也没有验证 entropy-based credit。

对“许多版本究竟测了什么”的复核表明，版本号不能当作 benchmark 次数。V2.43.14 是两臂各64题的 development gate，得到 whole-table `4→5/64`、Composite `0.458367→0.509762`，但95% paired bootstrap区间 `[-0.016349, 0.123977]` 跨0。V2.43.15 随后确实冻结了 `220/220` predictions，forward为 `3041.558286s`，却有2个parent hard timeout，使完整child/model/transport receipt只有 `218/220`；预注册health gate失败后没有调用evaluator，所以没有benchmark分数。修复runner/accounting后的V2.43.20再次做两臂各64，whole-table `5→5/64`、Composite反而 `0.468169→0.451261`，严格NO-GO。这个复核否定了“V2.43.14已经证明staged reserve稳定提分”的说法，也解释了为何跑到220仍不能报告分数。

V2.43.30是第二个边界案例：baseline/candidate都冻结了 `220/220` prediction rows，但candidate non-identity task、admitted cell change和正entropy credit都是0，另有shared-prefix与effect-accounting门失败，evaluator依法未开。它只能证明完整forward的failure-as-zero与fail-closed边界，不能进入全集成绩表。相反，V2.42.67、V2.42.87、V2.46.30、V2.46.35和V2.47.14/18 identity case才有固定220分母的结果；其中只有V2.42.67和V2.46.35位于当前两条前沿。

最新V2.47.37–42进一步把generic transfer的瓶颈定位到transport failure domain，而非熵策略。V2.47.37在 `16.384839s` 完成24个benchmark-external任务、48个arm prediction与50个固定请求，49个请求成功。ROR簇12/12任务发生改变，48个identity target和96个target–value cell完成绑定；World Bank一个共享bulk请求失败却让该簇12/12任务全部abstain。V2.47.38据此确认了“一次shared transport failure放大到整簇task non-change”。V2.47.42改为target-isolated、bulk/aggregate OR-admission，在两个全新target上固定发4个请求，但只有1个成功、`1/2` target admitted，墙钟 `15.272258s`，仍为严格NO-GO。同一主机的两种表示不是可靠的独立冗余；这些实验没有运行DeepWideBench、evaluator或entropy-credit比较。

V2.47.43–49 首次把这一边界推进到跨schema、跨host的通用record binding，但整体外部门仍为NO-GO。纯binder只接受精确可见身份、精确列名和结构化field/value；official exact-address record可单源填Unknown，普通页面必须由两个registrably-independent source同值支持，冲突则abstain。V2.47.48在预先冻结的6题/24行外部人口上固定发32个请求，`2.067710s`内完成6/6 valid task；ROR official路径得到8个完整行，Crossref+OpenAlex普通双源路径自然得到3个完整行和6个corroborated cells。后者是目前最直接的“同一通用binder跨两个不同公开schema自然触发”证据，不再只是ROR或World Bank单namespace adapter。

该结果不能写成generic transfer GO。Crossref official exact簇没有完整行，因此预注册三簇合取门失败。冻结后content-free诊断显示，Crossref 16个并发请求只有3个HTTP 200，另13个全部为HTTP 429；ROR与OpenAlex分别8/8 HTTP 200。证据把失败定位到host-local request scheduling与公开API rate limit，而不是普通双源值绑定本身，但同一人口禁止补请求或重跑。下一实验若继续，必须在全新DOI/ROR人口上预先固定host-local Crossref低并发或pacing，同时保持全局跨host并发、单URL一次尝试、相同identity/value/conflict门。只有三条路径均通过后才有资格进入fresh paired dev64。V2.47.48没有调用DeepWideBench evaluator，也没有衡量entropy或credit assignment；所以全集分数、SOTA结论与信息熵创新证据均不变。对应证据为 [`results/v24748_cross_domain_result_v1_20260806.json`](results/v24748_cross_domain_result_v1_20260806.json)、[`results/v24748_cross_domain_postresult_audit_v1_20260806.json`](results/v24748_cross_domain_postresult_audit_v1_20260806.json) 与 [`results/v24749_v24748_host_rate_limit_diagnosis_v1_20260806.json`](results/v24749_v24748_host_rate_limit_diagnosis_v1_20260806.json)。

title-backfill也应从方法候选中删除。V2.46.30的40个、V2.46.35的47个唯一backfilled URL全部被query-local同URL先占，最终 `surviving_backfilled_union_lead_count=0`。它们没有进入下游candidate，因而V2.46.35的Composite变化不能归因于backfill。provider citation title即使暂时进入discovery lead，也会在fetch成功后被页面title/text替换；fetch失败时又没有active-evidence资格。继续优化这个表面计数不会产生可归因的task utility。

V2.47.14/18 又产生了一份完整 `220/220` candidate prediction/result，但没有形成新的质量前沿。V2.47.14 在 frozen V2.42.67 predictions 上执行稀疏 World Bank adapter，runtime 只接收 `{opaque_id, question}`。4 个 bulk ZIP 中 3 个成功，`AG.SRF.TOTL.K2` 在 30 秒超时；唯一 route-eligible 题因此 fail closed。完整 pass 用时 `30.199208s`，model/search/per-country requests 均为 0，applied tasks 为 0，220 个 prediction 均未改变。其 mechanism audit 是 `audit_valid=false`，因为 bulk completeness 与实际干预门失败。权威工件为 [`results/v24714_sparse_full220_forward_result_v1_20260806.json`](results/v24714_sparse_full220_forward_result_v1_20260806.json) 和 [`results/v24714_sparse_full220_forward_audit_v1_20260806.json`](results/v24714_sparse_full220_forward_audit_v1_20260806.json)。

预测冻结后，V2.47.18 在 opaque ID、prediction hash 与 prediction bytes 三层确认 candidate 和 V2.42.67 control 全部相同，因而合法复用旧 evaluator rows，新 evaluator calls 为 0。结果仍是 whole-table `7/220 = 3.1818%`、Entity `0.690909`、Row F1 `0.201856`、Item F1 `0.346810`、Column F1 `0.414591`、Composite `0.413541`，所有 delta 为 0。post-result closure audit 才是 `audit_valid=true, findings=[]`。所以现在确实已有完整 220 结果，但它是 exploratory identity result，不是 fresh full-search execution、Avg@4、benchmark improvement 或 SOTA；`30.2s` 也只是零模型 sparse pass，不能替代 V2.46.35 约 `18.96` 分钟的 full generation+evaluation 耗时。权威工件为 [`results/v24718_v24714_identity_full220_result_v1_20260806.json`](results/v24718_v24714_identity_full220_result_v1_20260806.json) 和 [`results/v24718_v24714_identity_full220_postresult_audit_v1_20260806.json`](results/v24718_v24714_identity_full220_postresult_audit_v1_20260806.json)。

V2.47.00 在 benchmark-external World Bank population 上先得到过受限的 target–value GO。frozen parser 与 expanded parser 均为 exact-table `0/12`、Composite `0.752604`；target–value arm 达到 `3/12`、Composite `0.921875`、Item F1 `0.687500`。但 V2.47.06 的可见题面审计显示，该答案权威 namespace 在 DeepWideBench 只自然覆盖 `1/220`，其余 `219/220` 没有同类显式权威来源。外部门证明 adapter 在适用域内有用，同时证明单 namespace hard-coding 不是通用刷榜路线。下一候选应解决跨题的 generic primary-identity/target–value binding 与 decision reachability，而不是继续增加 World Bank/ROR 专用规则。证据分别见 [`results/v24700_v24694_worldbank_result_v1_20260806.json`](results/v24700_v24694_worldbank_result_v1_20260806.json) 和 [`results/v24706_full220_visible_authority_scope_audit_v1_20260806.json`](results/v24706_full220_visible_authority_scope_audit_v1_20260806.json)。

V2.47 链还给出三项方法学教训。V2.47.07 的 planning probe 打开了 raw question 和 evaluator-side category/topic/language metadata；虽然没有 forward/evaluator effect，也没有把字段传给 runtime，此后链条仍只能标为 exploratory。V2.47.11 又错误要求 visible/control 原始文件同序；两者 ID 集相同却只有 3 个位置相同，V2.47.13 改为 opaque-ID 唯一 join。V2.47.15 的 active-runner observer 因 return 缩进错误返回 `None`，严格 validator 正确拒绝，V2.47.16/17 以 append-only failure/repair 保留。未来的 label-blind 边界必须覆盖设计探测的 source allowlist、输入排列不变性和 observer totality，而不只检查最终 forward prompt。对应记录为 [`results/v24707_preimplementation_probe_contamination_audit_v1_20260806.json`](results/v24707_preimplementation_probe_contamination_audit_v1_20260806.json)、[`results/v24713_v24711_protocol_order_failure_v1_20260806.json`](results/v24713_v24711_protocol_order_failure_v1_20260806.json) 和 [`results/v24716_v24715_build_observer_failure_v1_20260806.json`](results/v24716_v24715_build_observer_failure_v1_20260806.json)。

项目证据应按层解释。synthetic/build-only 测试只能证明合同和故障边界；benchmark-external gate 可以识别机制与 outer utility，但不能给 DeepWideBench 分数；dev64 是是否承担全集成本的 development gate；只有固定 220 分母、failure-as-zero 的 exact/full-220 才是完整 benchmark 结果。V2.47.00 属于第二层，V2.46.79 属于第三层，V2.47.14/18 属于第四层的 identity case。小版本在前置门终态后形成的“结论”是该门的结论，不应被写成未完成全集的性能结论。

V2.46.79–85 已完成一个固定64分母的DeepWideBench historical dev/validation schema gate，但结果为严格NO-GO。64个control全部fresh运行，仅8个expanded-schema自然触发任务fresh运行candidate，其余56个candidate精确复用同轮control。唯一有效forward在`305.128444s`完成72/72 child，0 runtime failure、0 fallback和0 model-slot timeout；8/8 schema treatment触发，7/8改变prediction。post-freeze evaluator评价64个baseline和7个changed candidate prediction，再为57个hash-identical candidate复用同一judgment，最终仍按两臂各64计分。baseline→candidate为whole-table `3→3/64`、Entity `0.718750→0.718750`、Row F1 `0.253472→0.256077`、Item F1 `0.448457→0.449156`、Column F1 `0.547557→0.547717`和Composite `0.492059→0.492925`。唯一失败门是预注册的whole-table至少`+1`，因此不授权exact-220。

这次结果进一步限制了“结构不确定性”或“熵降”作为credit的表述。离线配对诊断显示，8/8 treatment都成功应用schema，7个changed pair的whole-table与Entity却全部不变；Composite只有1正、4零、2负，固定64均值`+0.000865815`，95% paired bootstrap区间`[-0.001402, 0.004272]`跨0。显式schema可改变输出表面，但没有稳定改变事实正确性或整表完成。因此，schema entropy reduction、parser reachability或prediction change本身不能获得正task credit。下一实验必须在schema之后加入可地址化target–value evidence、确定性cell admission和独立completion check，并把expanded parser only保留为强对照。

上述差异也不能解释成expanded parser的纯因果效应。parser是在公开220题面coverage审计后形成，当前64题不是unseen人口；8个treated pair又是两次独立fresh generation，没有共享模型随机数。该结果只支持“在这次冻结工程门中观察到微小、混合的局部F1变化且无whole-table收益”。它不支持泛化、220提分或SOTA主张。权威工件为 [`results/v24679_schema_dev64_result_v1_20260806.json`](results/v24679_schema_dev64_result_v1_20260806.json)、[`results/v24679_schema_dev64_postresult_audit_v1_20260806.json`](results/v24679_schema_dev64_postresult_audit_v1_20260806.json) 与 [`results/v24685_v24679_schema_dev64_diagnosis_v1_20260806.json`](results/v24685_v24679_schema_dev64_diagnosis_v1_20260806.json)。

V2.46.51–54 提供了新的 benchmark-external 质量证据，但没有改变上述 DeepWideBench 全集分数。12个fresh ROR任务先在相同总fetch cap内形成baseline，再把最多4个fetch定向到baseline Unknown ROR cell的official ROR v2 exact-name active lookup。唯一forward在`73.045937s`内冻结24个预测；37个targeted lookup中36个得到唯一可采纳记录，1个歧义而abstain。预测冻结后的一次评价得到baseline→candidate exact-table `0→7/12`、Item F1 `0.552083→0.927083`、Composite `0.888021→0.981771`、Unknown cells `40→4`。该结果支持“identity-bound、target-bound、唯一official record驱动的Unknown recovery”在这类fresh registry任务上有正向outer utility；它不支持把任意网页的熵下降当credit，也不支持DeepWideBench或SOTA结论。

这次GO同时澄清了信息熵创新点的证据边界。36个replacement与outer quality同时改善，但实验没有计算每个evidence step的条件信息增益，也没有对单步做同状态删除、替换或Shapley干预；因此不能把质量增益归因于“高熵增步骤得到更多credit”。目前可支持的是较弱而可复验的链条：先用primary identity、target–value与唯一record约束定义可接受observation，再让post-freeze outer utility决定candidate policy是否值得保留。信息熵仍是该链条中的shadow epistemic量，而非已经验证的credit estimator。

V2.46.36 的冻结后配对诊断把这次分叉定位到“局部质量恢复不等于整表完成”。V2.46.30 的 34 个 fallback 在新调度下全部转为模型输出，该组 Composite 从 `0` 升到 `0.341235`，但整表成功仍为 `0/34`。两轮都由模型生成的 185 题反而从 `5` 降到 `4` 个整表成功，Composite 从 `0.477635` 降到 `0.458023`。这组聚合结果与 Search as Computation Allocation、Bridge Evidence、HiMPO、WikiLoop 和 step-level credit 文献的共同约束一致：局部信息、局部 F1 或执行完成度只有在终局任务价值上产生正向差值时才接近 credit。这里的比较来自同一公开任务集的两次随机执行，不是随机化调度实验，不能证明 20/8/240 对质量的因果效应。

V2.46.35 仍给出可靠性层面的直接结果。相对 32 active/8 slots/150s，20 active/8 slots/240s 将 fallback 从 34 降到 1，model slot timeout 降到 0，219/220 得到模型表；完整 forward 在 15.26 分钟完成。该结果支持把 20/8/240 固定为后续可靠性基线，却不支持继续把容量调度作为质量创新。下一阶段应在 benchmark-external 新表格任务上固定该调度与总预算，检验 schema-conditioned coverage、missing-cell retrieval、row/cell consistency verification 和 deterministic completion checks 是否同时提高 exact-table success 与 Composite。熵只能调节 epistemic prioritization；正 credit 仍需同状态反事实、独立 evidence stratum 或 outer outcome 验证。

V2.46.30 也给出一个负机制结果。40 个唯一 backfilled URL 全被既有 leads 遮蔽，没有一个进入下游候选，因而该 backfill 对本次预测没有直接作用。与此同时，32 个 `best_effort_fallback` 全部出现模型槽等待或截止时间耗尽，186 个模型生成成功则没有模型槽 timeout。冻结配置让 32 个 active task 竞争 8 个模型槽，并给每题 150 秒总 deadline；该共现诊断把下一优化优先级从“增加搜索深度”转向“限制 synthesis admission、保护 synthesis 容量并重新分配 deadline”。这仍是同一次运行的事后运行时诊断，不是随机化因果实验。

项目证据现已越过“只有 build audit”的阶段，但尚未验证熵/VOC 方法本身。V2.42.67 在严格 label-blind、预测全冻结后才开放 evaluator 的 full-220 单轮中得到 Success `3.1818%`、Entity `69.0909%`、Row/Item/Column F1 `20.1856/34.6810/41.4591%`；它仍是仓库 whole-table 最佳。V2.46.35 的 Composite 更高，但 whole-table 只有 `4/220`。V2.43.30 虽在约62分钟完成两个共享前缀 arm 的 `220/220` forward，但 pair-summary 工程门 fail closed、且 candidate 全为 identity，未授权 evaluator，不能伪装成新 benchmark 分数。V2.43.57 benchmark-external 门进一步证明 9+1 hidden-verifier runtime 在12题上稳定，却得到 parent eligible support/candidate/entropy credit 全0；V2.43.61 的 two-batch registrable-host union 随后把12题全部选满10 host，parent eligible support从0提升到2题/3组并自然产生2个 candidate，说明 coverage 干预确实改变了目标机制。但单个 hidden verifier host 将2个 candidate 全部回退，独立 entropy credit仍为0；这既可能是真冲突，也可能是单页缺失/不提及导致的低检验功效，不能解释成质量收益或 candidate 必错。下一可证伪实验应固定 V2.46.35 的可靠性调度，在全新 benchmark-external 表格任务上验证 schema coverage、missing-cell retrieval 与独立 row/cell verification；只有 exact-table success 与 Composite 同时过门，才把熵/VOC policy 与无熵简单基线做 fresh paired dev64。

2026-08-05 的 V2.45.87 又补充了一个更细的 acquisition 边界。修复 nested collector 后，唯一一次8题外部门在 `149.965s` 内得到 `8/8` worker/capability、零 timeout/nonzero/递归；pre-dedup preservation 在 `8/8` 任务触发，并保留195个同源附加候选，说明 exact-URL-before-source 去重与不可变 collector 确实可运行。但1,056个可见 lead 只有3个 title-surface hit，且全部来自已排除 source，最终 selected title hit、validator-aligned title replacement和其与 preservation 的同题共现均为0，所以严格 NO-GO。这个结果不支持“熵 credit 提升质量”，也不能证明 title validator 过严或搜索 provider 无法返回有效标题；它只把瓶颈从 collector/dedup 推进到 query surface、人口消歧后缀与 frozen title validator 的对齐。V2.45.89–93 因而在完全不增加 query/search/fetch/model 预算、不放松证据或 credit 门的前提下，把两条查询分别对齐 validator 的 full surface 与 core/initialism fallback，并完成 proof-carrying/total/private-parent build audit `72/72`。当前仍只授权全新外部协议设计，不能据此进入 dev64 或 exact-220。

V2.42.55 在 2026-08-01 12:18 UTC 把理论区分落实为可执行但仍 build-only 的 kernel。此前 V2.42.11 只预测单步 task contribution/token；它没有 finite-depth Bellman recursion，也不显式给出 pure IG、myopic terminal-loss VOC 与 descendant option value。新 kernel 在同一个 content-free、校准 transition DAG 上计算三者，并复现 high-IG/low-value、low-IG/high-value 和 myopic-zero/dynamic-positive bridge 三类反例；depth=1 与 myopic 精确等价，缺 calibration 则 abstain，cycle/unreachable/概率或预算非法则 fail closed。定向实现/审计 18/18，v3 回执 SHA f285ba53…9f447。这只证明算法合同，不证明真实 DeepWide 四层损失或 transition 已校准，更没有 runtime/dev64/exact-220 效果；因此 Search as Computation Allocation 的 novelty 边界不变：贡献候选是四层终端风险的任务化与经验校准，不是 Bellman VOC 或信息熵公式本身。

V2.42.56 又把“校准 transition”从口号变成数据合同。对 V2.41.23 源码的 schema audit 表明，其 matched-continuation aggregate 能提供 myopic terminal contribution，却不含 post-action four-layer projection、next-state target 或 transition probability；现有单步模型不能被重新命名成 dynamic VOC。新 primitive 要求 development fit/calibration task clusters 不相交，以 cluster-equal fit + Dirichlet smoothing 估计 transition，以 held-out normalized multiclass Brier gate；stop-now loss 同样只在 fit clusters 拟合、用 calibration MAE gate。任一局部失败都会让 V2.42.55 三策略全 abstain。实现/audit 17/17，回执 SHA 8c726fca…a6cf1；真实 successor dataset 和 calibrated model 仍不存在。因此它收紧了证据标准，但尚未产生方法效果。

## 摘要

“把信息熵用于搜索代理”或“给熵降大的步骤更多 credit”都不能作为本项目的核心首创主张。Semantic Entropy 已将自由文本答案聚类为语义等价类并用熵预测错误；FLARE、Self-RAG、TASR 和 Know Before You Fetch 已用置信或校准概率控制检索与停止；CuriosiTree、Conformal Information Pursuit 和 ECR 已用期望信息增益或期望熵下降选择下一动作；InfoReasoner、IGPO、IG-Search、SIGHT、TEPO 和 IGRPO 已把信息量用于搜索代理训练或 rollout 分配。更直接地，ECHO 已把后验收缩称为 epistemic credit，TRACE、LOTAPO、STAMP、RICE-PO 等分别用真值答案似然、删除干预、证据 provenance 和同状态局部分支定位 turn credit；MICA 又把结构化状态 potential 的单步下降与 Monte Carlo return 混合成跨时 credit。[178] DeepWide 侧也已出现 Table-as-Search、A-MapReduce、Web2BigTable、WebSwarm 与 SearchOS，分别覆盖持久表格状态、横向并行、递归 deep/wide 路由和 coverage-aware 调度。Forage V2 又直接研究完成边界未知时的 denominator blindness，Shared Discovery Paradox 则说明更准确的共享 posterior 若被压成重复的单一动作，可能降低群体发现覆盖。[72,73] 2026 年 7 月下旬的 AREX、Harness-G 与 Baikal 又分别覆盖“已验证约束/未解决约束”驱动的递归跟进、检索等价坍缩与非近视 credit、semantic-region bandit coverage。[76,81,82]

截至 2026-07-31，信息熵作为统一优化目标还有一个更直接的理论反例。Search as Computation Allocation 证明，mutual information 只有在终端决策为概率分布且使用 log loss 时才等于 myopic value of computation；若终端目标是零一损失或 simple regret，动作价值是 posterior best-decision improvement，也就是 knowledge-gradient 型 VOC。该文构造的有限问题中，按信息增益选中的 computation，其 VOC 可以低于最优 computation 的任意给定比例。[83] 因而，本项目更准确的核心是**以四层 DeepWide 终端损失定义 value of computation**。信息熵只在 log-loss 子问题中充当精确短视价值，在一般损失下充当诊断或代理；只有当损失有界且通过目标变量决定时，低 mutual information 才给出 myopic VOC 的单侧上界。它不能单独决定跨动作排序或 credit。

在本次检索范围内，仍有一个可验证、也可被否证的候选缺口：尚未找到工作在 DeepWide 表格任务中同时校准隐藏 anchor、未见结果质量、行资格和格值，并把这四类风险变化与结果对齐的同状态反事实 credit 联合验证。有限候选集上的低 Shannon 熵不代表开放集合完整，甚至可能是在错误 anchor 上过度确信。因此，本综述建议将创新假设收窄为：用校准的四层信念估计任务风险变化；用 evidence-set equivalence 和来源依赖图防止同义查询、镜像页面或同源记录制造虚假宽度；再通过同状态干预和 provenance 判断风险变化是否由该步骤造成、是否支持最终任务。信息量在这里是 epistemic signal，而不是自动成立的 causal credit。V2.42.11 已实现 label-blind 的单步 contribution/token controller 和真实 action-to-state runtime bridge，V2.42.55/56 分别补上 build-only finite-depth Bellman kernel 与 split calibration/source primitive；V2.42.12/13 又冻结了 selected-component publisher 与恢复协议。V2.46.30/35 已完成两次完整 220，V2.46.31–33 完成容量诊断、模拟和中性压力测试，V2.46.36 完成冻结后的聚合配对诊断；这些结果验证了可靠性调度，却没有运行四层 entropy/VOC candidate，也没有产生真实 successor calibration dataset 或 independent outer credit target。因此它们不能说明四层方法有效、提高分数或正确定位 credit。

V2.42.21 进一步把 CGDP 最接近本项目的 predicate belief 与 programmatic exhaustion 实现为独立、build-only 的 label-blind 强基线。该基线只接收 predicate/action/evidence/source-class 的 SHA-256 投影；`answer_ready` 只表示 required predicates 都有 clean page-backed support，并不表示任务成功或开放集合完整；同一 evidence class 一旦既 clean 又 contradicted 就 fail closed。它没有概率校准、四层开放世界状态、entropy/VOC、来源独立性估计、runtime 接入或 benchmark 权限。因此它只补齐未来对照，不构成四层方法有效、提分或 SOTA 的证据。

V2.42.31 将 WebSwarm 的两个缺失机制落实为可审计但尚不可运行的强对照。它冻结 `full`、`no_probing`、公开实现语义下的 `no_experience_upstream` 和保留两 scout 调度的 `no_experience_matched_schedule` 四臂。后两臂用于分离 sibling experience 内容与“取消两阶段 scout/fanout”造成的调度变化。经验只能由同一实例、同一父节点和同质 siblings 的精确两条 scout trace 生成；输出 renderer 只暴露有限通用搜索策略，signal hash、scope/parent/group hash 和任务事实均不进入 prompt。四臂绑定相同 model/search/fetch/prompt/output/total-budget contract，probe/extractor 开销纳入 ledger 并声明从总 cap 扣除。当前实现没有执行预算 cap 的 runtime，也没有独立验证 tactic 语义或 process/fact 分离，因而只能证明 schema、origin binding、重封印防护和权限边界，不证明 WebSwarm 已运行、成本匹配、质量提升或全集效果。

V2.42.32 将上述“共享总预算”声明变成可重放的 build-only 账本。四臂使用同一个九维 cap，覆盖 model calls/attempts、search、fetch、other-tool、orchestrator、input/output tokens 和 wall time；probe/extractor overhead 必须是首条 charge，来源 wall time 分别向上取整。每次 charge 由 exact schema、唯一 reference 和前向 hash chain 绑定，任一维度到顶即 hard stop，溢出、零 charge、重复 reference 以及重封印的 post-stop 追加均被拒绝。审计 replay 不再复用测试 helper，并重新核验 V2.42.31 的四个父控制文件。定向实现与审计 `20/20`、V2.42.02/31/32 联合回归 `70/70`，只证明纯 accounting primitive 和 fail-closed 边界。调用方成本未被独立测量，charge-before-side-effect 也没有 runtime wrapper 证明；当前 active-forward import 为零，所有执行权限为 false。因此该实现仍不支持 WebSwarm 成本匹配、质量提升、DeepWideBench 分数或 SOTA 结论。

V2.42.33 又把“先扣账再允许 effect”收窄为可审计的纯协议。调用方先声明九维上界，该上界完整写入 V2.42.32 账本后才生成一次性 permit；settlement 只接受不超过上界的 caller-reported actual cost，且不退回未使用 reservation。这个设计能在合同内拒绝重复 permit/effect receipt/settlement、逐维 overrun、重排删除和到顶后的新 permit，也允许多个已串行 admission 的 pending permit 乱序结清。它仍不执行或授权模型、搜索、fetch 与 orchestrator 调用，也不证明声明上界保守、provider limit 真正生效、actual cost 独立测得、外部 effect 发生在 permit 之后或 concurrent writers 使用 CAS。因此 `20/20` 定向测试和 V2.42.02/31/32/33 的 `90/90` 联合回归只支持 preauthorization journal 的机械边界，不能支持真实成本匹配、运行时先后关系、质量提升或 benchmark 结论。

V2.42.34 将 caller-reported vector 进一步拆为 provider-typed attempt measurement。七类 contract 分别冻结 logical model call、HTTP attempts、hosted-search provider actions、Tavily search calls、native fetch calls 与两类 local calls 的映射；token/tool usage 使用 `observed`、`unavailable` 和 `not_applicable` 三态，避免把接口不提供 usage 与真正的零消耗混为一谈。若某个适用维度 unavailable，结算只在该维使用已经预扣的 reservation，其他维继续采用 observed lower bound；若 observed lower bound 已越过 reservation，即使 fallback vector 表面在界内也拒绝结算。transport failure 不能携带 response hash/bytes，HTTP response 则必须同时绑定二者。该实现仍是 build-only schema：response hash、bytes、本地 counter 和 wall interval 都由调用方提供，无独立 provider attestation 或可信 clock；无密钥 canonical hash 也不能排除攻击者重写整套自洽收据。因此 `23/23` 定向实现/审计和 V2.42.02/31–34 的 `113/113` 联合回归只补齐未来同预算 WebSwarm 实验的 typed accounting 边界，不能证明真实计量、执行顺序、质量收益或 benchmark 提升。

V2.42.35 开始跨过“只有 schema、没有 effect control flow”的边界，但仍是隔离候选而非 production runtime。它在单进程 lock 内先扣 V2.42.34 reservation、commit permit/challenge，再调用 caller-supplied single-attempt callback；同一 effect 的 bounded retries 串行，不同 permits 的 callbacks 可以并发，settlement 再串行提交。异常、challenge/observation 错绑和 over-reservation 都留下 charged pending permit，禁止自动重放整个 effect；安全收据嵌入 meter/permit/invocation/attempt/measurement 完整子图且不记录 raw callback value。V2.42.36–40 分别把 local GPT-5.6、Tavily、native fetch、Azure hosted-search 和 Anthropic server-search 固定为 one callback/one transport attempt；V2.42.41 再用 `flock`、锁内 CAS、content-bound pending、file/directory fsync 与 no-clobber hard link 保存 V2.42.33 incremental events。V2.42.42 把两者接成隔离 coordinator：durable permit 先于 callback，durable settlement 后于完整 measurement；namespace/invocation 确定性绑定阻止重启后换 meter replay，所有旧 pending 与不确定 effect 都 quarantine，无关 effect 仍可并发。三处真实 `os._exit` crash cut 和同 invocation 双进程竞争支持“协作进程、同一本地 POSIX filesystem”的 at-most-once callback 边界。V2.42.43 又在冻结父层外加可注入 monotonic clock、strict retry-admission check 与 deterministic capped backoff；backoff 在父 callback interval 内执行并预先纳入 wall reservation，短 sleep、oversleep、坏 clock 与 callback/parent return 越界均 fail closed。V2.42.44 只对 settled GPT-5.6 typed value 加 strict JSON object boundary：完整 object/fence、duplicate/nonfinite/资源上限与 NFKC nested privileged-key firewall；parse failure 零 repair effect。V2.42.45 再把 native fetch 验证后的公网地址直接作为 urllib3 connection host，保留原 Host/SNI/certificate hostname，按 durable attempt index 确定性轮换，并禁用 internal retry/redirect。这排除了 V2.42.38 中“preflight 后 Requests 按 hostname 再解析”的 rebinding 窗口，但不证明上游 DNS/BGP、单 socket connect 次数、close 成功或 provider authenticity。V2.42.46 随后把三个 search provider 的输出压缩为 untrusted URL/title leads，并只让与父 hash/length 匹配的 fetch body 进入 bounded page-text projection；provider narrative、query、score、cited text、script/style 等不进入对应 projection。lead 不是 page evidence，page text 也始终零 instruction authority、零 active-evidence eligibility。fetch URL/content-type 与 search typed fields 仍未与父 response bytes 独立绑定，projection 也不证明 prompt-injection safety、真实性、相关性或来源独立性。

V2.42.47 将上述隔离组件装配为一条 exact-typed candidate runtime，但没有接入 active clients 或 benchmark runner。五种 adapter/request 配对都通过同一个 durable deadline scheduler；GPT-5.6 结果只进入 strict JSON boundary，三类 search 结果只进入 untrusted-lead projection，pinned fetch 只进入 untrusted page-text projection。public wrapper 不暴露 callback/fault hook，私有执行入口再次检查 operation、adapter exact class 和 request exact class，并从 exact class descriptor 绑定 callback，避免 subclass 或实例级 `bind` 覆写改变 dispatch。`18/18` 定向审计与 V2.42.02/31–47 的 `366/366` 父链回归只支持这些机械边界。它们没有调用真实 provider，没有独立证明 adapter 代码身份、provider authenticity、prompt-injection safety、来源独立性或 benchmark 效果。整个候选链仍不支持 hard-cancel 卡死 callback、NFS/分布式安全、真实断电、恶意同用户防篡改或 active-runtime integration，因此不能替换当前 R1，也不能启动重复 WebSwarm 全集。

V2.42.48 又在 assembly 外加入 content-free action-ref facade，但仍不是 legacy client 或 active wrapper。调用只以 caller scope ref、stage ref、operation 和 ordinal 派生 durable invocation；prompt、query、URL 与返回内容不进入 action identity。每条 effect 的 exact adapter/request/assembly、meter、deadline/backoff、token/tool/search/fetch 和返回数量上限均先冻结并在 effect 前重验；同一 action ref 换 prompt 的重放会在第二次 provider call 前失败。search lead 超额只作确定性截断，receipt 记录数量而不记录内容，lead/page 继续没有 active-evidence authority。`23/23` 定向审计和 V2.42.02/31–48 的 `389/389` 父链只证明这些机械边界；caller scope/stage ref 的语义独立性、adapter 代码身份、provider authenticity 与 schema 防重封仍未证明。09:05 UTC 的 label-blind terminal envelope 仍为 `203/220`，mapping/gold/evaluator 未读、released score 不存在，故该 facade 没有产生 DeepWideBench 提升、entropy/credit/WebSwarm 效果或 SOTA 证据。

V2.42.49 局部封闭了 caller 自由选择 action ref 的问题。每个 pristine registry 以 OS CSPRNG 建立随机实例域，固定三个 operation stage，并在 local `flock` 下为所有操作发放全局单调 ordinal；claim 经 create-exclusive file 和 file/directory fsync 持久化后才进入 V2.42.48 facade。无效请求也消耗 ordinal，transport 首次被调用时对应 claim 已可重放，public API 不暴露 action ref/callback/fault hook。`19/19` 定向审计与 V2.42.02/31–49 的 `408/408` 父链只支持该 local-POSIX 顺序边界。registry 不读取内容，因此相同请求仍是两个 action；另建 registry 可获得新域，caller 单 registry ownership、父 facade 全局不可绕过、claim→outcome durable binding、claimed-but-unstarted crash recovery、并发 effect completion order、NFS/分布式语义、代码身份与恶意同用户防重封均未证明。09:26 UTC 的安全 envelope 仍为 `203/220`，released score、提升与 SOTA 仍不存在。

V2.42.50 将一个 ledger 内的 effect 限成 single-inflight，并把 V2.42.49 claim 与完整验证后的 success receipt 持久绑定。锁从 clean-prefix 核对一直持有到 claim、provider effect 和 create-exclusive success outcome fsync 完成；因此成功前缀里 claim order 等于 outcome order。无效请求、transport 异常、provider 成功后 outcome 发布失败或绕过 ledger 的父 registry claim 都会形成 unresolved claim，之后永久 quarantine，既不自动重试也不把未知状态写成失败。`19/19` 定向审计与 V2.42.02/31–50 的 `427/427` 父链证明该 local-POSIX success-only顺序边界；它以失去同 ledger 并行换取明确顺序，仍没有 failure settlement、uncertain-effect reconciliation/provider idempotency、single-ledger ownership、父层不可绕过、NFS/分布式语义、代码身份或 active integration。09:39 UTC 安全 envelope 自然推进为 `204/220`，但 mapping/gold/evaluator 未读，仍无 released score、提升或 SOTA。

V2.42.51 进一步补上 typed provider chain 与旧 runner 调用形状之间的显式 evidence-ingress 边界。model 侧把 durable strict JSON object 转成 content-free trace/counter；search 侧绝不把 lead 或 provider prose直接交给 `add_search_batches`，而是在同一 exact ledger 内执行 lead→pinned fetch，并核对 canonical URL 等值、显式媒体类型、未截断 page、父 body hash/length、trust flags 与完整 outcome graph后才生成 admission。admission 对 runner result 的 title/URL/content-type/raw-content/query 作 SHA-256 binding，缺失、改写或字段漂移都会在 legacy ingestion 前拒绝；未知 direct fetch 在 claim 前失败。页面只被提升为可使用的 active evidence **data**，仍是 `untrusted_data=true`、`instruction_authority=false`，不证明 prompt-injection safety、事实真实性、相关性或来源独立性。`20/20` 定向审计与 V2.42.02/31–51 的 `447/447` 父链只支持 fake-only candidate bridge；无密钥重封印、URL/content-type→response bytes 的密码学绑定、exact failure usage、并行 provider、全局 ingestion enforcement、active runtime、真实 provider、dev64/exact-220 与质量效果均未证明。10:24 UTC 最新一致 label-blind aggregate 为 `206/220`，mapping/gold/evaluator 仍未读，故没有 released score、提升或 SOTA。

V2.42.52 将这条隔离链封装为可预检、可重启的 source-bound candidate package，但仍不构成实验结果。单一 pristine root 下分别建立 durable journal、action registry 和 success-outcome ledger，package initial/ready 均 create-exclusive 发布；`open` 会重放父链并继续全局 action ordinal，unresolved claim 则继续 quarantine。contract 固定 V2.42.31–52 的 22-file bytes manifest、guidance/budget/facade、parser/projection、provider endpoint/model 和资源上限；runner public operation 前重新核验。credential 仅作为 ephemeral adapter 参数，不参与 canonical hash、receipt 或持久化，但仍会留在 adapter 进程内存。这个 boundary 不能排除 source-check→effect 的 TOCTOU、已加载代码与磁盘 bytes 不一致、直接绕过 package 调父层、无密钥同用户重封或 NFS/硬件 durability。`20/20` 定向审计与 V2.42.02/31–52 的 `467/467` 父链只证明 fake model→restart→search→pinned fetch→legacy ingestion、三 provider exact 配对及上述 fail-closed 边界；真实流量、active runtime、dev64、exact-220、质量/成本效果仍全部未评估。10:52 UTC R1 自然推进为 `207/220 = 41 completed + 166 failed`，mapping/gold/evaluator 未读，因此依然不存在正式分数、提升或 SOTA。

V2.42.53 再把 V2.42.52 package 接到一个隔离的 production-shaped `DeepWideRuntime` subclass，但没有修改 active runner。公开 task surface 精确限制为 `{opaque_id, question}`；package、ready receipt、runtime config、launch limits、source manifest 与 prospective dev64 identity 被同一 contract 绑定。search 与 direct-fetch 返回在 inherited ingestion 前必须通过 V2.42.51 admission validator；更重要的是，父 runtime 在 stage 内和异常路径也会 checkpoint，因此 wrapper 在**每次 `_save` 前**重验完整 evidence store，所有 page/structured chunk 都须保留 admission-derived `source_type`，并保持 untrusted/zero-instruction-authority。pristine output、no-resume/no-selective-rerun 和三 provider exact mapping也被冻结。prospective dev64 合同要求两臂 fresh、同 64 IDs/manifest/budget、两臂 terminal 后才开 evaluator、failure-as-zero 和单 lease。`20/20` 定向审计及 V2.42.02/31–53 的 `487/487` 父链只使用 fake transport，active-forward 命中 0；真实 provider、active wrapper、dev64、exact-220 与质量效果仍为 0。11:17 UTC R1 仍是 `207/220`，因此这项工程闭环不能被写成 benchmark 提升或 SOTA。

V2.42.54 将上述 prospective gate 收窄为 create-exclusive、preparation-only launcher package，而不是另造一条活动执行器。它把 V2.42.53 audit/source/runtime/package/config 与现有 V2.42.16 protocol/activation/wait-audit逐字绑定；对 64 行可见 JSONL 和同序 ID 文件现场做精确 schema/duplicate-key/唯一性/顺序校验，只保存 bytes hash、count 和 schema。初始化只建立 control/candidate 各自空的 package/output roots与 initial/lease-intent/ready receipt；唯一预注册差异是是否启用 V2.42.53 checkpoint/page postcondition。合同要求一个既有 shared `flock` 连续覆盖两次 forward 和两次 evaluator、两臂 exact-terminal 后才读 mapping、failure-as-zero、no-resume，并保持 V2.42.16–20 优先；completion/whole-table/四项 quality/token ratio 与 material-gain 阈值也在 pair materialization 前冻结，GO 只授权未来 activation 设计而不直接授权 exact-220。public API 没有 launch/lease/evaluator/task 方法；定向审计 `21/21`、V2.42.02/31–54 父链 `508/508`，receipt SHA `50b78b7a…d5a03`，全部是 local fake replay。11:54 UTC R1 仍为 `208/220`；本实现没有 dev64 结果、正式分数或效果证据。

V2.42.36 为最关键的 GPT-5.6 reasoning-model path 补上首个 single-attempt adapter。它只允许本机 `127.0.0.1:9878/responses` 和 `gpt-5.6-sol`，禁重定向并关闭 Requests 环境代理/`.netrc`；一次 callback 在源码中只有一个 POST call site，429/timeout 等 retry 由 V2.42.35 在新 attempt invocation 下调度。成功必须同时有 text 与 observed nonzero usage；缺 usage、invalid JSON 和 empty output 都不是零成本成功。fake-transport 审计实际重放了 429→200 两个 callbacks/两个 POST，receipt 不含 raw prompt/answer。新增 public `single_attempt` 入口的 reservation-bypass 回归后，定向实现/审计为 `23/23`，V2.42.02/31–36 全链为 `160/160`；这些结果只证明本地 adapter 的机械边界，没有调用真实 9878、没有证明 challenge 被 provider 消费或 response hash 具真实性，也未覆盖 hosted search、Anthropic、Tavily、fetch、crash durability 或 dev64 质量效果。

V2.42.37 再补 Tavily Search single-attempt adapter。官方 Search endpoint 的 Bearer 认证允许 credential 留在 ephemeral header 而不进入 canonical request body；adapter 按 sealed attempt index 轮换 caller-supplied credentials，并把 401/403/432 与普通 retryable HTTP 分开。它不读环境、文件或 keyring，但 credentials 会在 adapter 进程内存中保留；query 含 credential 时 pre-POST 拒绝，response 直接回显 credential 时在 hash 前拒绝。同一次 Tavily result 的有限 relevance score 被保留，但静态审计限制为 decoder 中唯一一次读取，不能充当 benchmark/evaluator signal。`432 → 200` fake replay 证明两个 callbacks 对应两个 POST 和两个不同 credential，query/answer/result/page/key 均不进入 receipt。定向实现/审计为 `19/19`，V2.42.02/31–37 全链为 `179/179`；这仍没有调用真实 Tavily API，也没有证明 provider challenge consumption、response authenticity、total deadline、active runtime 集成或 benchmark 效果。

V2.42.38 将 native page fetch 拆成单 callback 单 GET。每次 attempt 都先解析 hostname，并在任一地址非 global 时拒绝；不跟 redirect、保留 bounded response prefix、启用 TLS verification 并关闭 Requests 环境继承。这个实现刻意不把 DNS preflight 包装成完整 SSRF 证明：解析结果没有 pin 到 transport，DNS rebinding 仍可能；prefix cap 也不等于总传输量硬上限，截断时 response hash 只覆盖 retained prefix。常见敏感 query key 会 pre-GET 拒绝，但不能独立证明任意 caller URL 无秘密。fake replay 为 `500 → 200` 两次 DNS preflight/两个 GET；定向实现/审计 `17/17`、V2.42.02/31–38 全链 `196/196`。这些仍只是隔离机械边界，没有真实 fetch、active runtime、dev64 或 benchmark 证据。

V2.42.39 将 Azure Responses hosted search 拆成单 callback 单 POST，并同时计 HTTP search attempt、provider tokens 与实际 `web_search_call` actions。缺 usage/action/text 不得成为零成本成功；provider action 超过 reservation 时保留真实 attempt observation，再由 settlement fail closed，而不是掩盖已经发生的超额 effect。它仍不能在 effect 前硬限 provider action、证明 input-token reservation、验证多 query marker 完整性或把 action 当页面证据。fake `429 → 200` replay 支持定向实现/审计 `16/16`，V2.42.02/31–39 全链为 `212/212`；没有调用真实 9878、没有 active integration、dev64 或 benchmark 效果。

V2.42.40 再把 Anthropic Messages server search 拆成单 callback 单 POST，并保留现有 one-query-per-request、forced `web_search_20250305` 与 query-local provenance 语义。credential 由 caller 显式传入且只进入 `x-api-key` header；adapter 不读环境/keyring，request/response 中的直接 credential 回显分别在 POST 前和 response hash 前拒绝。计量把 direct/cache-creation/cache-read tokens 合并为 input cost，并交叉验证 `usage.server_tool_use.web_search_requests` 与实际 `server_tool_use` block 数；不一致时取较大计数后 fail closed。provider 超声明 `max_uses` 也只是在 effect 后被发现，不能声称 pre-effect hard cap。fake `429 → 200` replay 支持定向实现/审计 `17/17`、V2.42.02/31–40 全链 `229/229`，现有 Anthropic client 契约另为 `8/8`；没有真实 Anthropic 调用、active integration、dev64 或 benchmark 效果，server result 仍只是 discovery lead 而非 page evidence。

V2.42.22 又把 fixed evidence-sufficiency termination 写成独立 build-only 对照。catalog 声明 coverage/source/time/exclusion criterion、动作类和 clean evidence/source 阈值；当前 active page contradiction 阻止该 criterion 满足，硬预算耗尽只允许 abstain。该实现不含 entropy、概率 belief 或 evaluator 信号，因而能在未来同预算实验中检验四层 VOC 是否真正优于固定完成条件。其哈希与空 supplied trace 只能验证 schema、绑定和调用内时序合同，不能证明 criterion 的语义来源、调用外真实时序或 active-evidence snapshot 完整性；当前也没有 benchmark 效果。

V2.42.23 修正了旧 OWIC 加法原型的一个实现风险。旧公式可能让 entropy、provenance 或 cost 项翻转终局 contribution 的方向；新 build-only kernel 只接受至少 3 次 fixed continuation 的同状态、有效、in-overlap、非 OOD、post-terminal outcome-verified contribution，并把其均值作为唯一符号来源。entropy 的正负只记录“收缩/扩张”，调幅时使用绝对量；provenance 与 cost 也只改变有界幅度。这样，权威反证即使提高 entropy，只要减少终局损失仍保留正 credit；相反，大 entropy drop 也不能把负 contribution 翻正。该 kernel 的 `19/19` 定向测试与 `82/82` 联合回归只证明合同与公式，不证明 intervention 真实有效、Gate 2B 通过、训练有益或 benchmark 提分。

V2.42.24 进一步封闭了 V2.42.23 的证据来源，但没有扩大科学主张。它不再让调用方直接选择 validity booleans，而是逐项验证 V2.41.23 的 exact manifest/bundle、六个 terminal/evaluated receipts、六个 terminal states、prediction-freeze artifact、post-freeze provenance binding、三个 contribution records 与 enriched aggregate，随后才构造 verified contribution。失败分支仍按 unit loss；缺失/重复 receipt、跨 manifest/bundle/replicate/protocol、freeze/provenance 漂移、重新 seal 的符号翻转以及 terminal state 中的 evaluator-only metadata 都 fail closed。其 `8/8` source tests、`5/5` audit tests 和 build-only 回执只证明机械 source graph 闭合；它没有独立重放 live evaluator provenance，也没有证明 intervention 的语义正确性、state overlap 的分布含义或 semantic/distributional OOD。

V2.42.25 把 TRIAGE v3 的最强直接对照实现为独立 build-only baseline，而不是把其论文结果转述为本项目证据。实现固定四个角色常数 `(1,0.5,-0.1,-0.5)` 和加法式 `A_role=A_outcome+λc_role`；role judge 的局部窗口最多包含前后各 5 个 action–observation pair，但不含 final verifier outcome。outcome advantage 由独立 post-terminal receipt 绑定，verifier 也不可见 role label；λ 只能在预注册 training split 选择，且 judge call/token 成本必须计账。这个忠实实现揭示了一个关键差异：TRIAGE 的 additive correction 能翻转较小的 verifier advantage，而 V2.42.23 只允许信息量改变幅度、不能改变终局贡献方向。因此 TRIAGE 是 future Gate-2B/training 的必要强基线，却不是 causal attribution oracle；角色语义是否判断正确、是否改善训练或 DeepWideBench 仍无真实证据。

V2.42.26 又发现了比符号翻转更隐蔽的验证风险。V2.42.23/24 从同一组终局 continuation 计算 contribution，再把该 contribution 用作 credit 的符号来源。如果 Gate 2B 仍用同一 contribution 计算 signed accuracy 或 Spearman，指标会机械奖励定义内的一致性，不能作为 held-out credit 定位证据。新的 build-only firewall 因此把 fit、calibration 与 audit task clusters 分开，先在 inner continuation graph 上冻结 credit prediction，再用语义步骤和 manifest 相同、但 freeze、provenance、evaluated receipts、contribution records、aggregate 与 arm graph 全部不重用的 outer continuation graph 构造评价目标。数值恰好相等不构成 artifact 复用；同一 source graph 充当 target 则 fail closed。该实现和 `193/193` 联合回归只证明 API 和 artifact-hash 合同可执行，不独立证明真实 wall-clock 创建顺序、semantic equivalence 或 distributional OOD。真实 outer pairs、正式 Gate 2B、训练效果与 benchmark 提升仍为 0。Auto Research 的 inner-freeze/outer-holdout 是最接近的方法学近邻，[140] 但它不替代 live-web step credit 所需的逐 artifact 独立性；TRIAGE 和 Counterfactual Shapley 又分别提供角色修正与可重置环境中的因果上界。[175,176]

V2.42.27 将 V2.42.26 的逻辑先后关系收紧为仓库内 create-exclusive 状态机：prediction commitment 先发布，随后发布 launch receipt，再创建固定 SHA-256 namespace 的 outer root 并写 reservation receipt，之后才允许写 outer pair 和 reveal。最终 reveal 绑定 commitment、launch、reservation、pair 及五个 stage file 的 bytes hash；stage 文件拒绝符号链接、硬链接、额外 residue、重复或半写后重试和重封印篡改，本地文件和父目录也做 fsync。该机制只支持 store API 强制的物化顺序；无密钥 SHA-256 seal 不能独立证明 API 真被执行，也不能在密码学上排除事后伪造整套自洽 JSON。它没有可信物理时钟，不能排除外部系统事先计算 target，也不声称能抵抗拥有同一文件系统写权限的恶意并发进程；V2.42.26 pair schema 还没有原生携带 launch challenge，所以 reveal 必须保留 `outer_pair_native_launch_challenge_binding_present=false`。同样需要精确披露的是，reveal validator 在 prediction 已冻结后会读取 sealed pair 中的派生 `outer_target_contribution`。这不属于同一 benchmark forward 的标签路由，但也不能被写成“控制面从不接触任何 reward-like scalar”。正式 Gate 2B 还需要 outer executor 在原生 pair/provenance graph 中回显不可预知 challenge，并由独立信任域或可信 append-only service 证明 launch-before-execution；在此之前 V2.42.27 仍是 build-only ordering primitive，不是独立性、效果或因果 credit 证据。create-exclusive audit 与 `262/262` 联合回归只支持实现和审计边界。

V2.42.28 进一步检验了“把 challenge 放进图的每层”到底能证明什么。它不改 V2.41.23/V2.42.26 历史 schema，而在外层为 request、prediction freeze、executor declaration、evaluator provenance、六个 terminal、三个 contribution、aggregate 和 final pair 建立 exact-schema compatibility envelopes。每层都绑定同一 launch challenge、namespace 和父 hash；final join 重新执行 V2.42.24 source replay、重验 V2.42.26 pair，并逐值核对 terminal loss、signed contribution 与 aggregate。该结构能拒绝 swapped challenge/request/executor、缺层、top-level-only challenge、跨 trust domain 和重封印 wrapper，但不能证明旧 payload 是在 challenge 后生成的。executor declaration 没有签名，独立 append-only trust domain 也不存在，因此 `historical_payload_after_wrapping_possible=true`，而 `legacy_payloads_are_challenge_native`、`store_api_execution_independently_attested`、`external_target_precomputation_excluded` 与 `formal_gate2b_evaluation_authorized` 全为 false。定向实现+审计 `16/16` 和 V2.42.23–28 联合 `109/109` 只支持合同、replay 和 fail-closed 边界，不支持因果 credit、训练效果或 benchmark 提分。正式 outer campaign 仍需真实 executor 消费 challenge，并由独立信任域提供 keyed/asymmetric signature 与 append-only launch-before-execution receipt。

V2.42.29 将签名问题再拆成“密码学有效性”和“声明可信性”。纯验证模块冻结 domain-separated canonical JSON statement、canonical DER RSA public key，以及 RSA-PSS/SHA-256、MGF1-SHA-256 和 32-byte salt；statement 覆盖 V2.42.28 的完整 compatibility graph。OpenSSL 生成的临时测试签名可由独立实现验过，错误 key、salt、signature、statement、pair、challenge 与非 canonical key/base64 均被拒绝。该结果只说明对应私钥持有者签过这些 bytes。没有外部身份绑定、独立控制域、append-only publication 或可信时间时，签名不能证明声明为真，也不能证明 launch 早于 execution。实现因此保留 `independent_signer_identity_verified=false`、`independent_trust_domain_verified=false`、`statement_truth_independently_verified=false`、`launch_before_execution_independently_attested=false` 和 `external_target_precomputation_excluded=false`。V2.42.23–29 实现+审计 `126/126` 仍只是 build evidence；正式 Gate 2B、训练和 benchmark 权限均未开放。

对候选 DAG 的源码级追踪也排除了一个误判：当前 R1 的 `anchor_unresolved` 与 `bridge_entity_unresolved` 失败不意味着未来 candidate 没有对应机制。schema68 已集成 V2.40.6 bridge completion 和 V2.40.7 anchor completion，schema74 进一步加入 relation-aware anchor；repo-local byte replay 证明这些机制沿 schema75/76/77 保留，并由 V2.42.15 的 deepest cumulative graph 重建。故再做一套 P9/P10 completion 会重复既有代码。正确实验问题是这些机制在 fresh paired/fullset 上是否有效，而不是用冻结 R1 的旧失败簇为平行实现提供事后依据。

最新补漏又使这一设计原则不再能单独承担新颖性。SGCD 用 detached teacher/student divergence 和 entropy 产生 `[1,2]` 的正 credit multiplier，重加权 outcome-verified policy-gradient advantage，而不增加 teacher-matching actor gradient；其 sibling evidence、external-LLM credit reference 与 verifier outcome 均限训练期，部署只接 clean prompt。[173] 因而 sign-preserving weighting 已有直接近邻。InfoSeeker 则用 Host–Manager–Worker、worker context isolation 与 MapReduce 式聚合实现层级并行，并在 20 个 WideSearch-en 查询上报告 `1→17` workers 的 wall-clock 从 911 秒降到 162 秒。[174] 该结果未同时提供等总 token/tool-call 的质量曲线，不能证明更多 worker 提高有效宽度，也不能横比 DeepWideBench。未来必须把跨题 executor concurrency、单题 worker width 与来源依赖校正后的 evidence width 分开。

最后两项遗漏使 credit novelty 进一步收窄。TRIAGE 把环境动作分类为 decisive progress、useful exploration、no-progress infrastructure 与 regression，并在 verifier/GRPO outcome advantage 上加入 bounded role-conditioned correction；训练期 judge 不看最终 verifier outcome，部署期也不调用 judge。[175] 它在 ALFWorld、Search-QA 与 WebShop 的论文设置中超过 GRPO，但 Search-QA 只报告一次固定训练配置，per-segment judge 带来显著额外成本，而且作者明确 role-aware attribution 不是 causal identification。这已占据“给信息获取/探索角色额外 credit”的直接近邻，要求本项目加入同 judge/context/cost 的 role-typed baseline。

Counterfactual Shapley Credit Assignment 则把 MDP 写成 SCM，用 baseline policy 替换 action coalitions，以 counterfactual natural total effect 构造 Shapley reward redistribution；论文证明在其设定下保留 optimal policy，并针对 sparse causality、stochastic luck 与 delayed reward 给出估计器。[176] 但它需要 resettable simulator、显式 baseline policy 和 counterfactual-independence 表示，计算仍需 `O(T·M)` counterfactual simulations；作者的实证主要是可控 MDP/模拟环境。因此它是同状态 continuation 的因果 oracle 上界，而不是 live-web 可直接运行的 controller。四层 OWIC 若要保留创新性，必须证明在不可 reset 的开放网页、未知结果集与 provenance/source dependency 下，用少量固定 continuation 能形成有用且校准的近似，而不能笼统声称首次做 causal/Shapley credit。

2026-08-01 的分类 RSS 去重与全文核验补入两个会改变实验合同的近邻。Agent-UCT v2 在离散 RAG workflow 配置树上加入由 bipartite prefix-reuse graph 计算的边际执行成本，并用 content-addressable replay 复用已物化前缀；论文报告的 `73.6%` 是相对 no-prefix-sharing 上界的 logical-cost reduction，`4.2×` 才是 sampling 相对 full-pool 的 wall-clock speedup。[177] 它不控制单题 live-web 动作，也不估计四层风险，但要求本项目分开记录逻辑配置成本、实际 API/token/wall-clock，以及复用命中前后的质量。只有 task-independent、语义不可变且 provenance 完整的前缀才能复用；当前题证据、历史 evaluator outcome 或 benchmark label 不能成为 runtime reuse key。

MICA v3 进一步占据“结构化风险下降加延迟回报”的宽泛 credit 主张。它从同一个用户支持状态 potential 构造即时 Incremental Distance Reward 与其 Monte Carlo return，经不同范围归一后形成 mixed advantage，不需要 matched-state rollout tree 或 learned critic。[178] 该方法依赖 environment-provided dense feedback，应用域是情感支持对话，不是开放网页搜索。它因此是四层风险 credit 的低成本强基线，而不是 DeepWide 的直接替代。未来训练实验必须比较 MICA-style `potential delta + return`、outcome-only、TRIAGE、同状态 outer continuation 与 OWIC，并把 dense judge 的调用和特权信息预算单列。

2026-08-01 02:43 UTC 已将这项对照落实为 V2.42.30 的 label-blind build-only primitive。实现逐式复现 `gamma in (0,1]` 的 discounted IDR return、同 prompt 同 turn 的有效轨迹 population normalization、同 prompt 全部有效即时 IDR 的 population normalization，以及 `alpha/beta` 凸混合；支持论文正文明确讨论的 variable horizon。它只接收 hash、有界 scalar 和成本计数，不读题目、网页、benchmark label、mapping、gold、reward/score 或 evaluator payload，也未接 active runtime。该实现的通过测试和 create-exclusive 审计只证明公式与能力边界，不证明四层 potential 正确、dense judge 正确、因果 credit、训练增益或 DeepWideBench 提分。WebSwarm 的递归委派、Web-Probing 和 sibling experience 继续作为系统级强对照；其单题 worker width 必须与跨题 executor concurrency 分开，并在同总 token/search/fetch/orchestrator/wall-clock 预算下比较。

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

22:25 UTC 再次查询官方 arXiv Atom 的 `agentic search`、`deep research`、`multi-agent search`、`information gain` 与 `credit assignment` 日期窗，并按 arXiv ID 与当时的 172 篇清单去重。WebSwarm、SearchSwarm、CGDP、GDCR/SAPO、SlimSearcher、AggAgent、LiveBrowseComp、DeepWeb-Bench 与 R²-Searcher 仍为 v1，SAAS 仍为 v3。23:10 UTC 沿 sign-preserving credit 与层级并行的遗漏轴全文核验 SGCD v3 和 InfoSeeker v1，将清单扩为 174 篇。[173,174] 23:36 UTC 再核官方 Atom，WebSwarm 仍只有 v1；随后全文补入 TRIAGE v3 与 Counterfactual Shapley Credit Assignment v1，清单扩为 176 篇。[175,176] 这个增量结果不证明检索穷尽；它把正值 multiplier、Host–Manager–Worker、role-typed correction 与 simulator-based causal Shapley credit 都加入必须对照的既有机制。

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
- 2026-08-01 00:33–00:34 UTC 用官方 arXiv Atom API 复核 WebSwarm、SearchSwarm、TRIAGE 与 Counterfactual Shapley 的版本链。四者仍分别为 `2607.08662v1`、`2606.09730v1`、`2606.32017v3` 与 `2607.16999v1`，其中 WebSwarm 仍标注 `Work in progress`。GitHub 公共 API 同时确认 WebSwarm main HEAD 仍为 `40c9aaca…5717`，提交时间为 2026-07-18。同一 arXiv API 对 2026-07-30 至 2026-08-01 的 `agentic search / deep research / multi-agent search / credit assignment / information gain / web search agent` 窄窗口返回 10 条。Baikal、Search as Computation Allocation、FinanceHarness、PCD、GRSD、MARS-RA 与 $\beta$-OPSD 已在 176 篇清单中；FarmSeeker、ReDiPPO 与缺乏可复核同协议链的 *DeepResearch Agent System* 经筛选后不进入核心矩阵。本轮没有发现改变 WebSwarm 同预算对照、四层风险或 independent outer-target credit 合同的新直接近邻，因此不为增加数量而加入弱相关引用。
- 2026-08-01 00:59 UTC 再用官方 arXiv Atom endpoint 逐 ID 核验上述四篇：版本仍为 v1/v1/v3/v1，标题、作者和 comment 未变。WebSwarm HTML 指向的公开仓库 `songxiaoshuai/WebSwarm` main HEAD 仍为完整 SHA `40c9aacad7cd6e9cdb3e7add954d59b766425717`，commit timestamp 仍为 2026-07-18 05:33:19 UTC。本轮没有新增引用；它把证明责任从“有没有更新版本”转回同预算机制实验和可信 outer-target 时序。
- 2026-08-01 01:47–01:52 UTC 再次用官方 arXiv Atom 逐 ID 核验 WebSwarm、SearchSwarm、TRIAGE 与 Counterfactual Shapley，版本仍为 `v1/v1/v3/v1`，WebSwarm 仍标注 `Work in progress`。随后对 2026-07-28 至 2026-08-01 的 agentic/web/deep research、swarm/parallel search、information gain 与 credit assignment 做六组日期窗查询。BM25 scaling、Self-Speculating Agent、FinanceHarness、Baikal、Search as Computation Allocation、GRSD、MARS-RA、SkillRise 与 CAST 均已包含在 176 篇清单中；其余召回没有比现有近邻更直接的四层风险或 outer-target credit 合同。因此本轮不增加弱相关引用。WebSwarm 公共仓库 main HEAD 也仍为 `40c9aacad7cd6e9cdb3e7add954d59b766425717`。
- 2026-08-01 02:10–02:17 UTC 用 `cs.AI/cs.CL/cs.IR/cs.LG/cs.MA` 官方 RSS 对现有清单按 arXiv ID 去重，并逐篇读取 Agent-UCT v2 与 MICA v3 的 HTML 正文、方法、成本表和 limitation。[177,178] Agent-UCT 增加 prefix reuse 的逻辑成本与真实成本分离；MICA 增加无需 matched-state rollout 的 structured-potential/return credit 强基线。Actions Have Consequences、GuidedRAG、UrbanDS、AgentMap 与 Evidence-Ledger Adjudication 经筛选后只与因果检测、语义检索、领域多代理、ontology matching 或 claim adjudication 相邻，没有改变四层 live-web risk/credit 缺口，故不为扩大篇数加入核心清单。同一轮逐 ID 核验确认 WebSwarm/SearchSwarm/TRIAGE/Counterfactual Shapley 仍为 `v1/v1/v3/v1`，WebSwarm 仍标注 `Work in progress`；其公共 main HEAD 仍为 `40c9aacad7cd6e9cdb3e7add954d59b766425717`。广域 Atom 查询一度返回 `429`，因此本轮只声明 RSS 与定向全文范围，不声称检索穷尽。
- 2026-08-01 03:06–03:17 UTC 再次逐 ID 读取官方 arXiv HTML，确认 WebSwarm、SearchSwarm、Agent-UCT 与 MICA 分别仍为 `v1/v1/v2/v3`；`git ls-remote` 确认 WebSwarm public main 仍为 `40c9aacad7cd6e9cdb3e7add954d59b766425717`。广域 Atom 查询先后超时与返回 429，后续仅用官方分类页做标题补查；召回的 MANTA、perception credit、FinanceHarness、Harness-G 与 SimpleWikiSearch 均已在 178 篇清单中。本轮不新增引用，也不声称检索穷尽。V2.42.31 的四臂 build-only 实现只把已知 WebSwarm 机制变成可审计对照，不改变 novelty 结论。
- 2026-08-06 用官方 arXiv Atom 元数据逐 ID 核验 8 月新增的 Router-Mem、EASy、SIEVE、Long-Horizon Search Diagnosis、ScrambleToolBench、Deep Research Pretraining 与 RubricRanker，并复核 RARG v2。[79,179–185] RARG 已是原清单 [79]，因此本轮是 7 篇净新增，参考文献总数为 185，而不是重复计数后的 186。WebSwarm 与这些论文的作者报告仅用于机制和实验合同：不同模型、工具、任务子集与预算下的数字不与本项目分数直接横比。广域关键词查询受到 arXiv endpoint 限流，本轮不声称检索穷尽。
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
| SGCD (2606.12634v3) | mixed success/failure sibling 形成 training-only credit reference；detached divergence/entropy 产生正 multiplier | 需要 sibling verifier outcomes 与 external-LLM reference，但部署只见 clean prompt | 否；`[1,2]` multiplier 只保留并放大 outcome advantage 的既有方向 | sign-preserving credit weighting 已有直接近邻；OWIC 必须比较 SGCD，并证明四层开放世界 task risk、同状态终局 intervention 与 provenance 的额外价值 [173] |
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
| structured potential drop + Monte Carlo return | 高，但依赖逐步 dense feedback | 很低；MICA 与 SIOP 已覆盖 potential/return credit | 强基线，单列 judge 与特权信息成本 |
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
| Router-Mem、EASy | evidence sufficiency；executor capability、cost 与 milestone dependency | 提前停止、执行调度 | 是 | 否 | 充分性路由和成本感知编排已有；本项目须把吞吐、fallback 与任务质量联合设门 [179,180] |
| CuriosiTree、C-IP、ECR | 决策/标签/答案假设 | 推理控制 | 是，按 EIG/EER | 通常固定有限集 | EIG 动作选择与熵停止已有 |
| Evidence-aware termination、ScaffoldAgent | 预声明的证据充分性条件；evidence-indexed outline 与复合 downstream utility | 推理控制 | 是，继续取证或扩张/收缩/修订 outline | 否 | 显式充分性停止、utility-guided structure 与边际收益停止已有；四层方法必须证明校准终端风险的增量 |
| RARG、SIEVE、RubricRanker、Long-Horizon Search Diagnosis | relevance execution prior、网页 section、query-specific document-set rubric、累计证据 recall | 检索排序、局部 fetch、集合选择与轨迹诊断 | 是 | 通常否 | 更多搜索量不等于更高质量；必须区分 retrieval gap、utilization gap、集合覆盖与上下文浪费 [79,181,182,185] |
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
| Deep Research Pretraining、ScrambleToolBench | evidence-graph predictive navigation；隐藏工具映射与环境漂移 | 离线预训练、交互适应评测 | 学习后或推理时控制 | 动态环境但非开放结果集 | predictive navigation 已有，额外 test-time compute 也可能放大穷举；容量干预须与策略改进分开 [183,184] |
| MisKnow-Agent、FinanceHarness | 误导证据采用、lifecycle、PIT corpus 与工具契约 | reliability injection、时间隔离、rubric | 评测/训练 | 固定 corpus | truthfulness、时间污染与 tool shift 必须单列，不能被 entropy/coverage 指标吸收 |
| TaS、A-MapReduce、Web2BigTable、VecTree-RAG | 行、格、横向子任务；语料与文档结构 | 推理系统 | 是 | 启发式或固定语料覆盖 | 表格状态、大规模宽搜与两级结构检索已有 |
| WebSwarm、SearchOS、InfoSeeker | 搜索节点、网页结构、coverage/gaps；Host/Manager/Worker 层级状态 | 推理系统 | 是 | 定性 open-set / scope audit | 动态 deep/wide、覆盖驱动调度与层级并行已有；高并发必须做等总预算和 effective-width 对照 [174] |
| GRSD、SGCD、OVCSD、CSCR | outcome group、training-only credit reference、state-aligned teacher continuation、opposing-outcome sensitivity | 训练 credit | 学习后控制 | 否 | verifier-sign-preserving weighting 与 outcome-aligned 局部蒸馏已有；entropy/teacher shift 只能调幅，不能成为方向来源 [95,97,98,173] |
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

Gate 2B 还必须把 prediction source 与 evaluation target 分开。Inner campaign 可从固定 continuation 产生用于预测构造的 contribution，但在 prediction freeze 之后，signed accuracy、Spearman、calibration 和 pivotal-step recall 只能针对新的 outer campaign 计算。两次 campaign 共用预注册 manifest contract、语义步骤、模型、预算和 continuation policy，以控制可比性；它们的 freeze、evaluator provenance、terminal receipts、contribution records、replicate aggregate 与 arm graph 必须全部不交。fit、calibration 与 audit task clusters 也必须两两不交。相同任务的重复 rollout、同一 contribution 的重新封装或同一 source graph 的别名都不能充当 independent confirmation。这个要求把 Auto Research 的 outer-holdout transfer 原则推进到 step-credit artifact 层，[140] 并防止 outcome-anchored credit 在自己的定义目标上机械自证。

### 9.7 信息与任务价值是否错位

构造至少三类 state-matched case：高 IG 但低 terminal-loss reduction、低 IG 但高 regret reduction，以及 myopic value 为零但能开启高价值 descendant computation。比较 RelIG、myopic VOC、learned dynamic VOC 与 oracle rollout value 的排序、top-1 regret 和 calibration。若 pure IG 与 task value 的排序差异没有在真实轨迹或构造反例上复现，论文只能将 VOC 作为理论动机；若复现，则 controller 的主消融必须报告差异来自 terminal loss，而不是换了更多 features。

### 9.8 误导证据、时间污染与工具漂移

对不含 benchmark label/gold 的审计集注入语义相关但受控错误的来源，改变 source dependency、authority-like presentation 和进入 research state 的阶段，并测 false-claim adoption、完整证据链率、四层 risk calibration 与独立验证召回。DRNOISE-style paired clean/noisy 条件还要区分 retrieval miss、truth found but incomplete route、complete-route override 与 reconciliation failure，避免把所有采用错误直接断言都归因于检索。[145] 另做 point-in-time 或固定 snapshot 复现实验，记录知识快照、页面清洗与切块、索引字节、检索/融合后端、tool schema、observation truncation、提交规则和搜索截止时间的环境指纹。SimpleWikiSearch 说明这些变量本身足以改变 agentic-search 结果；任何只在 live web、合成语料、单一 snapshot 或单一后端成立的增益都必须标为环境依赖结果。[87,88,145,148]

### 9.9 自适应机制是否真实执行、且是否优于简单算力分配

对每个名义 adaptive 系统报告实际执行路径。至少记录各 route 的触发频率、每题 agent/round 分布、提前停止中的错误比例、曾出现正确中间态但最终被覆盖的比例，以及按 query、URL/content、evidence set 和 source dependency 修正后的有效独立分支数。主对照加入相同生成 token 的独立搜索样本、DivInit-style first-turn diverse seeds、相同 tool-call 的随机 region/agent allocation 和相同 wall-clock 上限的并行采样。[143] 另加 SwarmResearch-style depth-varying allocation，与相同 worker iteration、总 token、工具调用和 orchestrator 开销的最佳固定 width×depth 比较；它在代码优化上的 4/5 结果只用于预注册该对照，不构成 DeepWide 方向先验。[147] 层级系统还要独立扫描 delegation/planner 与 execution/child 的模型容量，不能默认所有角色使用同一模型最优；Think Big, Search Small 的摘要结果提示容量敏感性可能集中在 delegation，但这一结论仍需在 DeepWide 上按同预算重测。[120] 在线控制采用两段式决策：先按预期 task/resource advantage 排序候选 workflow，再以独立 margin 决定是否替换 factual workflow，防止“best candidate”在所有候选均有害时仍被执行。[119] 若 adaptive 组件很少触发，或其质量–成本点不超过简单采样 Pareto 前沿，结果只能支持“系统可运行”，不能支持 controller 或 swarm 机制有效。[104–109,119,120,143,147]

## 10. 对当前项目的直接诊断

截至 2026-08-06，当前已完成的最新框架是 V2.46.35 exact-220，而不是继续等待 V2.42 watcher。每题的前向边界严格为 `{opaque_id, question}`，执行链为 `plan → 最多两波 2+2 logical queries → 最多 6+4 fetch → evidence projection → synthesis → 必要时 repair/recovery → prediction freeze`。220 个预测全部冻结后，独立 evaluator 才能读取 mapping 和答案语料。跨题 active child 为 20，全局模型槽为 8，每题总 deadline 为 240 秒。该配置的 forward 为 `915.58s`，evaluator 为 `222.24s`，顺序相加约 `18.96min`。

项目结果必须按证据等级解释。V2.46.30 与 V2.46.35 都是 220 题、固定分母、failure-as-zero 的 benchmark 结果；V2.46.36 是两者冻结后的 aggregate-only 诊断，不是第三次 benchmark。V2.46.79 是历史 dev/validation 人口上每臂固定 64 分母的方向性 gate，不是新的 full-220 或 unseen 结果；8/12/16 题 external gate 使用 benchmark-external 人口，只能判断机制是否可达；build、unit 和 fault-injection 使用 0 道 benchmark 题，只能证明工程合同。版本号增加不等于多次取得 benchmark 分数。V2.43.30 虽完成 220 题 forward，但未通过 pair-summary 工程门且没有 evaluator，因而没有可报告的质量结论。

V2.46.30 的检索扩展没有形成下游作用。40 个唯一 backfilled URL 全被已有 leads 遮蔽，最终 surviving candidate 为 0。该版本的 34 个 fallback 与 slot/deadline 饱和共现，促成 V2.46.32–35 的 benchmark-external 容量模拟、GPT-5.6 中性压力测试和 20/8/240 successor。V2.46.35 将 fallback 降到 1、model slot timeout 降到 0，却只得到 `4/220` 整表成功。V2.46.36 又显示 34 个被恢复为模型输出的旧 fallback 任务仍为 `0/34` 整表成功。容量编排问题已经缓解，下一优先问题因而变为 exact-table objective alignment，而不是增加 query、fetch、backfill 或继续压 fallback。两次公开集运行不是随机化调度实验，不能建立质量因果效应。

以下 V2.42.11–29 内容保留为历史控制面和 credit 研究轨迹，不代表当前运行状态。完整 Risk-DeepWide/OWIC-DeepWide 方法仍未产生质量增益证据。V2.42.11 把纯 entropy/VOC kernel 接到三个冻结决策 context 和九个 context–action 组合；action 分支执行真实的两查询 observation、V2.41.22 provenance-preserving state adapter 与有界幂等 restart，stop/abstain 则只写双层 sealed receipt。runtime 构造只接收已绑定的模型、job manifest 和 selected-parent manifest，不读取环境变量、benchmark label 或 evaluator artifact；未发布 package 仍 fail closed。

V2.42.12 publisher 覆盖 18 个 entropy 决策和 14 个唯一 parent byte graph，并为目标 schema 87–100 生成独立 rebase 合同。首次 activation 因 successor 错用了 V2.42.10 的 frozen-false 字段名而 fail closed；它没有打开 selected work order/report/model，没有创建 publication/candidate，没有取得 lease，也没有调用模型、搜索或 evaluator。失败 activation/state 已封存且禁止原协议 restart。V2.42.13 只修正这一字段名，并在新的 protocol、activation、state、publication 与 candidate namespace 中恢复。V2.42.15–17 又依次冻结 joint-package recovery、fresh paired dev64 gate 和 neutral capacity successor。V2.42.18 已冻结并激活唯一 single-owner exact-220 executor，但仍停在 `waiting_for_v24216_package_gate_terminal`。其 execution-start、四个 fresh roots、lease、preflight、forward、mapping/evaluator 和 result 均未出现。

V2.42.19 又冻结了 post-terminal、label-blind contamination scanner。其 protocol/decision/12-file manifest SHA 为 `d7923f65…e0a61 / c5dcbea7…c0c4 / 4784cb91…5737`，activation/wait-audit SHA 为 `3355de78…a8759 / 38f2d222…fbeaa`。watcher PID `3141508` 当前只读 V2.42.18 的 preterminal safe envelope，未打开 task manifest/evidence，未创建 detail/report，也没有 lease、网络、模型、搜索或 evaluator 调用。它扫描的是 runtime 持久化的 query-focused page evidence，不是未保存的整页原文，因此不能证明网页未留存部分不存在污染。这条供应链证明实现边界可审计，不证明 calibration、controller quality、credit validity、污染率或 benchmark 提升。

V2.42.20 在 V2.42.19 之后冻结来源依赖审计。其 protocol/decision/12-file manifest SHA 为 `7297cd10…a6555 / 63e11c55…53290 / 0402f617…7bf7`，activation/wait-audit SHA 为 `cb3dbdc9…744c / e5c5f8c8…fb40`。watcher PID/start ticks `3216528/748157819` 当前只读 V2.42.19 的 preterminal envelope；task evidence、detail/report、网络/API、lease、forward 与分数路径均未打开。该实现把 exact/near-duplicate 和强镜像连成硬簇，对同源、共享 quote、结构化记录与路径镜像另做软折扣；同 host 本身不触发硬合并。它只能给出 dependency-adjusted sensitivity，不能证明页面来源真的独立或支持答案，也不会从官方主分数中删题。

production runtime 只读取 `{opaque_id, question}`，支持 Tavily、Azure hosted 和 Anthropic hosted search、持久 JSON state、开放集 anchor/`OTHER`、scope/candidate discovery、mention recall、逐行/逐格查询、cell-level provenance、行级 quarantine、单位尺度审计和确定性表格渲染。V2.42.23 已在 freeze import graph 外实现 verifier-sign-preserving modulation，V2.42.24 绑定 sealed source graph，V2.42.25 提供 TRIAGE role-typed 对照，V2.42.26 拒绝同一 source contribution 充当 Gate-2B target，V2.42.27 提供仓库内 commitment/launch/reservation/pair/reveal 顺序，V2.42.28 把 launch challenge 和父 hash 贯穿 compatibility graph，V2.42.29 则验证完整图的 detached RSA-PSS signature。active runtime、entropy runtime、runner 与 launcher 都不导入这些 build-only credit 模块。V2.42.29 的 create-exclusive v2 审计为 `audit_valid=true / build_only=true`，文件 SHA 为 `b72002b7…856ba`；V2.42.23–29 实现+审计联合回归为 `126/126`。这些结果只支持合同、seal、replay、仓库时序、签名字节有效性和静态能力边界。尚缺的关键证据仍是真实 development calibration bundle、由 native executor 消费 challenge、由仓库外独立 trust domain 签名并 append-only 发布的 inner/outer intervention pairs、双父终态选择、joint package regression、dev64 package gate 和 fresh exact-220 结果。开放集合仍只有未校准 proxy；credit training、正式 Gate 2B 与 RL pilot 均未开始。

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

泄漏审计发现旧 smoke 脚本曾把生成与本地近似 gold evaluation 放在同一进程。新 runtime manifest 已限制为 `{opaque_id, question}`，预测完成后再由独立 evaluator 读取 instance ID、subset label 和 gold table；测试覆盖 manifest 边界、anchor replay provenance、identity support、闭合行域防伪、通用 verifier、Tavily key 轮换、历史迁移版本、evidence continuity、checkpoint drift、evaluator retry、targeted no-op 和并发故障 trace。V2.46.30 的 prediction-freeze 与 post-result audit 已证明本次前向没有读取 mapping、gold、category、question type、split、evaluator 或 score，31 项审计检查通过。本地免 key GPT-5.6 已用于该全集；Azure hosted search 仍有历史偶发 429。正式投稿还需人工确认 contamination audit 的 EAL candidates，并补整页 capture/精确 span、跨进程文件权限与未持久化页面盲区审计。

## 11. 结论

信息熵适合作为这项工作的理论主线，但不能作为孤立 novelty。已有文献已经覆盖语义熵、信息增益奖励、EIG 动作选择、熵驱动证据选择、校准停止、未知 denominator 审计、belief–coverage 分离、POMDP acquisition、gold-conditioned contextual-IG credit、answer-graph credit、shared-prefix suffix credit、verifier score-to-credit、Bayesian belief revision、execution hindsight、Shapley attribution 与 sign-preserving advantage modulation。[140,149–151,157–191] 限定到本次 191 篇公开文献核验范围，可辩护的候选问题是：DeepWide 的隐藏 anchor、开放集合遗漏、行资格和格值能否形成一个经校准且不简单相加的任务风险模型；该模型能否在相同动作菜单、共享前缀、预算、证据等价与来源依赖约束下改善 terminal task loss；若进一步训练策略，四层风险变化能否预测由同状态 suffix 或 artifact-disjoint outer continuation 确认的 signed step contribution。

V2.48.00 当前是仓库内单轮完整 220 的联合前沿，whole-table 为 `8/220`、Composite 为 `0.456834`。V2.48.01 的 95% task-bootstrap 区间跨 0，且成本增加约 `40.86%`，所以这份内部提升不能被解释为固定 full budget 的普遍因果收益。V2.48.02 又表明，在 WebSwarm 的精确 76-task manifest 上，两者 SR 在论文报告精度下相同，而 Row F1 与 Item F1 各有胜负；由于模型、工具、预算与 evaluator 不匹配，这也不是 SOTA 对照。

下一步应在 benchmark-external、task-cluster-disjoint 人口上冻结共享前缀三臂：first-wave only、fixed full budget，以及 coverage-risk/terminal-loss VOC adaptive。三臂必须共享模型、renderer、候选证据顺序与 hard caps，并报告固定分母质量、成本、evaluator health 与 task-cluster bootstrap。四层 entropy/VOC 只有在该候选优于两个强控制，且 step sign 又由 same-state suffix/deletion/replacement 或独立 outer utility 支持时，才可升级为经验核心；否则保留为 uncertainty diagnostic。真实四层 calibration、正式 outer-valid step-credit 数据与 credit-training 收益目前仍为空。

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
79. Li, J. et al. **A New Role for Relevance: Guiding Corpus Interaction in Agentic Search.** arXiv:2607.24223v2 (2026). https://arxiv.org/abs/2607.24223
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
173. Ding, T., Xin, J. & De la Cruz Weinstein, J. P. **Keep Policy Gradient in Charge: Sibling-Guided Credit Distillation for Long-Horizon Tool-Use Agents.** arXiv:2606.12634v3 (2026). https://arxiv.org/abs/2606.12634
174. Lee, K. Y. et al. **InfoSeeker: A Scalable Hierarchical Parallel Agent Framework for Web Information Seeking.** arXiv:2604.02971v1 (2026). https://arxiv.org/abs/2604.02971
175. Xu, Y. et al. **TRIAGE: Role-Typed Credit Assignment for Agentic Reinforcement Learning.** arXiv:2606.32017v3 (2026). https://arxiv.org/abs/2606.32017
176. Li, M., Kaizhan-Lee & Bareinboim, E. **Counterfactual Shapley Credit Assignment.** *Reinforcement Learning Journal* / RLC (2026); arXiv:2607.16999v1. https://arxiv.org/abs/2607.16999
177. Li, Y. et al. **Agent-UCT: Upper Confidence Bounds Applied to Trees for Agentic Workflow Optimization with Cost-Awareness.** arXiv:2607.24162v2 (2026). https://arxiv.org/abs/2607.24162
178. Zhang, N. et al. **MICA: Multi-granularity Intertemporal Credit Assignment for Long-Horizon Emotional Support Dialogue.** arXiv:2603.06194v3 (2026). https://arxiv.org/abs/2603.06194
179. Lin, Y., Wang, K., Lou, J. & Li, J. **Stop When Memory Suffices: Evidence-Conditioned Progressive Execution for LLM Agents.** arXiv:2608.01285v1 (2026). https://arxiv.org/abs/2608.01285
180. Liu, J., Luo, L., Vu, T.-T. & Haffari, G. **EASy: Towards Efficient LLM-Based Agentic System.** arXiv:2608.04588v1 (2026). https://arxiv.org/abs/2608.04588
181. Wang, S., Chen, H., Yin, Y., Zhuang, S., Koopman, B. & Zuccon, G. **Search, Inspect, Fetch: Exploiting Structure-Aware Boolean Retrieval for Deep-Research Agents.** arXiv:2608.02751v2 (2026). https://arxiv.org/abs/2608.02751
182. Liu, Q., Mao, J., Zhu, F. & Chua, T.-S. **Diagnosing Search Behavior and Failure Modes in Long-Horizon Search Agents.** arXiv:2608.01913v1 (2026). https://arxiv.org/abs/2608.01913
183. Toh, V., Majumder, N., Liu, Z., Chen, N. F. & Poria, S. **ScrambleToolBench: Agents Search Exhaustively Even When Their Own Map Points to the Next Step.** arXiv:2608.02358v1 (2026). https://arxiv.org/abs/2608.02358
184. Zhou, J., Fan, Z., Wu, X., Yu, T., Zhang, F. & Wang, L. **Deep Research Pretraining via Predictive Navigation.** arXiv:2608.00432v1 (2026). https://arxiv.org/abs/2608.00432
185. Liu, W. et al. **Training Documents Reranker with Search Rubrics for Deep Research Agent.** arXiv:2608.03527v1 (2026). https://arxiv.org/abs/2608.03527
186. Lu, Y., Ye, R., Wang, J., Du, Y., Jin, T., Liu, S. & Chen, S. **ABSeeker: Training Long-Horizon Search Agents via Answer-Backtracked Credit Assignment.** arXiv:2608.05102v1 (2026). https://arxiv.org/abs/2608.05102
187. Liu, Y., Wang, Z., Yao, H., Liu, W. & Zhang, Y. **Shared Prefixes, Better Credit: Adaptive Routing for Multi-Agent Reasoning.** arXiv:2608.02291v1 (2026). https://arxiv.org/abs/2608.02291
188. Liao, S., Chen, Z. & Tang, Y. **TCPO: Turn-Level Credit Policy Optimization.** arXiv:2608.01667v1 (2026). https://arxiv.org/abs/2608.01667
189. Huang, Y., Xu, B., Cao, H. & Zhu, C. **BiCAA: Bidirectional Credit Assignment for Search-Augmented Agent.** arXiv:2608.01321v1 (2026). https://arxiv.org/abs/2608.01321
190. Wang, Z.-H. et al. **AgentOPSD: Recursive Self-Distillation for Agentic Reinforcement Learning.** arXiv:2608.05987v1 (2026). https://arxiv.org/abs/2608.05987
191. Qu, C., Dai, S., Cai, H., Zhou, Y., Chen, X., Simon & Xu, J. **TurnSight: Turn-Level Hindsight Self-Distillation for Tool-Integrated Reasoning.** arXiv:2608.04007v1 (2026). https://arxiv.org/abs/2608.04007
## 2026-08-04 补充：source-volume 不是 verifier coverage，entropy 必须对齐 utility

V2.43.70 的真实外部门提供了一个对 Deep/Wide 搜索设计很重要的反例：发现 559 个 registrable hosts 并不保证最终验证覆盖。若系统先按返回顺序截取前 10 个来源，再随机保留两个 verifier，则后发现的 query/batch strata 可能完全没有进入 proposal 或 verifier 集。这个失败和近期工作中的几个观点相互印证：Diverse Query Initialization 强调初始化分散性，但分散 query 若在 source selection 处被 first-k 截断，其收益不会传到下游；conjunctive cross-page retrieval 关注“所需证据是否共同覆盖”，而非单纯 source 数；Bridge Evidence 区分静态检索相关性与对最终决策的因果 utility；Context Gathering Decision Process 则提示 acquisition policy 应按下游 belief/decision value 设计，而不能把更多网页当作目标本身。

因此当前实现把创新点进一步收紧为三层账本，而不是笼统的“entropy reward”：

- `proposal information gain`：独立 proposal source 对某个精确 entity-column-value support set 的条件熵下降；
- `verification outcome`：候选前冻结的、与 proposal source 不相交的 hidden verifier 是否对同一 target/value 提供支持、支持 baseline 或产生冲突；
- `utility-aligned entropy credit`：只有 exactly-bound、独立支持且无 target-bound conflict 的 proposal entropy 才获得最终 credit。

这比“哪个网页看起来信息量大就给哪个 step credit”更可行。原始 surprisal、页面新颖度、字符数或 source count 都可能奖励噪声、误导证据与重复信息；V2.43.70 恰好显示 proposal entropy 可以为正而最终 utility 为零。对于 credit assignment，合适的量不是无条件信息增益，而是受来源独立性、目标绑定与反事实 utility 约束的增益：`credit(e) = I(Y; e | state, prior evidence) × verified_utility(e)`。其中 `verified_utility` 不能由同一 proposal 自证，需要预留的独立 evidence stratum 或未来 outer intervention；否则会把“系统相信得更坚定”误写成“系统更正确”。这与 CIGPO 的 contextual information gain、Bridge Evidence 的 causal utility、CGDP/POMDP acquisition view、MICA/TRIAGE/step-level graph credit 的长程归因问题相接，但当前方案的可区分点是把 entropy、verifier outcome 和 downstream utility 以可重放 receipt 显式分离。

V2.43.71 的 batch-stratified prefilter 是这一观点的工程化实例：完整容量先从两个 discovery batch 各取 5 个 registrable hosts，再让每批各贡献 4 proposal 和 1 hidden verifier；它只读 visible query、URL/title 与 source provenance，发生在 fetch/candidate/entropy/evaluator 之前。合成测试显示它修复了 first-10 对第二批的完全遮蔽，并保持 2 search/10 fetch/3 model effects；但它目前仍只是 coverage mechanism evidence。只有全新外部门出现独立支持、正 utility credit 与最终 net gain，随后 paired dev64 和 exact-220 质量提升，才能把它升级为 benchmark 或论文主结论。

## 2026-08-06 补充：exact-table objective gate 的第一次真实质量检验是 ceiling NO-GO

V2.46.38 首次把此前 external mechanism gate 补成了完整的质量识别链：12 个全新机场表任务、96 个实体、共享 plan/search/fetch evidence、相同模型与 token 上限、平衡两臂调用顺序；24 个预测全部冻结后，独立 evaluator 才读取绑定到不可变 OurAirports commit 的 ICAO/IATA gold。forward 仅用 45.70 秒，12/12 bundle 有效、36 次模型 effect、0 slot timeout。这说明 fixed 20/8/240 可靠性基线可以把中等规模 paired gate 压缩到分钟级，而不是天级。

结果同时暴露了实验设计风险：标准 synthesis 和 schema-conditioned coverage-ledger prompt 都得到 `12/12` exact table，Composite 均为 `1.0`。候选确实把可见实体拼写/顺序严格保持从 `10/12` 提到 `12/12`，但预注册 evaluator 对行顺序不敏感，exact 与 Composite delta 均为0，所以 gate 必须判 NO-GO，不能事后把结构 receipt 改写成质量胜利。机场代码对 GPT-5.6 和 web search 太容易，因而该轮验证了运行时隔离与结构机制，却没有估计困难开放世界下的 completion utility。

这对 entropy/credit 也给出一个直接反例：两臂 outer utility 完全相同，任何由页面新颖度、coverage completion 或内部 ledger 产生的正信息增益都不应获得正任务 credit。若定义 `credit(e)=IG(e)×verified_utility(e)`，本轮可识别的 candidate-vs-baseline outer utility 是0，因此增量 credit 必须为0。下一外部门需预先证明非天花板难度，使用长尾、跨页、不可由模型记忆直接填满的 immutable registry facts；同时把顺序/identity compliance 作为预注册 secondary metric，而非事后替换 exact-table 主指标。

V2.46.39 随后用不可变 ROR registry 做了这项非天花板复验。12个任务各含4个长尾机构，答案是9字符 ROR suffix 与 ISO alpha-2 country code；任务、gold和provenance在预测前分别物理隔离，forward只见名称和schema。baseline 与 coverage-ledger 共享搜索/页面、共享行 projector、各一次合成调用。baseline 与 candidate 都是 `2/12` exact，但 candidate Item F1 从 `0.645833` 降到 `0.635417`、Composite 从 `0.911458` 降到 `0.908854`，同时 Unknown cell 从15降到14。

这个组合比单纯 NO-GO 更有信息量：candidate 的内部 completion signal 看起来改善，却以额外错误值为代价。也就是说，减少未知项不是 task utility，页面覆盖或熵下降也不是事实正确性的充分条件。对 credit assignment，candidate-vs-baseline 的 verified outer utility 为负，因此即使某个 cell 的主观熵下降为正，其 task credit 也必须非正。工程策略应从“coverage ledger 强制填满”切换为 evidence-constrained verification：只给 exact target/value/source binding 且由独立页面支持的 cell 正 credit，无支持时保留 Unknown。该结论来自 benchmark-external ROR 门，不是 DeepWideBench 提分，也不授权 dev64或220。

V2.46.40 随后直接检验了这个更保守的设计。第三个 model effect 只能为 baseline 的 Unknown ROR cell 提案；deterministic projector 只有在同一条模型可见的截断页面里同时看到 exact organization phrase 与 exact ROR suffix 才能录入，而且非空 ROR 和所有 country cells 都不可改。新12题/48实体与此前4,336个实体 exact/canonical 互斥，gold仍逐record绑定同一不可变ROR commit。唯一 forward 在139.93秒内得到12/12有效bundle、36次model acquisition、48条query、120次fetch和113条usable page，零slot timeout；所以零触发不能归因于容量或网络失败。

post-freeze evaluator显示两臂完全相同：`1/12` exact、Item F1 `0.572917`、Composite `0.893229`、Unknown cells `21`。机制receipt进一步显示12题均返回空 `replacements`，raw/formed/supported/admitted proposal全部为0。这个证据不能说“deterministic gate太严格而拒绝了候选”，因为gate从未见到声明；同样不能把113条usable page解释成113条exact support，因为“页面有文本”和“页面共同绑定entity与value”是两回事。content-free forward artifact也刻意不保存页面或值，因而不能事后区分页面确实没有pair support，还是模型面对已有support仍选择abstain。

V2.46.41 的冻结后诊断把这个边界量化了：48个baseline ROR格中11个正确、16个非空错误、21个Unknown；country格44个正确、4个错误。仅补Unknown且不改非空事实时，只有3/12任务结构上可能变成exact。因此 evidence-constrained completion只能解决一部分precision–coverage问题，不能独自承担whole-table optimization；安全补缺与安全纠错必须分开识别。下一可证伪机制应先用确定性文本解析在模型可见证据中发现 exact entity–ROR pair，再把唯一/歧义/无pair counts作为content-free observation交给dependent revision。nonempty correction则需要另一套独立来源或反事实冲突门，不能通过放松Unknown gate获得。

这也进一步收紧信息熵credit的适用域。网页数量、字符量、来源新颖度乃至检索后主观熵下降，都发生在可地址化 `target–value` proposal之前，不能直接获得正task credit。合理链条是：先构造pair-level候选及来源依赖图，再估计该候选相对当前belief的信息增益，最后用独立验证和冻结后的outer task utility决定credit的符号与幅度。V2.46.40的outer delta为0，所以任何内部proposal-free entropy signal的增量task credit都必须为0。这支持“entropy是受约束的epistemic中间量”，不支持“entropy gain本身就是credit assignment”。

## 2026-08-06 补充：可地址化 pair 仍不等于正确 identity binding

V2.46.42 把 V2.46.40 的零声明瓶颈移出了模型：它直接在模型实际可见的页面中确定性寻找 organization phrase 与 ROR suffix 的共同出现，并把每题模型调用从3次降为2次。12题/48实体的全新外部人口在80.13秒内完成，92个可见页面中33个包含显式ROR、26个包含目标实体文本，形成2个唯一pair并自然 admission 1个 Unknown。因而该轮排除了“机制完全不触发”以及“必须增加搜索量”这两种解释。

但唯一 admission 是错的：candidate ROR 是 registry 中另一机构的真实 ID。baseline 与 candidate 都是`0/12` exact、Item F1 `0.552083`、Composite `0.888021`；Unknown虽从27减到26，任务质量没有改善。V2.46.43 的 post-freeze aggregate diagnosis 再确认 changed cell=1、correct admission=0、incorrect admission=1，且错误ID确实对应历史中的不同组织。最合理的局部解释是，官方ROR页面正文提及目标机构只表达 affiliation、合作或其他关系，而页面自身的 primary organization 是另一实体。

这个反例在 entropy credit 前增加了不可省略的身份层。`entity text ∈ page body` 与 `ROR URL ∈ page` 只证明两者在一个文本窗口内相关，不能证明随机变量所指向的是同一主体；若把这种共现当成 target–value observation，posterior entropy 可能下降得很大，却是在错误状态空间上变得更自信。故 credit 的可辩护顺序应是：先用 exact normalized title，或结构化 primary-identity 字段，建立页面主体与目标实体的绑定；再绑定该主体与值；之后才计算条件信息增益、来源依赖、独立验证和 outer utility。任何 identity binding 失败的 step，即使新颖、surprising 或减少 Unknown，也不能得到正 task credit。

这使当前创新主张更具体：不是一般性的“按信息熵增益给搜索步骤 credit”，而是 **identity-gated, utility-aligned information credit**。其最小 receipt 至少要分离 primary-identity binding type、target–value binding、source dependency、belief delta、independent verifier outcome 与 post-freeze utility；其中任一前置层失败，后续正 credit 均应 fail closed。下一外部门因此应删除 body-only binding，只比较 title-bound 或 structured-primary-identity-bound pair，并在全新 population 上以 exact-table strict gain 和 Item/Composite non-regression 证伪；在此之前不能声称 entropy credit 已被验证，也没有 DeepWideBench 或 SOTA 提升。

V2.46.44–45 把这个结论实现成了可审计的身份层。HTML路线不再把“页面里提到目标名”当主体，而要求抓取终点的canonical ROR profile URL与normalized whole fetched-page title同时绑定；structured路线要求official ROR API URL、record ID与唯一`ror_display` name三重一致。实现特别区分了三种常被混淆的metadata：search lead title在fetch前清空，requested URL不能替代redirect后的final URL，普通正文中的“Organization/ROR”样式也不能冒充顶层registry record。这样一来，关系页、目录页、合作方、重定向旧ID和搜索摘要都不能凭共现制造低熵但错误的belief。

为了让严格gate仍可自然触发，系统只把已经发现的official `ror.org/<id>` lead确定性改写为同ID的official API endpoint；没有新增query或fetch。API response又在共享evidence形成前投影为`id + ror_display names`，所以baseline与candidate看到相同信息，candidate没有隐藏的privileged channel。新48实体population与4,432个历史实体literal/canonical双重不重叠；build/package audits分别44/44和31/31通过，forward manifest不含private population、gold、provenance或evaluator。这些前置结果当时只证明实现与实验设计边界；随后完成的唯一forward与post-freeze评价见下文。

V2.46.45 现已完成这次外部检验。唯一 forward 在 `69.705274s` 内冻结12题的24个arm predictions，24次model-slot acquisition均完成且没有slot timeout。108个模型可见页面中，strict gate识别出3个structured-primary-identity pair，同时拒绝12个body-only pair。三个结构化pair都指向baseline已非空的ROR cell，35个baseline Unknown没有一个得到unique identity-bound pair。因此candidate没有改变任何预测。这一结果支持“正文共现不能越过primary identity gate”的实现边界，但没有实际处理过Unknown，不能估计该门对候选值的precision或recall。

post-freeze evaluator确认两臂均为exact-table `0/12`、Item F1 `0.625`、Composite `0.90625`、Unknown value cells `35`。V2.46.47 的aggregate-only diagnosis又把baseline事实状态分为ROR `12 correct / 1 incorrect / 35 Unknown`和country `48 correct`。11/12题若能安全补全ROR Unknown，结构上可以达到exact；另1题还需要纠正一个非空ROR。这个分解说明当前失败不是任务没有可改善空间，而是结构化acquisition没有对准需要干预的cell。权威证据为 [`results/v24645_primary_identity_pair_result_v1_20260806.json`](results/v24645_primary_identity_pair_result_v1_20260806.json)、[`results/v24645_primary_identity_pair_postresult_audit_v1_20260806.json`](results/v24645_primary_identity_pair_postresult_audit_v1_20260806.json) 与 [`results/v24647_v24645_zero_intervention_diagnosis_v1_20260806.json`](results/v24647_v24645_zero_intervention_diagnosis_v1_20260806.json)。这些是benchmark-external ROR结果，不是DeepWideBench提升。

这次零干预使论文公式的识别条件更严格。`credit(e)=1[primary_identity_bound]·1[target_value_bound]·IG(Y;e|state)·verified_utility(e)`仍可作为待检验假设，但V2.46.45没有估计其中IG或verified utility对有效干预的作用。identity-bound evidence若只重复baseline已有事实，增量task credit仍为0；candidate没有改变状态时，双臂持平也不能证明identity gate本身无效。下一外部门应在相同总预算内把acquisition直接指向baseline Unknown，并与deterministic official-registry exact-name lookup比较。必须先自然产生至少一个identity-bound Unknown intervention，再用strict exact-table gain与Item/Composite non-regression评价；nonempty correction另做独立实验。entropy/credit assignment在此之前仍未验证。

## 2026-08-06 补充：Unknown-target official lookup 首次获得正 outer utility，但尚未识别 entropy credit

V2.46.51–54 完成了上述外部门。新人口来自同一immutable ROR tree的未消费slice `[3000,3482)`，48个实体与4,480个历史实体literal/canonical交集均为0。forward只接收`{opaque_id, question}`；private population、48行gold、provenance和evaluator不在37-file forward manifest中。每题先用6个generic fetch形成baseline，再只对Unknown ROR cell执行最多4个official ROR v2 `query.advanced=names.value:"..."&filter=status:active` lookup。完整响应、唯一active record和唯一normalized `ror_display`缺一不可；歧义、截断、分页不完整或URL/record/name不一致均abstain。

唯一forward在`73.045937s`内完成12/12任务和24/24预测，24次model-slot acquisition无timeout。72个generic fetch之后请求37个target，36个得到唯一exact response，1个歧义；最终36个replacement。prediction freeze后的一次evaluator-only评价得到baseline exact-table `0/12`、Item F1 `0.552083`、Composite `0.888021`、Unknown cells `40`，candidate分别为`7/12`、`0.927083`、`0.981771`和`4`。strict exact gain与两个non-regression guardrail均通过，postresult audit无finding。权威结果为 [`results/v24654_v24651_unknown_target_structured_result_v1_20260806.json`](results/v24654_v24651_unknown_target_structured_result_v1_20260806.json)。

该结果支持的是一个受限机制：当任务公开schema指向可验证的权威namespace时，先定位Unknown target，再以唯一structured primary record做deterministic recovery，可以把额外acquisition转成正确表格值。它没有比较相同effect的随机化动作，也没有估计页面或step的`IG(Y;e|state)`，因此不是“信息熵credit有效”的证据。36个admission与36个Unknown reduction相等，但这只是policy-level before/after；缺少逐step counterfactual，不能排除credit属于target selection、registry exact matching、abstention rule或它们的组合。

对论文主张，当前最强可辩护表述是 **identity-gated, target-bound, utility-validated information acquisition**，而不是“按entropy gain分配credit”。若要把entropy升级为核心经验贡献，后续实验至少需要在同一可接受observation集合上预注册三臂：无熵的deterministic Unknown-target baseline、entropy/VOC排序candidate，以及matched-cost随机或固定排序control；冻结每步belief state、source-dependency group与action budget，并用同状态删除/替换或sibling counterfactual估计step contribution。只有entropy/VOC排序在fresh任务上同时提高outer exact-table utility、通过来源独立性门并优于无熵强基线，才可声称entropy提供了增量credit signal。

DeepWideBench迁移仍需要一道新的独立门。ROR API是领域特定权威adapter；把它未经验证地应用到任意DeepWideBench题会混淆mechanism transfer与domain shortcut。V2.46.79 已经完成 expanded-schema historical dev64，但 whole-table `3→3/64`，因此不能充当这道迁移门的 GO。下一实验应先在 fresh benchmark-external 表格人口比较 frozen parser、expanded parser only、expanded parser + target–value evidence/admission 三臂；路由只能依据 visible question/schema 与预注册 namespace，禁止 category、question_type、mapping、gold 或 score。只有 whole-table 严格增益、Composite/Entity/Row/Item/Column F1 全部 non-regression、evaluator health、自然触发率与同总 budget 共同过门，才可重新设计 DeepWideBench gate。当前没有新的 full-220 授权或 SOTA 证据。

## 2026-08-06 补充：World Bank 外部门 GO 没有迁移成全榜干预

V2.47.00 将 target–value recovery 从 ROR 迁移到另一类公开权威数据。12 个 benchmark-external World Bank 表格任务固定三臂、固定分母并在 prediction freeze 后评价。frozen parser 与 expanded parser 都是 exact-table `0/12`、Item F1 `0.010417`、Composite `0.752604`；target–value arm 是 `3/12`、`0.687500` 和 `0.921875`。相对 expanded parser，后者分别增加 `+3`、`+0.677083` 与 `+0.169271`，因此外部门 GO。实验没有使用 DeepWideBench evaluator，也没有计算信息增益或 step counterfactual。它支持 structured target–value acquisition 在显式权威 namespace 中的 task utility，不支持 entropy credit 或一般网页搜索。

V2.47.06 随后在不读取 mapping、gold、category、question_type、split 或 score 的条件下，只审计 220 个可见 question/schema。严格的“题目明确指定答案权威来源”条件只识别出 1 个 World Bank 任务，覆盖率为 `1/220`；此前两个模糊线索分别是 GitHub discovery clue 和相机 ISO 字段，均被排除。这个结果说明 adapter quality 与 benchmark reachability 是不同问题。即使 adapter 在其适用域内表现良好，只能安全触达一题的 policy 也几乎不可能移动全榜 whole-table 指标。

V2.47.14 仍执行了一次预冻结、single-pass 的 sparse migration，用来同时检验 transport 与 fail-closed identity。4 个 bulk indicator ZIP 并发下载，3 个成功，1 个在 30 秒超时；唯一 eligible 题由于 bundle 不完整而拒绝 intervention。220 个 prediction 全部终态且逐个未变，model/search/per-country calls 为 0，总耗时 `30.199208s`。因此，220 题规模本身并不解释此前天级等待；这次运行的临界路径只是单个 30 秒下载 timeout。反过来，它也不能证明完整 GPT-5.6 pipeline 只需 30 秒，因为模型生成已由 frozen control predictions 取代。

这一轮对 entropy credit 提供的是零干预识别边界。若 action 没有改变 admissible observation、belief state 或 terminal prediction，其增量 task credit 必须为 0；页面或 bulk source 的潜在信息量不能补上实际 intervention 的缺失。即使将来 bulk 成功，credit 仍需区分 transport success、pair admission、belief change 与 terminal utility，不能把“下载到了权威数据”直接当作有用步骤。V2.47.18 的 220/220 byte identity 和全指标 delta 0 正好形成 matched outcome 的 null case。

## 2026-08-06 补充：下一实验必须把 entropy 与强无熵基线分开

目前最强的外部正结果来自 deterministic Unknown-target lookup，而非 entropy 排序。合理的下一检验不是再运行一个带“信息熵”名称的完整 pipeline，而是在相同 admissible observation 集、相同 identity/value gate 和相同总成本下冻结三个动作策略：无熵 deterministic Unknown-target 强基线、按四层 task-risk/dynamic-VOC 排序的 candidate，以及 matched-cost 固定或随机排序 control。只有 candidate 在 fresh task clusters 上同时改善 outer exact-table utility、保持所有分项 non-regression，并在 step counterfactual 上优于两类控制，才能把增量归因于 entropy/VOC signal。

step credit 的符号不能来自 entropy drop。每步应先冻结 pre-state、可选 action set、source-dependency group 与成本，再用同状态 deletion/replacement、sibling continuation 或 artifact-disjoint outer continuation 估计 signed task contribution。entropy、semantic entropy 或 expected information gain 可以预测 rank 或调节 credit 幅度，但不能把 verifier-negative、identity-unbound 或 outer-zero 的步骤翻成正 credit。必须单独报告 high-IG/zero-utility、low-IG/high-utility、错误来源使 posterior 变尖和低短视 IG 的 bridge step；这些反例决定该信号是否仅是 diagnostic。

工程门也需前移。bulk transport 应先在 benchmark-external population 上通过 completeness、checksum/schema、冷/热缓存与一次性 timeout stress，再进入任何 benchmark forward。generic candidate 则需在启动前证明多题的非零安全 intervention reachability。若外部与 fresh dev64 均 GO，只冻结一个 candidate 做一次 full-220；目标至少同时达到 V2.42.67 的 `7/220` whole-table 与 V2.46.35 的 `0.437892` Composite，并要求至少一项严格增加。没有独立 leaderboard 或同协议系统比较时，达到内部前沿仍不能称为 SOTA。

## 2026-08-06 补充：transport 可靠性门否定 aggregate-JSON primary

V2.47.21 将 transport 从 adapter quality 和 DeepWideBench 分数中单独识别。指标向量不是根据网络成败挑选，而是 V2.47.09 和 V2.46.90 在本轮 outcome 前已经冻结的 6 个 World Bank 指标。每个指标比较 bulk ZIP 与 aggregate JSON 两种官方表示，固定 2 waves、每 endpoint 每 wave 单次尝试、12 workers、20 秒 hard total wall 和 15 秒 socket timeout。aggregate JSON 在请求前被指定为 primary；bulk ZIP 只作 diagnostic comparator。运行不读取 benchmark，不调用模型、搜索或 evaluator，也不保存 response body、国家或值。

唯一运行在 `30.415992s` 内完成固定 `24/24` 请求，但预注册门严格 NO-GO。bulk ZIP 为 `12/12` 成功，每次约 `0.18–0.26s`。aggregate JSON 只有 `9/12` 成功，3 次失败都在约 `15.2s` 达到 socket wall；其中一个指标两波都失败，另一个指标第一波失败、第二波成功。两波总体墙钟仍在 25 秒上限内，说明失败不是父进程失控，而是 primary endpoint 的 per-request transport 不稳定。post-result audit 为 `audit_valid=true, findings=[]`，其含义是 NO-GO 结果可信，不是 transport 通过。权威工件为 [`results/v24721_worldbank_transport_result_v1_20260806.json`](results/v24721_worldbank_transport_result_v1_20260806.json) 和 [`results/v24721_worldbank_transport_postresult_audit_v1_20260806.json`](results/v24721_worldbank_transport_postresult_audit_v1_20260806.json)。

V2.47.22 的冻结后诊断进一步分开 transport failure 和 semantic-domain mismatch。9 个双表示共同成功的 indicator-wave pair 中，共同 260 个三字符代码的 value mismatch 总数为 0；然而 ZIP 每次含 265 个代码，aggregate JSON 每次含 260 个，9 次 symmetric difference 都是 5。这个结果支持“共同域值一致”，不支持“完整表示等价”。它也禁止事后把 12/12 的 ZIP 改成 primary 来翻转 V2.47.21 结论。权威诊断为 [`results/v24722_v24721_transport_diagnosis_v1_20260806.json`](results/v24722_v24721_transport_diagnosis_v1_20260806.json)。

该结果对 entropy credit 的约束是前置性的。transport 没有返回 observation 时，step 的 realized information gain 和 task credit 都必须为 0；同一 endpoint 在另一波成功也不能回填失败波。表示域不同又意味着 posterior state 必须显式指定 universe。若把 ZIP 的 265 项与 JSON 的 260 项直接视为同一随机变量，五项 domain difference 会被错误记为冲突、遗漏或 entropy change。下一外部门因此只能在 fresh indicator population 上预注册 bulk-primary，并分别报告 primary 全域、跨表示共同域和表示特有域；这仍是 transport/mechanism 证据，不是 DeepWideBench 提分或 entropy-credit 验证。

## 2026-08-06 补充：fresh bulk-primary transport 通过，但 comparator 继续暴露端点异质性

V2.47.23–26 完成了上一节要求的独立复验。fresh population 不是按网络结果挑选：它从 V2.47.21 outcome 之前 commit `d2b7deacc9f66cf8ac8c4904b588c8c889d68c26` 中的 literal `TARGETS` 机械选择此前未消费的 `IT.NET.USER.ZS@2022` 与 `SP.DYN.LE00.IN@2022`。protocol 在任何本轮请求前冻结 bulk ZIP 为 primary、aggregate JSON 为 diagnostic comparator，固定 2 waves、每 endpoint 每 wave 单次尝试、4 workers、20 秒 hard wall、15 秒 socket wall，禁止 cache、resume、retry 和 selective rerun。15/15 定向测试、label-blind AST、credential scan、shared lease 与 watcher identity 均在 launch 前通过。

唯一运行共发出固定 8 个请求，总墙钟 `30.419029s`。bulk primary `4/4` 成功，每次返回 265 records；两个指标各自的 semantic hash 跨波完全稳定，故预注册 primary gate 为 `transport_go`。aggregate comparator 仅 `2/4`：internet-use 两波成功，life-expectancy 两波都在约 15.2 秒报 transport error。两次双表示共同成功中，共同域均为 260 个代码、共同值冲突为 0、bulk-only 为 5、JSON-only 为 0。post-result audit 为 `audit_valid=true` 且 findings 为空；结果与决定分别冻结在 [`results/v24726_fresh_bulk_transport_result_v1_20260806.json`](results/v24726_fresh_bulk_transport_result_v1_20260806.json)、[`results/v24726_fresh_bulk_transport_decision_v1_20260806.json`](results/v24726_fresh_bulk_transport_decision_v1_20260806.json) 和 [`results/v24726_fresh_bulk_transport_postresult_audit_v1_20260806.json`](results/v24726_fresh_bulk_transport_postresult_audit_v1_20260806.json)。

这个结果只支持一个窄结论：对这两个预先选定的 fresh indicators，bulk ZIP 可作为下一机制实验的稳定 primary transport。它不证明 aggregate JSON 普遍不可用，也不证明 bulk 对任意 namespace、任意时间或 DeepWideBench 都可靠；两次 comparator failure 反而说明 endpoint/indicator 层异质性仍需 fail-closed。更重要的是，transport GO 没有产生 benchmark observation、belief change、prediction 或 evaluator call，所以它的 task credit 和 DeepWideBench delta 都未定义，不能写成提分，更不能写成 entropy-credit 验证或 SOTA。

对信息熵视角，V2.47.26 把随机变量的支撑域问题固定下来：primary belief state 应以 265-code bulk universe 为准；跨表示一致性只能在显式 260-code intersection 上计算，5 个 bulk-only codes 不能被误记成 disagreement 或 entropy reduction。下一阶段必须把“数据可达”与“任务可达”分开：先在预冻结、task-cluster-disjoint 的多题外部人口中自然产生至少两个 cluster 的 identity-bound、target-value-bound、prediction-changing intervention，再比较 deterministic Unknown-target、entropy/dynamic-VOC 与 matched-cost control。只有 entropy arm 在同一 admissible observation、同一 verifier 和同一预算下提供额外 outer utility，才有资格获得增量 credit；V2.47.26 本身只清除了 transport 这一前置混杂。
## 2026-08-08：30k 证据预算得到 shared-prefix 因果支持

V2.48.44 是 V2.48.42 原子表头闭包的首个完整 DeepWideBench 220 结果：whole-table `5/220`，Composite `0.449620`，Entity/Row/Item/Column F1 为 `0.704545/0.217208/0.394956/0.481768`。它相对 V2.48.40 提高 Composite、降低 exact，且仍低于 V2.48.00 的 `8/220 / 0.456834`，因此不是 SOTA。逐题配对仍被独立搜索、抓取、生成和judge采样混杂；运行也没有记录原子依赖实际触发次数，不能据此声称表头闭包带来因果质量增益。

冻结后 V2.48.45 显示证据供给是更强的观察梯度：fetch failure为0的33题 Composite为 `0.6104`，5–7次failure的59题为 `0.3589`；投影达到15k的155题为 `0.4931`，4–8k的19题为 `0.3397`。V2.48.00 与V2.48.44又同时在检索后端（Tavily URL-lead vs keyless hosted search）和投影预算（约30k vs16k）上不同，所以跨版本差异不能识别单一机制。

V2.48.46/47 因此做了matched shared-prefix验证。两臂共享完全相同的两份World Bank原始响应、固定8页结构向量、可见任务、模型、prompt、输出cap和并发；唯一行为差异是原子闭包总cap `16k -> 30k`，每页仍为5k。32个任务的64份prediction全部冻结后才打开private evaluator。16k取得 `10/32` Exact、Composite `0.792969`，30k取得 `25/32`、`0.835938`，Exact `+15`、Composite `+0.042969`，其余质量指标均不降；两臂orphan均为0，原子依赖补入均触发37次。该结果是“在target-cell-disjoint结构表格人口上，30k证据预算优于16k”的因果证据；它不是一般网页搜索或DeepWideBench SOTA证据，也没有验证entropy credit。

## 2026-08-08：30k 外部门收益未迁移到 DeepWideBench 全集

V2.48.48 把上述 treatment 以严格单变量方式迁移到完整 DeepWideBench：父算法为 V2.48.44，除总投影 cap `16k→30k` 外，220题向量、prompt、GPT-5.6、keyless search/fetch、单题预算和 `20 task / 8 model` 并发均不变。forward 只读 `{opaque_id, question}`，220个预测在mapping/evaluator打开前全部冻结；220个content-free receipt显示0 missing、0 orphan、0 missed supported requirement，总投影4,494,390字符。值得注意的是，本批抓取页面没有自然产生长表 continuation 或表头依赖补入，因此这次实验主要检验更宽的通用证据窗口，而没有重新检验V2.48.47中实际触发的结构闭包机制。

官方32-worker evaluator exactly-once覆盖220条预测，13个evaluator error按预注册规则计0。结果为whole-table `5/220`、Entity/Row/Item/Column F1 `0.690909/0.205215/0.381860/0.468587`、Composite `0.436643`。相对16k父版本V2.48.44，exact不变，Composite下降`0.012977`；相对内部最佳V2.48.00，exact少3、Composite下降`0.020191`。因此“30k在结构化matched-prefix人口有效”不能外推为“在开放网页检索上普遍有效”。更大的窗口同时增加潜在支持证据、冗余、冲突和生成负担；若不显式估计证据质量与依赖关系，容量不是单调收益变量。

这也收紧了entropy/credit的主张。投影字符增加本身既不是信息增益，也不应得到正credit；必须把可见需求覆盖、source/record identity、target-value binding、独立来源、新颖性、冲突与冗余纳入belief update，再用同状态deletion/replacement或sibling continuation估计signed outer utility。下一可识别实验应在fresh shared-prefix任务上比较fixed-16k、fixed-30k与matched-cost quality-gated三臂；entropy/IG只预测动作排序或value-of-computation，verifier-negative、identity-unbound、重复或outer-zero证据的credit必须为0或负。V2.48.48没有验证entropy credit，也没有刷新benchmark前沿或SOTA。

## 2026-08-08：V2.49.22 完整 220——有效全集结果，但 target–value 机制零暴露

V2.49.22 已完成完整 DeepWideBench `220/220` single-pass forward。forward 只读 `{opaque_id, question}`，全部 prediction 冻结并通过 content-free audit 后才开放 mapping、gold 和 evaluator。运行用时 `782.780341s`，219 个表由 GPT-5.6 生成、1 个 fallback。固定 32-worker evaluator 对 220 条冻结 prediction 各评一次，207 valid、13 error 固定计零；结果为 Exact `7/220`、Entity `0.686364`、Row/Item/Column F1 `0.192148/0.366439/0.455804`、Composite `0.425189`。post-result audit 为 `audit_valid=true, findings=[]`。相对项目当前单轮最佳 V2.48.57 的 `9/220 / 0.457249`，Exact 少 2、Composite 低 `0.032060`，所以这是明确 NO-GO，不是 SOTA。

该分数不能回答 target–value projector 是否有效。12 个 Tavily key 各在第一次 provider attempt 返回 HTTP `432`，随后被 key-local disable；880 个 logical query 全部失败，successful query、URL lead 和 fetch 都为 0。由此 220 个 projector receipt 中 supported/retained target–value pair、table-header dependency addition 和 selected continuation 全为 0。换言之，V2.49.21 的核心 treatment 从未接触可投影页面；本轮主要测得 GPT-5.6 无网页证据时的退化基线，而不是“target–value coverage 对 parent projector”的有效比较。完整固定分母仍然有效，但 mechanism estimand 不可识别。

这也是 entropy-credit 的一个重要负控制。无 observation 时，realized information gain、evidence credit 与 mechanism exposure 必须为 0；不能因为模型仍输出表格、最终有 7 个 Exact，便把 credit 追溯给未发生的 search 或 projector action。下一可识别实验必须先通过独立的 credential-blind aggregate transport gate，再在 fresh benchmark-external shared-prefix population 上让 parent 与 target–value 两臂共享完全相同的 fetched page bytes、模型和预算。只有自然出现 identity-bound、target–value-bound、source-dependency-aware pair，并由 prediction change 与 post-freeze signed outer utility确认增量贡献，才可给该步骤正 credit。V2.49.22 不支持“信息熵增益越大 credit 越大”，但支持一个更严格的零点公理：无可采纳 observation 或零 mechanism exposure 时，epistemic/task credit 必须为零。

## 2026-08-09：V2.49.27 全集暴露 Unicode totality，而非搜索容量瓶颈

V2.49.27 将 visible-row sparse compaction 与 target–value projection 接到本地免 key GPT-5.6 production path，并完成完整 DeepWideBench `220/220`。全部 prediction 在 mapping/gold/evaluator 打开前冻结；32-worker evaluator 对每个 prediction exactly once，3个 evaluator error 固定计零。最终 Exact `5/220`，Entity/Row/Item/Column F1 为 `0.468182/0.144019/0.253297/0.311637`，Composite `0.294284`。forward `656.872813s`，130个 model-generated、90个 fallback。它显著低于 V2.48.57 的 `9/220 / 0.457249` 和 V2.49.22 的 `7/220 / 0.425189`，因此不是 benchmark 提升或 SOTA。

冻结后 content-free aggregate 将90个 fallback 全部定位为 synthesis 前的 coarse `ValidationError`，最后安全阶段为 `retrieval_terminal`；220个transport和single-shot receipt均有效，hosted-search deadline failure为0。130个正常任务恰好有130个 sparse projection receipt，90个失败任务没有。这个一一对应把系统性故障缩到 evidence projector 邻域，而不是endpoint、并发或模型生成。为保持 label-blind，诊断没有读取冻结题目、页面、预测或逐题correctness，因此不能进一步宣称每个失败任务的原始异常消息。

纯组件审计随后复现了 V2.49.24 的确定性 totality bug。组件先用 NFKC 清理页面，却在receipt中要求规范化后的输出长度不超过原始输入长度；兼容字符可以合法扩张，例如 `½→1⁄2`、`Ⅷ→VIII`、`℡→TEL`、`™→TM`、`℃→°C`、`ﬃ→ffi`。结果是证据内容越丰富并不一定越接近synthesis；一个单字符页面即可在投影receipt处fail closed。V2.49.28以append-only方式把预算域改成NFKC规范化后的输入长度，同时分开记录raw、normalized、expansion与contraction；30k总cap、5k/page、search/fetch/model/token/context/wall caps均不变。8类扩张字符父版本全部失败、candidate全部成功，12/12定向测试和300个随机Unicode/结构fuzz通过。

这个结果对信息熵/credit有一个容易忽视的含义：representation normalization的字符数变化不是belief entropy变化。`½`展开为三个code points既没有自动增加关于答案的知识，也不应得到epistemic credit；它只是编码/规范化层面的可表示性变化。若将token数、字符数或压缩率直接当作信息增益，系统会给Unicode展开、重复格式和冗长证据错误的正credit。credit状态必须定义在语义变量与admissible observation上，而不是字符串长度上。

## 2026-08-09：V2.49.29 中性门严格 NO-GO，但 totality 子目标通过

V2.49.29–31 使用20个benchmark-external Unicode官方文档任务，在生产同形的本地GPT-5.6 hosted search/fetch、`20 task / 8 model`并发、每题`3 model / 4 query / 10 fetch / 240s`下检验V2.49.28。控制面先暴露一个独立bug：空的`conflicting_process_pids=[]`被通用truthiness检查误判为失败；V2.49.30修正布尔极性，V2.49.31只适配corrected-start role，没有改变算法或预算。

唯一forward在`41.549525s`结束，20/20 parent success、20/20 primary model-generated、20/20 projection/retrieval receipt，fallback、hard timeout、hosted-search deadline failure和model-slot timeout全部为0。共164次fetch、155个usable pages；真实网页中15/20任务出现NFKC扩张，总扩张135字符。这是对Unicode-total reliability的强外部支持：机制在真实页面中自然触发，并没有只通过合成样例。

整体门仍按预注册判为NO-GO，因为要求logical query至少72条，planner实际只提出58条。不能事后把58解释成72或删除条件；但也不能反向说Unicode修复失败。query数是检索强度代理，totality直接证据是20/20 projection receipt与0 fallback。该门揭示了实验设计问题：当155个usable pages已经超过80页门槛时，强迫planner接近4 query/task并不能增加可靠性，反而把“少而足够的查询”错误判负。后续门应直接约束usable evidence、identity/target binding、mechanism engagement、prediction change与outer utility，并只把query/fetch作为成本与守恒统计。

因此下一可识别实验不是再跑公开220，而是fresh shared-prefix质量门：两臂共享同一冻结页面字节、模型、prompt与output cap；父臂V2.49.24遇到NFKC扩张按预注册failure-as-zero，candidate使用V2.49.28。只有candidate除20/20 totality外还提高Exact、保持Composite/Entity/Row/Item/Column全不降，才说明工程可靠性修复转化为任务效用。即使该门通过，credit也应归给“避免无效失败、恢复可执行路径”的outer utility，而不是归给字符扩张或熵下降；entropy/VOC仍需在相同admissible observation、matched cost和counterfactual continuation下另行识别。

## 2026-08-09：V2.49.32 完整 220——totality 修复成功，质量没有刷新前沿

按“先跑出全集”的明确指令，V2.49.32 将 V2.49.28 Unicode-total projector 接入与 V2.49.27 相同的完整 DeepWideBench 执行链。唯一算法变化是把 compaction budget domain 从 raw input length 改为 NFKC-normalized input length；220题向量、GPT-5.6、prompt、search/fetch/model/token/context/wall caps、`20 task / 8 model`并发均保持不变。forward 仍只读 `{opaque_id, question}`，98项冻结前测试和 label/evaluator/credential audit 全通过。唯一 single-pass forward 用时 `839.875004s`，220条 prediction 在 mapping、gold 和 evaluator 打开前全部冻结；220题均生成模型表格，fallback为0，Unicode projection、transport和single-shot receipt均为220/220。

这给出了比中性门更强的公开全集 totality 证据。故障父版本 V2.49.27 只有130个projection receipt并产生90个fallback；V2.49.32变为220个receipt和0 fallback。在固定分母下，Exact由`5/220`升至`6/220`，Composite由`0.294284`升至`0.421283`，Entity由`0.468182`升至`0.663636`，Row/Item/Column F1由`0.144019/0.253297/0.311637`升至`0.200021/0.370574/0.450899`。这支持“组件修复恢复了原本被错误拒绝的执行路径”，但不是严格的同页面、同生成随机数因果质量估计；跨完整运行的搜索页面和模型输出并不共享前缀。

固定32-worker evaluator对全部冻结预测exactly once，212条有效，8条error按预注册规则计零，用时`248.872243s`。最终Exact `6/220=2.7273%`、Composite `0.421283`。它仍低于V2.49.22的`7/220 / 0.425189`，也低于项目单轮最佳V2.48.57的`9/220 / 0.457249`；因此质量判定严格NO-GO，不是benchmark新最佳或SOTA。post-result audit复核220行join、32个固定分片、全部worker returncode为0、8个error-as-zero、无重评/选择性重跑、lease和四个protected watcher闭环，`findings=[]`。

这个全集结果进一步区分了两类credit。第一类是execution/reliability credit：删除Unicode长度域bug后，90个失败路径消失，因而可以给“保持合法观察可执行”正的系统效用credit。第二类才是epistemic/task credit：NFKC字符扩张本身仍不改变关于目标值的语义belief，不能按扩张字符数、token数或压缩率获得信息增益credit。要把credit归给检索或证据选择动作，仍需证明observation可采纳、source/record identity与target绑定成立，并用matched shared-prefix deletion/replacement、sibling continuation或post-freeze signed outer utility确认边际贡献。

因此下一优化不应继续修补totality或盲增证据量，而应在fresh benchmark-external shared-prefix人口上识别质量选择器：baseline固定为V2.49.32，两臂共享完全相同的页面字节、模型、prompt、输出cap和成本；candidate只改变identity/target-value/dependency-aware evidence selection，并把entropy/IG作为shadow/VOC特征。只有Exact严格增加、Composite/Entity/Row/Item/Column全不降、fallback和invalid不增加，且自然产生非零mechanism engagement与prediction change，才授权下一次公开220。权威全集结果与审计分别为[`results/v24932_unicode_total_exact220_result_v1_20260809.json`](results/v24932_unicode_total_exact220_result_v1_20260809.json)和[`results/v24932_unicode_total_exact220_postresult_audit_v1_20260809.json`](results/v24932_unicode_total_exact220_postresult_audit_v1_20260809.json)。

## 2026-08-09：V2.49.35 冷复现完成 220 题，显示 Exact 的 rollout 方差

V2.49.34 先对普通文本 contextual-record projector 做了 fresh shared-prefix 检验。24 个任务中两臂共享页面、模型、prompt和预算；candidate 的投影在24/24任务发生变化并保留540个 contextual pair。原报告的两臂 Exact `0/24`、Composite `0.25` 不是可信负结果：gold row identity 是 `name`，而全部384个冻结 prediction row按visible task合法渲染为`name [ISO3]`；继承 evaluator 对规范化字符串做 exact compare，因而把48份表的所有实体、行和值都机械归零。该结果现已隔离，不能用于给机制零 credit。

V2.49.36 在预测、页面、gold value、数值比较和GO门完全不变的条件下，对完整24×2向量做append-only identity erratum。唯一修正是把exact visible `name`和exact visible `name [matching ISO3]`映射到同一canonical entity，错误ISO3仍拒绝。修正后baseline为Exact `0/24`、Item F1 `0.505208`、Composite `0.876302`；contextual-record为Exact `7/24`、Item F1 `0.927083`、Composite `0.981771`，增量Exact `+7`、Item F1 `+0.421875`、Composite `+0.105469`，其余指标不降。post-audit为`findings=[]`。这证明普通文本heading→record context在该fresh World Bank人口上具有显著outer utility，但不证明它已迁移到DeepWideBench：后者V2.49.35的220份content-free receipt合计只有11个visible row target、0个supported target–value pair。

随后 V2.49.35 对 V2.49.32 做 namespace-only 冷复现。运行时仍只读`{opaque_id, question}`，算法、GPT-5.6 keyless transport、30k/5k projector、每题搜索/抓取/模型/墙钟上限和`20/8`并发完全不变。唯一 forward 在`848.054045s`内完成220/220，220个表均由模型生成、fallback为0；预测冻结后，固定32-worker evaluator恰好评测每题一次，213 valid、7 error按零。最终 Exact `5/220`，Entity/Row/Item/Column F1 `0.713636/0.209985/0.388156/0.474951`，Composite `0.446682`。post-result audit为`audit_valid=true, findings=[]`。权威结果为[`results/v24935_unicode_total_replication_result_v1_20260809.json`](results/v24935_unicode_total_replication_result_v1_20260809.json)，审计为[`results/v24935_unicode_total_replication_postresult_audit_v1_20260809.json`](results/v24935_unicode_total_replication_postresult_audit_v1_20260809.json)。

与同算法 V2.49.32 相比，V2.49.35 的 Exact 从6降到5，而Composite从`0.421283`升到`0.446682`；Entity及三个F1也全部上升。该方向相反的变化说明 whole-table Exact 对独立检索页面、生成采样和evaluator error较敏感，单次跨运行差值不能识别 projector 或信息熵策略的因果贡献。与项目当前最佳 V2.48.57 的`9/220 / 0.457249`相比，本轮仍少4个Exact、Composite低`0.010567`，所以不是SOTA。

对 entropy credit assignment，V2.49.34–36/35 合起来支持更严格的三段式归因：首先检查机制是否发生；其次检查 observation 是否 identity/target/source-bound 且可采纳；最后用共享前缀、matched cost 的 prediction change 和 post-freeze outer utility给 signed credit。V2.49.36 的候选既有540个retained pair又有正outer utility，因而可获得正的机制级credit；原错误evaluator则说明credit本身也必须带evaluator/provenance有效性门。仅有更多pair、更多字符、projection change或单次全集分数波动仍不足以证明 information gain。下一实验应在 fresh/disjoint paired population 上把 entropy/IG 保持为 shadow predictor，比较它对真实边际效用的校准度；校准通过前不得把它用于公开 benchmark 的在线路由或credit更新。

## 2026-08-09：V2.49.38 完整 220——contextual-record 在真实检索页面上仍为零暴露

V2.49.37 先用两个新 World Bank target cells 和两种普通文本布局复核 contextual-record 机制。24 个任务的两臂共享相同页面、模型、prompt 和预算，candidate 在 13 题改变投影并保留 384 个 contextual pairs；但两臂都达到 Exact `24/24`、Composite `1.0`，因此预注册的 strict exact-gain 门判 NO-GO。这是 evaluator ceiling，不是负效应证据，也不授权公开 220。

按用户随后“先跑全集”的明确授权，V2.49.38 在固定 DeepWideBench 220 上做一次 exploratory single rollout。运行时仍只读 `{opaque_id, question}`；220 题、GPT-5.6 keyless model/search、每题 `4 query / 10 fetch / 3 model calls / 240s`、`20/8` 并发和 evaluator 均沿用 V2.49.35，唯一算法变化是 V2.49.28 projector 替换为 V2.49.33。forward 用时 `889.850088s`，220/220 model-generated、0 fallback；mapping/gold/evaluator 直到 prediction freeze 和 content-free audit 提交推送后才打开。

完整结果为 Exact `7/220=3.1818%`、Entity `0.681818`、Row/Item/Column F1 `0.216565/0.386647/0.471674`、Composite `0.439176`。固定 32-worker evaluator 恰好覆盖全部 220 条，210 valid、10 error-as-zero；post-result audit 为 `findings=[]`。相对 V2.49.35，Exact 增加 2 而 Composite 下降 `0.007506`；相对项目最佳 V2.48.57 的 `9/220 / 0.457249` 仍为 Exact `-2`、Composite `-0.018073`。所以它不是项目新最佳或 SOTA。

关键结论来自 220 份 content-free receipt，而不是分数差：1,302 个页面和约 431 万投影字符中，visible row targets 只有 11，bound/contextual target–value pairs 都是 0，context dependency addition 也是 0。V2.49.33 在这次全集 forward 中根本没有自然触发；跨 rollout 的 Exact 波动不能冒充 projector 效果。可直接归因的瓶颈是开放世界 row discovery/schema binding：现有 `visible_row_targets()` 只接受问题显式枚举的实体，因此 209/220 题无法产生 row target。11,939 个 action sources 全缺 title、69 次 backfill 只覆盖 47 个 URL、surviving union lead 为 0 仍值得审计，但不能据此认定 title 是主根因；同 response citation 可回填 title，query-local lead 会按稳定顺序先于同 URL action source 去重，fetch 后还可从 HTML 恢复标题。现有证据排除的是继续堆搜索次数、字符窗口或 heading context，而不是证明 source-title 修复会提分。

对信息熵 credit assignment，这轮给出一个更强的 production 负控制：即使系统调用 443 次模型、378 次搜索、1,882 次 fetch 并获得 7 个 exact tables，只要目标机制没有产生 admissible bound observation，它的 realized epistemic/task credit 就必须为 0。下一可识别实验应借鉴 WebSwarm 与 Search–Inspect–Fetch 的分工，但把协作产物收敛为 source-bound cell/record ledger：每个 observation 先通过 source identity、record identity、entity、target、value、独立来源与冲突 gate；IG/entropy 只预测在该 ledger 上继续 inspect/fetch 的 value-of-computation。最终 signed credit 必须由 shared-prefix deletion/replacement 或 sibling continuation 的 post-freeze outer utility决定，而不能由网页数、字符数、token数或未绑定的 entropy reduction决定。

V2.49.39 随后把这个定位实现成 build-only 的开放世界 schema-bound record ledger。它不从 evaluator 或问题外元数据猜 row，而只接受同次 fetched page 中 exact visible-schema-bound table，或 exact identity/target label 的连续 record；source URL/host、record、row、target 和 value 被原子封装，跨页、错表头、坏列数和冲突均 fail closed。14 个定向测试和 55 个父链联合回归通过，且未绑定 observation 的 positive credit 机械保持 0。它解决的是“如何在未预枚举行时形成可审计 observation”的工程缺口；尚未证明这些 observation 改善外部终局 utility，更未验证四层风险或 entropy credit。下一证据必须来自 fresh shared-prefix、matched-cost 外部人口，且同时满足非零机制暴露、prediction change、Exact 增益与所有质量指标不降。

V2.49.40 的首个外部门在任务物化前因 source-capacity precondition fail closed：预注册需要 200 条记录，冻结响应只有 196 个 eligible real records；模型、预测和 evaluator 调用均为 0，不能解释为质量负结果。全新 V2.49.41 改用历史未见的 `SP.POP.TOTL@2021`，在 18 个 task-disjoint target cohorts 上比较 V2.49.33 与 V2.49.39；每题两臂共享同一冻结 page、prompt、GPT-5.6、调用次数与 30k/5k cap，问题只给 cohort predicate 和 schema，不给 row identities。18/18 projection 改变，864 个 admissible cell observations 中 747 个被投影保留；forward 36 个输出、0 failure，预测冻结后才生成 gold/evaluator。

外部结果显示 schema-bound ledger 将 Entity recall 从 `0.5` 提到 `0.847222`，Row/Item F1 从 `0.666667/0.666667` 提到 `0.903704/0.903704`，Composite 从 `0.708333` 提到 `0.913657`，Column F1 都为 `1.0`。但两臂 Exact 均为 `0/18`，因此预注册 strict gate 判 NO-GO，不能授权公开 220 或 SOTA 主张。这个结果首次给出“开放世界行发现和原子 schema binding 改善 outer table quality”的直接 external evidence，同时也说明局部 coverage/F1 提升仍不足以获得整表 credit。结合 `747/864` retention，下一可识别假设是 5k/page 内的 ledger 表示效率与完整 record retention，而不是增加搜索量或给 raw entropy drop 正 credit；仍须在 fresh/disjoint population 上用 Exact 与所有质量非回退共同验证。

V2.49.42 将 V2.49.39 每条 record 重复的 source、binding、row-label 和 target-label 改成一次 page-level schema/source header，record 行只保留 sealed record ID、row key 与 target-index/value；discovery、conflict gate、record/observation seal 和所有预算不变。合成页 ledger 字符从 `3536` 降到 `1645`，`48/48` observation 与 `16/16` record 在同一 5k cap 内保留。V2.49.43 随后在 fresh `SP.POP.TOTL@2020` 的 18 个 task-disjoint cohorts 上做 representation-only shared-prefix gate：verbose 与 compact 共用同一 records/observations、页面、prompt、模型与一次调用。compact 达到 `864/864` retention；post-freeze 结果从 verbose Exact `2/18`、Composite `0.913095` 提升到 compact Exact `13/18`、Composite `0.973958`，Exact `+11`、Entity `+0.118056`、Row/Item 各 `+0.062698`，所有指标不降，strict gate 为 GO。

这个结果把可归因主张进一步收紧：收益来自“已通过 identity/schema/source gate 的 observation 在有限上下文中的 record-atomic 编码与完整保留”，不是更多搜索、更多 token、一般 entropy reduction 或 credit shaping。它支持将 compact ledger 迁移到 DeepWideBench 做一次受控验证，但不证明四层风险校准、IG action selection、signed credit 或 SOTA；这些主张仍需各自的 intervention/calibration 证据。

V2.49.44 将 compact ledger 接入完整 DeepWideBench 220，保持 task vector、GPT-5.6 transport、`4 query/10 fetch/3 model/240s`、`20/8` 并发与 evaluator 不变。forward `870.668666s` 完成220/220、0 fallback；206 evaluator-valid、14 error-as-zero，最终 Exact `6/220`、Entity `0.704545`、Row/Item/Column F1 `0.206221/0.389805/0.477624`、Composite `0.444549`。相对 V2.49.38 的 Exact 下降1、Composite上升`0.005373`；相对项目最佳 V2.48.57 仍低3个Exact和`0.012700` Composite，因此不是新最佳或SOTA。

更关键的是220份content-free receipt再次给出生产负控制：1,313 pages和约433万投影字符中虽解析出1,092个visible schema columns，却没有发现任何schema-bound record、row或admissible observation。V2.49.42在真实forward中未自然触发，所以本轮分数不能归因于compact ledger；external GO证明的是“结构已经形成后如何压缩”，尚未解决“native fetch文本如何可靠恢复结构”。后续创新点应落在真实HTML-to-text布局上的header/record recovery与provenance-preserving binding，并在external frozen native-layout人口先验证；raw entropy、页面数和跨rollout波动仍不得获得正credit。

## 2026-08-09：V2.49.45–48——native-layout 外部门通过，但完整 220 未触发新机制

V2.49.45 用一个窄而可审计的规则扩展 schema binding。删除 bracket code 与四位年份后，page label 和 visible column 只有在多 token ASCII multiset 完全相同、且全表映射唯一一对一时才能绑定。单 token、非 ASCII、重复列、共享 signature、坏列宽、跨页或冲突全部 fail closed。V2.49.46 的 47/47 clean-build tests 和 label-blind audit 均通过；entropy/IG 仍仅是 shadow signal，signed credit 恒为 0。因此该实现检验的是 provenance-preserving schema recovery，不是在线 credit shaping。

V2.49.47 在 fresh `SP.POP.TOTL@2019` 的 18 个 task-disjoint cohort 上检验真实 native HTML 经生产 `html_to_text` 后的布局。两臂共享冻结页面、prompt、GPT-5.6、调用次数和预算。candidate 在 18/18 题改变 projection，形成 18 个 signature-bound tables、288 个 row keys 与 864/864 admissible/retained observations。Exact 从 `0/18` 升至 `13/18`，Composite 从 `0.708333` 升至 `0.973958`，Entity 从 `0.500000` 升至 `0.965278`，Row/Item F1 均从 `0.666667` 升至 `0.965278`，Column F1 保持 `1.0`。这个 matched shared-prefix 结果支持 native-layout schema recovery 的外部效用，但 claim scope 明确排除 DeepWideBench、entropy/signed credit 与 SOTA。权威结果与审计为 [`results/v24947_native_layout_signature_external_result_v1_20260809.json`](results/v24947_native_layout_signature_external_result_v1_20260809.json) 和 [`results/v24947_native_layout_signature_external_postresult_audit_v1_20260809.json`](results/v24947_native_layout_signature_external_postresult_audit_v1_20260809.json)。

V2.49.48 随后完成完整 DeepWideBench 220。forward 仍只读 `{opaque_id, question}` 与同次 fetched pages，mapping、gold、category、question type、split 和 evaluator 在全部 prediction 冻结前保持关闭。唯一 single-pass forward 用时 `864.734237s`，220/220 model-generated、0 fallback，共 `10,759,349` system tokens。固定 32-worker evaluator 对全部冻结预测各评一次，用时 `277.104120s`；213 valid、7 error-as-zero。最终 Exact `6/220=2.7273%`、Entity `0.672727`、Row/Item/Column F1 `0.221687/0.386769/0.467035`、Composite `0.437055`。相对 V2.49.44，Exact 不变而 Composite 下降 `0.007494`；相对项目单轮最佳 V2.48.57，Exact 少3个、Composite低 `0.020194`。因此它不是 benchmark 提升、leaderboard 结果或 SOTA。权威结果与审计为 [`results/v24948_schema_signature_exact220_result_v1_20260809.json`](results/v24948_schema_signature_exact220_result_v1_20260809.json) 和 [`results/v24948_schema_signature_exact220_postresult_audit_v1_20260809.json`](results/v24948_schema_signature_exact220_postresult_audit_v1_20260809.json)。

本轮最有识别力的证据仍是 content-free mechanism receipt。1,271 个页面包含 5,882 个 pipe groups、8,323 个 pipe lines 和 63 个 schema-touching lines，但只形成4个 exact header mappings；signature header mappings、discovered records/rows 和 admissible observations全部为0。V2.49.45 在完整运行中没有自然触发，故 `6/220` 不能获得 signature recovery 或 entropy credit。结果也修正了下一假设：问题不只是 HTML-to-text 是否保留 pipe group，而是生产页面 header 与 visible schema 之间常含部分 token、同义词、单位或更复杂的对齐差异。

下一实验应把 header alignment 从终局 score 调参中分离。在新的 benchmark-external、生产同形 frozen native-layout population 上，先做不读取 gold 或题类的 token-overlap bipartite 诊断，再逐项检验唯一 partial signature 和受控 synonym/unit binding。候选只有在歧义仍 fail closed、自然产生非零 schema-bound observation、改变 prediction、提高 Exact，且 Composite、Entity、Row、Item、Column、fallback 与 invalid 全不退时，才能进入下一次公开 220。信息熵可预测候选 observation 或 action 的 value of computation，但在 admissibility、identity/source binding 与 matched counterfactual outer utility 建立前，不能直接按 entropy drop 分配正 credit。
## 2026-08-11：从信息量扩张转向可验证 record proposal——V2.50.64–69

三次完整 DeepWideBench aggregate 给出了清晰的负结果：V2.48.57 用约`3.781M` tokens得到 Exact `9/220`、Composite `0.457249`；V2.50.30和V2.50.57把总token提高到`13.973M/14.302M`，但只得到`7/220 / 0.450291`与`6/220 / 0.449960`。更多query refinement、page context和token没有建立质量增益，新增record/page-self分支又都零暴露。因此，raw entropy reduction、检索量和上下文长度不能获得正credit；项目将一次现有模型调用重新分配给source-record proposal，而不扩大任何预算。

V2.50.65/66 把proposal与admission分离。模型可以建议记录，但确定性verifier只接受来自同一次forward fetched page的一段连续原文；row identity、source field和value必须都逐字出现在quote中，source label还必须唯一词法绑定到visible target column。不同quote coordinate上的同名实体保持不同record，同一coordinate冲突则fail closed。control与candidate共享plan、queries、search responses、pages和proposal cost，candidate只把verified blocks前置到与control严格等长的evidence。因此该设计检验provenance-preserving representation，不检验“模型置信度高就给credit”，也不把entropy drop当reward。

V2.50.68 在20个历史literal-zero PyPI包上做了唯一一次20路外部门。运行`86.33s`，20/20 terminal、19题双臂model success、1题failure-as-zero；查询、抓取和模型预算均守恒。但verifier exposure为`0/20`，prediction change仅`2/20`，机制门严格NO-GO，evaluator未获授权。post-freeze content-free diagnosis进一步显示，19次proposal都成功返回严格JSON；18次是合法空records，唯一非空proposal被field-binding gate拒绝。这个结果没有质量含义，却准确排除了“严格single-quote record会在production pages自然触发”的假设。

该负结果也揭示评测工程中的一个重要区分：`search_request_failures=32`来自hosted multi-query marker/citation mapping的query-local error计数；19个完成题仍均产生两波有效retrieval receipt，且transport、hard-total-wall、fetch helper/deadline和model request failure均为0。可恢复的mapping缺口影响source coverage，但不等于transport hard failure。后继协议应分别记录`coverage/mapping failure`与`terminal effect failure`，避免把两者混为可靠性退化；V2.50.68的冻结判定仍保持原样，不做事后改门。

下一可检验假设是field-local provenance：一个真实record的多个字段常分散在同一页面的不同连续片段，不会全部落入单一quote。允许每个target field携带独立的同页verbatim quote，同时要求所有quote共享一个可验证row identity/record anchor，可以增加自然reach而不牺牲source/identity边界。跨页、跨identity、跨release拼接和同target冲突仍必须拒绝。只有fresh/disjoint matched-cost外部门先证明非零verified records、prediction change和零terminal hard failure，才允许post-freeze quality evaluator；Exact严格增加且Composite/Entity/Row/Item/Column、invalid/fallback全不退后，才有资格进入下一次DeepWideBench 220。

对信息熵credit assignment，这一轮仍是负控制而不是支持证据。proposal合法、页面充足、模型调用成功，但admissible observation为0，所以realized epistemic/task credit必须为0。熵或IG最多作为“下一个inspect/fetch动作可能产生可采纳observation”的shadow predictor；正signed credit仍需`admissibility → identity/source binding → matched counterfactual prediction change → post-freeze outer utility`完整链条。当前项目最佳仍为V2.48.57的Exact `9/220`、Composite `0.457249`；无Avg@4、leaderboard或SOTA证据。

V2.50.70–72 将下一假设实现为build-only的field-local verifier。与single-quote不同，每个字段保留自己的连续verbatim quote，但都必须包含同一页上唯一的record anchor；anchor又必须包含row identity。合成测试证明，当首末字段跨度超过1,200-character quote cap时仍能形成一个verified record，而cross-page、缺anchor、非唯一anchor、wrong identity、ambiguous label与same-anchor value conflict均fail closed。matched runtime继续共享plan、4 queries、最多10 fetch和proposal，并保持每臂3次有效模型调用、240秒、60k evidence与等长对照。67/67 clean-build tests和label-blind/evaluator/credential审计通过，但尚无external或quality证据；entropy/IG signed credit仍为0。

V2.50.73 随后在fresh/disjoint的20个PyPI任务上做了唯一production external mechanism gate。20/20任务在`92.28s`内完成，双臂均20/20 model success，没有terminal transport、timeout、helper、model或outer failure；两臂查询、抓取、模型调用与evidence长度匹配。28条query-local mapping failure是coverage诊断，不是终端失败。这一结果排除了“field-local失败来自运行可靠性”的解释。

但机制仍严格NO-GO：verified exposure只有`1/20`，低于8题门槛；prediction change为`3/20`，低于4题门槛。V2.50.74 content-free归因显示，20次proposal调用全部成功且返回严格JSON，18次主动给出空records，2次非空proposal中仅1条通过、另1条被field label/value binding拒绝。因此，field-local约束把自然reach从`0/20`推到`1/20`，却没有解决主要的proposal abstention。并且只有1题evidence改变，故3题prediction difference中至少2题不能归因于candidate，而应视为独立synthesis随机性。没有运行evaluator，也没有DeepWideBench或quality新结论。

这一外部门进一步收紧了“信息熵用于credit assignment”的可识别条件。网页、模型调用和合法proposal格式本身都不是可计分observation；18个空proposal的realized credit必须为0，唯一verified observation在没有post-freeze outer utility前也只能保持shadow credit。熵或IG可以预测某个inspect/fetch/proposal动作产生admissible record的概率，但正signed credit必须来自matched intervention对终局utility的增量，而不是entropy drop、token量、网页量或两次随机rollout的差异。

下一候选应把anchor从“每个field quote都必须复制包含的字符串”改为“同页record-region边界”。唯一anchor包含row identity，并确定一个有界region；每个field quote只需在该region内逐字唯一出现，同时机械验证source label与value。这样可提高字段远离anchor时的reach，却仍禁止跨页、跨identity、跨record/release和冲突拼接。该设计必须先在fresh production-isomorphic外部门证明非零自然exposure与treatment-caused prediction change，且不增加任何检索、模型、上下文或时间预算；通过前不应再消耗一次公开220。

V2.50.75/76实现并接入了这一anchor-bounded方案。模型只给唯一anchor、identity和字段label/value，verifier在同页1,600字符region中选择唯一最短label–value跨度并自行构造quote；schema header可重复字段名，但并列最短坐标、重复quote、跨region、错identity或冲突仍拒绝。68/68 clean-build测试和label-blind审计通过。V2.50.78随后冻结20个历史literal-zero的新package并完成唯一paired forward：`79.15s`内20/20完成、双臂20/20 model success、零terminal hard failure，查询、抓取、模型调用与evidence长度严格匹配。

结果仍为机制NO-GO。verified exposure是`0/20`；prediction difference虽为`5/20`，但没有任何candidate evidence改变，因此这些差异全是独立synthesis波动，不能当作treatment effect。V2.50.79进一步聚合content-free funnel：20次proposal均成功且JSON合法，19次返回空records，唯一非空的1 record/3 fields被label/value binding拒绝；更上游40个wave receipt中的discovered、admissible和retained records也全为0。这说明放宽anchor几何约束没有解决`page/entity identity → proposal-ready record`的转换瓶颈。它不证明页面缺少相关事实，也没有质量、DeepWideBench或SOTA含义。

对检索系统设计，这个负结果支持把下一层从“让LLM更积极地提record”改成“先机械建立entity-specific page boundary”。visible row identity只能与同轮页面的唯一title/primary heading做精确或唯一规范化绑定；之后field verifier才在该identity-bound region内寻找source label/value。这个顺序与WebSwarm式search/inspect分工兼容，但共享产物必须是provenance-sealed record，而不是agent confidence或未绑定摘要。title/identity歧义、跨页拼接、字段坐标并列和冲突继续fail closed，且必须在fresh production-isomorphic人口先证明natural reach后再考虑公开220。

对entropy credit assignment，V2.50.78是更严格的零对照：系统有40个retrieval wave、20个成功proposal call和5个终局prediction difference，但admissible treatment observation为0，所以所有signed credit必须为0。IG可以作为未来identity-binding或inspect动作的shadow value-of-computation预测量；只有`identity/source admissibility → matched evidence intervention → treatment-caused prediction change → post-freeze outer utility`完整成立，才能给正credit。当前benchmark分数仍是最新V2.50.57的`6/220 / 0.449960`，项目最佳V2.48.57的`9/220 / 0.457249`，没有SOTA证据。
