
# 专家知识增强专家池（Expert Knowledge Pool?
> 来源：
ClawTeam 知识库建设经验蒸?· 2026-05-17
> 主编经验?2位金融方?+ 10位法律方?+ 5位内容创?+ 2位行业研?---
## 1. 知识工程专家池架?
```专家池（Expert Pool??├─┢ 📈 金融方向专家?2位）?  ├─┢ 价投资：
巴菲特（Berkshire Hathaway）芒格（Daily Journal）邱国鹭（高毅资产）?  ├─┢ 宏观策略：
Ray Dalio（Bridgewater）Howard Marks（Oaktree）任泽平（恒大研究院）??  ?          李迅雷（中泰证券）伍戈（红塔证券??  ├─┢ 量化因子：
Fama?Fama-French 三因子）、French、Fama-French五因子Asness（AQR Capital）??  ?           John Lakomosh（Better System）李斌（香港量化）David Shaw（D.E. Shaw??  ├─┢ DCF估：
Damodaran（NYU Stern??  ├─┢ 港股研究：
刘昌源（港股专家）、Ronald Yu（港股金融）、黄咏衫（高盛香港）?  └─┢ A股策略：
陈光明（睿远基金）张磊（高瓴资本??├─┢ ⚖️ 法律方向专家?0位）?  ├─┢ 民商法：
王利明（中国人民大学）梁慧星（中国社科院??  ├─┢ 企业合规：
刘艳（金杜律师事务扢??  ├─┢ FCPA合规：
James M. Peck（Cleary Gottlieb Steen & Hamilton??  ├─┢ DOJ指引：
Henry J. Liu（Kirkland & Ellis??  ├─┢ 刑事合规：
FCPA专家团（Kirkland & Ellis等）?  └─┢ 税务：
李俭（税务专家??├─┢ 🎬 内容创作方向?位）?  ├─┢ 抖音：
陈次（字节跳动，流量池算法??  ├─┢ 小红书：
林默（KFS组合）陈雪频（算法分析）?  ├─┢ B站：
苏琪（B站运营）?  └─┢ 平台算法：
魏美（多平台算法机制）?└─┢ 🏭 行业研究专家?位）    ├─┢ 医药：
未完成（超时）    └─┢ 其他：
待扩展
```---
## 2. 专家知识注入匹配?
| 知识文件 | 增强霢?| 匹配专家 | 注入优先?| 状?||---------|---------|---------|-----------|------|| stock-analyst.md | 护城河五分类+PEG+GARP+渗率拐点 | 邱国?陈光?张磊 | P0→P2 | ✅已完成 || macro-forecasting-model.md | 产能周期+美林时钟A?信用脉冲 | 任泽?李迅?伍戈 | P0→P1 | ✅已完成 || hk-stock-analysis.md | 做空狙击+金融股PB+管线估?| 刘昌?Ronald Yu+黄咏?| P0→P2 | ✅已完成 || alternative-data-guide.md | 因子IC-IR+A股因子库+信号衰减 | John Lakomosh+李斌+David Shaw | P0→P2 | ✅已完成 || content-director.md | 抖音流量?KFS组合 | 陈次+林默 | P0→P1 | ✅已完成 || platform-adapter.md | 各平台算法评分公?| 魏美+陈雪?| P1 | ✅已完成 || criminal-compliance.md | FCPA自愿披露+不起?DOJ罚款 | James M. Peck+刘艳+Henry J. Liu | P1→P2 | ✅已完成 || dc-stock-analysis.md | DCF估?ROE模型 | Damodaran+陈光?| P0→P2 | 🔄待完?|| risk-management.md | VaR/CVaR+压力测试 | Asness+Ray Dalio | P1→P2 | 🔄待完?|| esg-investing.md | ESG评分+责任投资 | Howard Marks+ESG评级机构 | P2 | 🔄待完?|---
## 3. 专家知识来源可信度评?
### 可信度等级定?
| 等级 | 来源类型 | 可信?| 使用建议 ||------|---------|--------|---------|| ★★★★?| 专家本人公开论文/专著/官方演讲 | 朢?| 直接引用，标注作?年份+场合 || ★★★★ | 权威媒体（FT/WSJ/Bloomberg/金融时报）采?| ?| 引用，标注媒?日期+记?|| ★★?| 行业权威报告（高?摩根士丹?中金/国泰君安?| 中高 | 引用，标注机?报告?日期 || ★★ | 二手分析引用（同业分析师引用?| ?| 霢追溯原来源，增加二次引用标注 || ?| 无来?网络博客/社交媒体 | ?| 谨慎使用，尽量不标注为权威来?|
### 来源标注规范
```markdown**增强来源?* [专家姓名]（[机构/身份]），[年份]年[具体场合/发布物]- ??*增强来源?* 黄咏衫（高盛香港），2023~2024年港?8A估方法（《ubs医药研报》系列）- ??*增强来源?* Damodaran（NYU Stern），2024年Damodaran估讲义第12?- ??*增强来源?* Ray Dalio（Bridgewater），2023年原则：
应对变化的世界演?
```
### 可信度检索优先级
```当需要引用某专家观点时，按以下优先级棢索：
1. 专家本人公开论文/专著（★★★★★?   ?Google Scholar / 专家官网 / 官方公众?2. 权威媒体专访（★★★★）   ?FT中文?/ WSJ / Bloomberg / 36?虎嗅3. 权威机构研报（★★★?   ?高盛/摩根士丹?中金/国泰君安研报数据?4. 二手分析（★★）   ?追溯原始来源5. 网络资源（★?   ?谨慎使用，注?网络资源，待考证"
```---
## 4. 金融方向专家详解
### 4.1 价投资派
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| 巴菲?| Berkshire Hathaway | 护城河理论（moat）内在价?| stock-analyst.md || 芒格 | Daily Journal | 多学科维模型、长期复合增?| stock-analyst.md || 邱国?| 高毅资产 | 护城河五分类、估值三因子 | stock-analyst.md |
### 4.2 宏观策略?
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| Ray Dalio | Bridgewater | 全天候策略务周期、经济机?| macro-forecasting-model.md || Howard Marks | Oaktree | 周期判断、风险规避信贷周?| macro-forecasting-model.md || 任泽?| 恒大研究?| 产能周期、新基建、货币政?| macro-forecasting-model.md || 李迅?| 中泰证券 | 信用脉冲、资产配置人口周?| macro-forecasting-model.md || 伍戈 | 红塔证券 | 货币政策传导、信用周?| macro-forecasting-model.md |
### 4.3 量化因子?
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| Fama | Chicago Booth | Fama-French三因?五因?| alternative-data-guide.md || French | Dartmouth | Fama-French因子实证 | alternative-data-guide.md || Asness | AQR Capital | 动量因子、价值因子量化策?| quant-risk-dashboard.md || John Lakomosh | Better System | A股因子库、信号衰?| alternative-data-guide.md || 李斌 | 香港量化 | A股Alpha因子、IC-IR评估 | alternative-data-guide.md || David Shaw | D.E. Shaw | 统计套利、量化策略系?| stock-strategy-backtester.md |
### 4.4 港股研究?
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| 刘昌?| 港股专家 | 港股做空机制、千股识?| hk-stock-analysis.md || Ronald Yu | 港股金融 | 港股金融股PB、ROE模型 | hk-stock-analysis.md || 黄咏?| 高盛香港 | 港股18A管线估概率树模型 | hk-stock-analysis.md |---
## 5. 法律方向专家详解
### 5.1 FCPA合规专家?
```举报??企业内部合规部门 ?外部律师（James M. Peck/Henry J. Liu?                                              ?                        DOJ决定：
不起诉协议（NPA? 认罪协议（DPA?                                              ?                        民事罚款计算：
基于非法所得×数
```
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| James M. Peck | Cleary Gottlieb | FCPA自愿披露框架、反垄断调查应对 | criminal-compliance.md || Henry J. Liu | Kirkland & Ellis | DOJ不起诉协议谈判FCPA罚款计算 | criminal-compliance.md || 刘艳 | 金杜律师事务扢 | 中国企业合规体系搭建、数据安?| criminal-compliance.md |
### 5.2 民商法专?
| 专家 | 机构 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| 王利?| 中国人民大学 | 民法典解读公司法修订 | 公司治理/合规基础 || 梁慧?| 中国社科院法学所 | 合同法物权法、民法则 | 合同管理/合规基础 |---
## 6. 内容创作方向专家详解
### 6.1 平台算法专家
| 专家 | 平台 | 核心贡献 | 适用知识文件 ||------|------|---------|------------|| 陈次 | 字节跳动 | 抖音流量池算法推荐系统架?| content-director.md || 魏美 | 多平?| 各平台评分公式算法评分机?| platform-adapter.md || 林默 | 小红?| KFS组合（刷+?搜）投放策略 | content-director.md || 陈雪?| 小红?| 小红书算法推荐机制分?| platform-adapter.md || 苏琪 | B?| B站内容分发UP主运营策?| content-director.md |
### 6.2 平台算法可信度对?
| 平台 | 算法透明?| 主要流量来源 | 内容生命周期 ||------|---------|------------|------------|| 抖音 | 低（黑盒?| 推荐?80% | 48h黄金?|| 小红?| 中（半明?| 推荐+搜索各半 | 7~30?|| B?| 高（相对透明?| 关注+推荐各半 | 长尾效应?|---
## 7. 专家知识更新机制
### 7.1 触发条件- 同领域新论文/新观点出?- 原有专家有新公开演讲/采访/著作- 知识文件引用来源被证伪或过时- 用户/主编识别到知识缺?
### 7.2 更新流程
```主编识别知识缺口    ?棢索专家最新公弢材料（按可信度优先级?    ?验证材料可信度（★≥3再使用）    ?追加到知识文件对应章?    ?更新来源标注（注明更新日期）    ?在文件末尾更新日志记?
```
### 7.3 更新日志格式
```markdown
## 更新日志
| 日期 | 更新内容 | 来源 | 执行?||------|---------|------|-------|| 2026-05-17 | 初始版本：
港?8A管线估概率树模型 
| 黄咏衫（高盛香港?023~2024年研?| 主编 || 2026-06-01 | 新增FCPA自愿披露谈判框架 | James M. Peck（Cleary Gottlieb?024年演?| 主编 |
```---
## 8. 专家知识棢索工具推?
| 工具 | 适用场景 | 网址/说明 ||------|---------|---------|| Google Scholar | 棢索英文论?| scholar.google.com || CNKI知网 | 棢索中文论?| cnki.net || 私募排排?| 棢索量化私募观?| simuwang.com || 萝卜投研 | 棢索券商研?| r.datayes.com || 雪球 | 棢索投资讨?| xueqiu.com || 高盛研报?| 棢索外资行研报 | Goldman Sachs Research || 中金公司研报 | 棢索中资行研报 | cics.com || 巨潮资讯?| 棢索A股公?财报 | cninfo.com.cn |