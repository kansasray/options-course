# 美股選擇權:先看懂損益圖,再談以小博大 — 課程設計

> 決策日:2026-08-25。框架:curate-course v2 + **本 fork 新增的單元 `figures` 欄位**(commit a6b4726)。
> 課程目錄:`courses/options/`。KOL 研究:`research/kol-strategies.md`(引文逐字驗證 50/50)。

## 一、定位與三個輸入

| 輸入 | 內容 |
|---|---|
| 使用者需求 | 美股選擇權、**圖表輔助**、容易理解、收錄 Gozilla 與 Led 的常用策略 |
| KOL 資料 | Gozilla=Threads `godzilla.us`(選擇權內容 10/73 篇,CC 為核心);Led=`_lepetitdejeuner`(20/58 篇,CSP 為核心)。出處:atlas threads-kol 資料,窗口 2026-05 至 08 |
| 供給盤點 | 14 主題全部合格片 ≥10 支(基礎 34、CC 32、LEAPS 32);最薄=履約與指派(10 支、中文 0)。`docs/plans/supply-survey.json` |

**KOL 呈現原則(已與使用者確認方向)**:策略寫進課程文字+損益圖並標明出處,影片用同主題教學片。兩位的引文主要放在**圖表 caption**(圖+話一起看)與單元散文;績效數字一律標「本人自述、未驗證」。

## 二、章節與配額(24 單元 / 88 項目 / 112 欄位)

| 章 | 標題 | 單元 | 項目 | 供給依據 |
|---|---|---|---|---|
| CH1 | 選擇權是什麼:四個基本部位 | 3 | 12 | 基礎 34 支(中文 16) |
| CH2 | 權利金:時間價值與 IV | 3 | 11 | 定價 14 + IV 22 |
| CH3 | Greeks:看得懂就好 | 2 | 8 | 27 支;刻意壓低,新手課不做希臘字母崇拜 |
| CH4 | 到期、履約與指派 | 2 | 5 | **全課最薄**(10 支、中文 0),留空可接受 |
| CH5 | Covered Call(Gozilla 的主策略) | 3 | 11 | 32 支;參數規則取自 Gozilla |
| CH6 | Sell Put 與 Wheel(Led 的主策略) | 3 | 12 | CSP 23 + Wheel 25;流程取自 Led |
| CH7 | 價差與中性策略 | 3 | 12 | spreads 26 + condor 29;**明標不從兩位取材**(資料中無) |
| CH8 | 下單、倉位與風險 | 3 | 12 | 26+20+22 |
| CH9 | 兩位的共同框架與誠實界線 | 2 | 5 | 綜合章:保守賣方紀律敘事+引文;影片配紀律/錯誤主題 |

單元明細(id 固定):
- ch1-u1 四個基本部位(long/short × call/put)·4|ch1-u2 買方與賣方:權利、義務與保證金·4|ch1-u3 為什麼是「美股」選擇權:規格、流動性與台灣人的管道·4
- ch2-u1 權利金=內在+時間價值·4|ch2-u2 時間衰減與到期日選擇·3|ch2-u3 隱含波動率與 IV crush·4 →(concept-3)
- ch3-u1 Delta 與 Gamma:方向與加速度·4|ch3-u2 Theta 與 Vega:時間與波動·4
- ch4-u1 到期那天發生什麼:ITM/OTM 與自動履約·3|ch4-u2 提前指派與除息·2
- ch5-u1 Covered Call 的損益結構·4 →(concept-1)|ch5-u2 Gozilla 的參數:delta 0.25–0.3、短天期、50–80% 水位·3|ch5-u3 Roll 還是不 Roll·4
- ch6-u1 Sell Put 與現金擔保·4|ch6-u2 Led 的流程:回檔開倉、小賺平倉·4|ch6-u3 Wheel:CSP 與 CC 的循環·4
- ch7-u1 垂直價差:把風險畫成一個盒子·4|ch7-u2 Iron Condor 與中性策略·4|ch7-u3 該不該用價差:成本、滑價與複委託限制·4
- ch8-u1 下單實務:報價、滑價、組合單·4|ch8-u2 倉位與風險管理·4 →(concept-2)|ch8-u3 新手最常見的死法·4
- ch9-u1 兩位殊途同歸的保守賣方框架·3|ch9-u2 誠實界線:自述績效、觀察窗口、你該自己驗的事·2

## 三、圖表系統(本課的差異化)

框架新欄位:單元 `figures: [{src, alt, caption}]`,SVG 放 `courses/options/assets/charts/`,原樣進 dist。
生成:`scripts/gen_payoff_figures.py`(純標準庫,程式化畫損益圖,不進 dist)。

**風格規範**(深淺主題皆可讀,`<img>` 內 SVG 吃不到頁面 CSS 變數,顏色寫死中性值):
軸線/文字 `#8b949e`;獲利區 fill `rgba(46,160,67,.22)` stroke `#2ea043`;虧損區 fill `rgba(248,81,73,.20)` stroke `#f85149`;履約價虛線 `#8b949e`;字體 system-ui;viewBox 640×400。

圖表清單(24 張起,對應單元):四基本部位×4、權利金分解、theta 衰減曲線、IV crush 前後、delta 斜率圖、gamma 加速度、到期流程圖、CC 損益、**Gozilla 參數帶狀圖**(delta 帶+水位比例)、roll 決策樹、CSP 損益、**Led 流程圖**(回檔開倉→小賺平倉/接股分岔)、wheel 循環圖、bull put spread、bear call spread、iron condor、倉位金字塔、**兩位框架對比圖**。KOL 引文放對應圖的 caption(含日期)。

## 四、立場頁(3 條,全掛文獻)

1. **concept-1(ch5-u1)**:賣方權利金是風險補償,不是免費午餐——covered call 的「穩定收入」以放棄上檔+承受下檔為代價。候選文獻:Israelov & Nielsen (FAJ 2014)、Whaley BXM 研究(JPM)。
2. **concept-2(ch8-u2)**:散戶選擇權交易的實證績效——多數研究顯示顯著落後。候選:Bauer/Cosemans/Eichholtz (J Banking & Finance 2009)、Barber & Odean (JF 2000)。
3. **concept-3(ch2-u3)**:「以小博大」的數學——買方便宜的是權利金,貴的是機率;OTM 選擇權系統性昂貴。候選:Bondarenko (put 昂貴性)。分級可能是 mixed,照實標。

**期刊白名單**(Crossref 也收掠奪性財經期刊,比照量子課防線):Journal of Finance、Journal of Financial Economics、Review of Financial Studies、Financial Analysts Journal、Journal of Banking & Finance、Journal of Derivatives、Journal of Portfolio Management、Management Science、Quarterly Journal of Finance。**不在清單一律不採,寧可留空**。

證據階梯:`peer-reviewed-study:1, index-data:2, replication:2, working-paper:3, practitioner-report:4, self-reported:5`。KOL 收入數字=self-reported,**只出現在 caveats,永不當證據**。

## 五、策展委派的固定條款(從前三門課的對抗審查學來,一條不可少)

1. **`tight`/`weak` 渲染語意**:tight=「常見的錯誤做法」、weak=「應該建立的紀律」,**只能填真錯誤/真紀律**,策展筆記留在 journal,不寫入資料檔(三門課審查的共同 CRITICAL/MAJOR)。
2. **assessment 只能寫驗證過的檢核**:不可發明 UI 元件(單勾雙勾教訓)、不可給沒驗過的數字判準(69 倍光速教訓);券商介面相關檢核一律寫「以你的券商實際畫面為準」而不指定按鈕位置。
3. **查詢污染源(本課專屬)**:排除**印度市場**(Nifty/Bank Nifty/lot size,`option trading` 高觀看幾乎全是)、**台指選擇權**(中文搜尋主要污染)、A 股/港股期權、加密貨幣期權;`premium` 撞保險、`assignment` 撞作業代寫。
4. 慣例條款:絕對路徑 out、oEmbed 200 才收、標題照抄 oEmbed、限流=空輸出要重試、單頻道 ≤15%、留空要 note。
5. **內容紅線**:宣稱「穩賺/零風險/月入 X%」而無風險說明的片不採(除非明確在反駁);跟單喊單頻道不採。

## 六、合規

footer + llms 雙免責:教育內容非投資建議;選擇權買方可全額歸零、未避險賣方損失可遠大於權利金;兩位創作者策略引自公開貼文、僅為作法示範、非本課程或本人背書;自述績效未經驗證;交易前確認自身券商之權限層級(option level)與台灣複委託限制。

## 七、已知風險與坑(建置時逐條對照)

- 履約章(CH4)供給薄:配額已壓到 2/5,留空+note 是預期結果
- `figures` 欄位是 fork 專有:**upstream `git pull` 後要重跑測試**確認 render.js 沒被覆蓋
- Lucide 圖示名要 `make icons` 驗證(brandIcon 用 trending-up,未在前課用過)
- 中文供給集中在基礎/CC/LEAPS,價差與履約偏英文——不硬湊中文
