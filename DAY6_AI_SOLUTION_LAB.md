# Day 6｜AI 解決方案實戰日

本日採「四站輪轉體驗＋選擇一案完整實作」，不是把 CNN、RNN、GAN、RL 各講一次後照抄程式。

## 學生入口

- 本機入口：`docs/index.html`
- 發布 GitHub Pages 後的預計入口：`https://johnnychao.github.io/python-machine-learning-2026-student/`
- 課前健檢：`notebooks/day6_ai_solution_lab/00_preflight.ipynb`

> 目前若尚未發布到 GitHub，請從入口頁下載 `.ipynb`，再到 Colab 使用「檔案 → 上傳 Notebook」。

## 六小時動線

| 時間 | 行動 | 證據 |
| --- | --- | --- |
| 00:00–00:15 | 任務簡報、分組、角色 | 組別與角色 |
| 00:15–02:15 | CNN / RNN / GAN / RL 四站輪轉 | 四份迷你實驗卡 |
| 02:15–02:45 | 選一案、Problem Canvas、Pain Map | 專案範圍 |
| 02:45–04:00 | Baseline 與 Candidate | 指標比較 |
| 04:00–04:40 | Gradio 課堂 Demo | 可操作介面 |
| 04:40–05:15 | 紅隊測試與錯誤分類 | 測試報告 |
| 05:15–05:55 | 4–5 分鐘成果發表 | 現場 Demo |
| 05:55–06:00 | Exit Ticket | 一項學習、限制、改進 |

## 四站 Notebook

1. `01_cnn_pet_router.ipynb`：改人工覆核門檻，記錄 F1、Coverage、人工覆核率。
2. `02_rnn_disaster_triage.ipynb`：改分類門檻，記錄 Recall、F1、False Negative。
3. `03_gan_monet_studio.ipynb`：改風格混合強度，記錄內容保留、風格感與破圖。
4. `04_rl_connectx_agent.ipynb`：開關防守規則，記錄勝率、非法行動率與決策時間。

## 交付原則

- 至少比較一個 Baseline 與一個 Candidate。
- 必須公開一個失敗案例。
- 模型指標以固定留出資料評估；Kaggle test 若無標籤，不可當本地驗證集。
- `demo.launch(share=True)` 只是 runtime 存活期間的暫時連結，不是正式公開部署。
- 不把 Kaggle Token、學生資料、醫療資料、客戶資料放入 Notebook 或 Gradio。
