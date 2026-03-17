# A2A Scrum Meeting 情境使用手冊

這份手冊是給「8 位 A2A 角色一起模擬公司工程會議，最後產出 3 張 scrum 工單」這個情境使用的。

如果你只想先跑起來，最短版本如下：

```bash
cp .env.example .env
# 編輯 .env，填入 DEBATE_* 或 OPENAI_* 相容設定

uv sync
bash run_scrum_meeting_demo.sh .
```

---

## 1. 這個情境在做什麼

這個 demo 會模擬一場跨職能工程會議，讓多個 A2A agent 一起審查一個程式專案，討論：

- 程式架構哪裡需要調整
- 程式品質和測試品質哪裡有風險
- 使用者體驗是否有明顯問題
- 上線、維運、安全面是否有隱藏成本
- 哪些改善項目最適合放進下一個 sprint

最後會固定產出：

- 一段完整的多角色會議過程
- 每個角色的結論
- 剛好 3 張 scrum 工單

每張工單都會包含：

- `title`
- `priority`
- `estimate`
- `owner_role`
- `supporting_roles`
- `problem`
- `description`
- `acceptance_criteria`（固定 3 條）
- `definition_of_done`

---

## 2. 會議中的 8 個角色

這個情境目前預設有 8 位角色：

1. `Senior Architect`
2. `Product Manager`
3. `QA Lead`
4. `Senior Developer`
5. `User Representative`
6. `DevOps Engineer`
7. `Security Engineer`
8. `Scrum Master`

各角色重點如下：

- `Senior Architect`
  看模組邊界、耦合、維護性、技術債。
- `Product Manager`
  看使用者價值、優先順序、scope 與 sprint 內可交付性。
- `QA Lead`
  看測試策略、驗收標準、回歸風險與可驗證性。
- `Senior Developer`
  看實作可行性、重構成本、程式健康度與落地方式。
- `User Representative`
  看真實使用者流程、易用性、錯誤訊息與感受。
- `DevOps Engineer`
  看 CI/CD、部署流程、觀測性、環境一致性與維運風險。
- `Security Engineer`
  看攻擊面、權限、依賴風險、敏感資訊與安全預設。
- `Scrum Master`
  看依賴、阻塞、切工是否合理、工作是否能在 sprint 內完成。

---

## 3. 支援哪些輸入

你可以讓這場會議審查兩種來源：

### 3.1 本機專案

例如：

```bash
bash run_scrum_meeting_demo.sh .
bash run_scrum_meeting_demo.sh /path/to/repo
```

適合情境：

- 你目前正在開發的專案
- 本機尚未 push 的程式碼
- 公司內網專案，不能公開給外部看

### 3.2 GitHub repository URL

例如：

```bash
bash run_scrum_meeting_demo.sh https://github.com/owner/repo
```

也支援帶 branch/path 的 GitHub URL，例如：

```bash
bash run_scrum_meeting_demo.sh https://github.com/owner/repo/tree/main/src
```

適合情境：

- 想快速分析公開 repo
- 想把某個 GitHub 專案拿來當會議題材
- 想比較不同 repo 的改善方向

---

## 4. 執行前準備

### 4.1 Python

需要：

- `Python 3.12+`

### 4.2 套件安裝

建議用 `uv`：

```bash
uv sync
```

或用 `pip`：

```bash
pip install -e .
```

### 4.3 LLM 設定

這個情境用的是 `debate_demo/model_config.py` 那套設定，所以需要在 `.env` 設以下其中一組：

#### 方案 A：公司內部 OpenAI-compatible gateway

```env
DEBATE_BASE_URL=https://your-llm-gateway.example.com/v1
DEBATE_MODEL_NAME=your-model-name
DEBATE_API_TOKEN=your_api_token_here
```

#### 方案 B：標準 OpenAI-compatible 設定

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
OPENAI_API_KEY=your_openai_api_key_here
```

### 4.4 可選：GitHub Token

如果你要分析 GitHub repo，建議加上：

```env
GITHUB_TOKEN=your_github_token
```

用途：

- 避免 GitHub API rate limit 太快打滿
- 讓讀取 GitHub tree / raw file 比較穩

---

## 5. 第一次啟動

### 5.1 複製環境檔

```bash
cp .env.example .env
```

### 5.2 編輯 `.env`

至少補上：

- `DEBATE_BASE_URL`
- `DEBATE_MODEL_NAME`
- `DEBATE_API_TOKEN`

或補上：

- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OPENAI_API_KEY`

### 5.3 執行目前專案的會議

```bash
bash run_scrum_meeting_demo.sh .
```

---

## 6. 常用指令

### 6.1 分析目前專案

```bash
bash run_scrum_meeting_demo.sh .
```

### 6.2 分析其他本機專案

```bash
bash run_scrum_meeting_demo.sh /Users/yourname/work/my-project
```

### 6.3 分析 GitHub repo

```bash
bash run_scrum_meeting_demo.sh https://github.com/owner/repo
```

### 6.4 增加討論輪數

每個角色預設是 `2` 輪，所以 8 個角色總共會有 `16` 次輪流發言。

```bash
bash run_scrum_meeting_demo.sh --rounds 3 .
```

這時總發言數會變成：

- `3 x 8 = 24` 輪

### 6.5 自訂會議目標

```bash
bash run_scrum_meeting_demo.sh \
  --rounds 3 \
  --objective "請聚焦在可維護性、測試品質與部署風險，整理出最適合下個 sprint 的三張工單" \
  .
```

---

## 7. 執行流程會發生什麼

執行 `bash run_scrum_meeting_demo.sh .` 後，流程大致如下：

1. 啟動 8 個 A2A agent server
2. 每個 agent 會在自己的 port 提供 `/.well-known/agent.json`
3. runner 會先掃描目標 repo，整理出摘要、tree preview、代表檔案片段
4. runner 把這些上下文提供給每個角色
5. 8 個角色開始輪流發言
6. 多輪討論結束後，每位角色各自給出結論
7. 最後由 `Product Manager` 把內容收斂成 3 張 scrum 工單

---

## 8. 角色與 port 對照

| 角色 | Module | Port |
|---|---|---|
| Senior Architect | `scrum_meeting_demo.senior_architect_agent` | `10010` |
| Product Manager | `scrum_meeting_demo.product_manager_agent` | `10011` |
| QA Lead | `scrum_meeting_demo.qa_lead_agent` | `10012` |
| Senior Developer | `scrum_meeting_demo.senior_developer_agent` | `10013` |
| User Representative | `scrum_meeting_demo.user_representative_agent` | `10014` |
| DevOps Engineer | `scrum_meeting_demo.devops_agent` | `10015` |
| Security Engineer | `scrum_meeting_demo.security_agent` | `10016` |
| Scrum Master | `scrum_meeting_demo.scrum_master_agent` | `10017` |

---

## 9. 輸出怎麼看

### 9.1 開場資訊

一開始你會看到：

- target 是哪個 repo/path
- objective 是什麼
- repository context 摘要
- 目前有哪些參與角色

### 9.2 Meeting Rounds

這段是會議過程，每一輪會顯示：

- 角色名稱
- 角色身份
- 第幾輪 / 總輪數
- 本輪發言內容

### 9.3 Final Positions

這段是每個角色在討論結束後的總結。

用途：

- 快速看每個職能最在意什麼
- 檢查是否有某些風險被忽略
- 確認 backlog 是否真的反映多方觀點

### 9.4 Scrum Backlog

最後固定會有：

- `Sprint Goal`
- `SCRUM-1`
- `SCRUM-2`
- `SCRUM-3`

每張工單建議你重點看：

- `Owner`
  主要負責角色是誰
- `Support`
  需要哪些角色一起配合
- `Problem`
  這張工單真正要解的是什麼
- `Acceptance Criteria`
  驗收條件是否具體、可測
- `Definition of Done`
  完成標準是否清楚

---

## 10. 可調參數

### `--rounds`

每個角色發言幾輪。

範例：

```bash
--rounds 3
```

效果：

- 輪數越高，討論越深入
- Token 成本也會更高
- 執行時間也會更久

### `--objective`

指定這次會議要聚焦什麼。

範例：

```bash
--objective "請聚焦在測試策略、部署風險與安全性"
```

適合拿來：

- 引導會議更偏技術債
- 引導會議更偏品質
- 引導會議更偏營運風險
- 引導會議更偏使用者體驗

---

## 11. Repo context 是怎麼抓的

這個情境不會把整個 repo 全部丟給模型，而是先整理上下文。

目前會做的事情包括：

- 掃描文字檔
- 排除 `.git`、`node_modules`、`__pycache__` 等資料夾
- 優先抽取像 `README.md`、`pyproject.toml`、`package.json`、程式主檔
- 生成 repository tree preview
- 擷取代表檔案片段

這樣做的好處是：

- 成本比較可控
- 討論會比較聚焦
- 不容易因為 repo 太大而把 prompt 撐爆

---

## 12. 建議使用方式

### 12.1 分析自己的專案

最實用的方式是直接在 repo 根目錄執行：

```bash
bash run_scrum_meeting_demo.sh .
```

適合拿來：

- sprint planning 前暖身
- code freeze 前做一次健康檢查
- legacy code 改造前先盤點

### 12.2 分析外部 GitHub repo

適合拿來：

- 當讀書會題材
- 當團隊內部練習題
- 拿別人的設計做反向檢討

### 12.3 調整 objective

如果不想讓討論太發散，建議一定要加 `--objective`。

例如：

```bash
bash run_scrum_meeting_demo.sh \
  --objective "請只聚焦在可維護性、測試缺口與安全風險，並整理成下個 sprint 的三張工單" \
  .
```

---

## 13. 常見問題

### Q1. 為什麼啟動時說 API token/key is not set？

表示 `.env` 沒有正確設定以下其中一組：

- `DEBATE_BASE_URL` + `DEBATE_MODEL_NAME` + `DEBATE_API_TOKEN`
- `OPENAI_BASE_URL` + `OPENAI_MODEL` + `OPENAI_API_KEY`

### Q2. 為什麼 agent on port xxxx failed to start？

常見原因：

- 依賴沒有安裝完整
- LLM 設定不正確
- port 被其他程式佔用
- agent import 時就失敗

建議先單獨跑某個角色確認：

```bash
python -m scrum_meeting_demo.senior_architect_agent
```

### Q3. 為什麼 GitHub repo 讀不到？

常見原因：

- 網路受限
- GitHub API rate limit
- repo URL 錯誤
- private repo 但沒有 `GITHUB_TOKEN`

### Q4. 為什麼最後不是 3 張工單？

理論上 runner 會要求 PM agent 固定輸出 3 張；如果模型一開始格式錯，runner 也會再要求它修正一次。

如果還是失敗，通常是：

- 模型沒有穩定遵守 JSON schema
- prompt 太長
- repo context 太大，導致後段輸出不穩

可以先嘗試：

- 降低 `--rounds`
- 縮小 repo
- 調整 `--objective` 讓討論更聚焦

### Q5. 為什麼跑起來很慢？

因為這不是單 agent 問答，而是：

- 8 個角色
- 多輪對話
- 最後還要整理 backlog

如果想先快速試：

```bash
bash run_scrum_meeting_demo.sh --rounds 1 .
```

---

## 14. 建議的操作節奏

如果你是第一次用，建議這樣跑：

1. 先對小 repo 跑 `--rounds 1`
2. 確認環境變數、依賴、輸出格式都正常
3. 再把 `--rounds` 提高到 `2` 或 `3`
4. 最後再拿真正的專案或 GitHub repo 跑完整討論

---

## 15. 進階用法

### 15.1 手動啟動所有角色

你也可以不用 script，自己逐個啟動：

```bash
python -m scrum_meeting_demo.senior_architect_agent
python -m scrum_meeting_demo.product_manager_agent
python -m scrum_meeting_demo.qa_lead_agent
python -m scrum_meeting_demo.senior_developer_agent
python -m scrum_meeting_demo.user_representative_agent
python -m scrum_meeting_demo.devops_agent
python -m scrum_meeting_demo.security_agent
python -m scrum_meeting_demo.scrum_master_agent
python -m scrum_meeting_demo .
```

### 15.2 只改會議目標，不改程式

如果你想讓它更偏某個方向，最簡單就是改 `--objective`，不一定要改程式碼。

### 15.3 之後串接 ADO

目前這版是先產出 backlog，還沒有自動建立 ADO 工單。

但你之後可以很自然地再往下接：

- 將 3 張工單轉成 Azure DevOps work items
- 將 backlog 再分派給後續 implementation agents
- 將 scrum meeting 產物存成檔案或報表

---

## 16. 相關檔案

如果你要看這個情境的主要程式，先看這幾個檔案就夠了：

- [run_scrum_meeting_demo.sh](/Users/isosoman/.codex/worktrees/9e04/A2Ademo/run_scrum_meeting_demo.sh)
- [scrum_meeting_demo/meeting_runner.py](/Users/isosoman/.codex/worktrees/9e04/A2Ademo/scrum_meeting_demo/meeting_runner.py)
- [scrum_meeting_demo/repo_context.py](/Users/isosoman/.codex/worktrees/9e04/A2Ademo/scrum_meeting_demo/repo_context.py)
- [scrum_meeting_demo/roles.py](/Users/isosoman/.codex/worktrees/9e04/A2Ademo/scrum_meeting_demo/roles.py)

---

## 17. 建議下一步

如果你要把這個情境真正用在團隊流程裡，下一步最值得做的通常是：

1. 把 backlog 自動寫進 Azure DevOps
2. 把會議輸出存成 markdown 或 JSON 檔
3. 增加「會後執行」流程，讓工單直接交給實作 agents
