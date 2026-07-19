# AI 解決方案綜合實作

這是一組以 Google Colab 為唯一實作環境的綜合演練。學員從網頁進入情境，再開啟 Notebook，依序完成「理解問題、執行基準方案、修改一個關鍵設定、比較結果、記錄限制」。

Kaggle 連結只用來說明專案題目的出處。學生不需要 Kaggle 帳號、API Token 或資料下載權限；實作資料會由 Colab 直接從公開教材來源、固定版本檔案或本課程自製素材載入。

## 建議流程

1. 先開啟課前健檢，確認 Colab runtime 與主要套件可用。
2. 依序體驗 CNN、RNN、影像風格轉換與 Connect X 四個情境。
3. 每個情境只修改一個指定變因，保存修改前後的指標或畫面。
4. 選一個最有感的情境，完成學習單與方案畫布。

## Colab 入口

- [課前健檢](https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/ai_solution_practicum/00_colab_ready.ipynb)
- [CNN：動物之家照片智慧分流](https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/ai_solution_practicum/01_cnn_pet_story.ipynb)
- [RNN：災害應變訊息智慧分流](https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/ai_solution_practicum/02_rnn_message_story.ipynb)
- [影像風格轉換：故事場景概念工作室](https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/ai_solution_practicum/03_style_transfer_story.ipynb)
- [強化學習：Connect X 智慧對手](https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/ai_solution_practicum/04_rl_strategy_story.ipynb)

## 四種免登入資料方案

| 情境 | Kaggle 專案脈絡 | Colab 實際載入來源 |
|---|---|---|
| CNN | Dogs vs. Cats | Keras 直接下載 CIFAR-10，再於 Colab 篩出 cat／dog 兩類 |
| RNN | Natural Language Processing with Disaster Tweets | Hugging Face 固定 commit 的 7,613 筆標記 CSV |
| 影像風格轉換 | I’m Something of a Painter Myself | 本課程以 ImageGen 製作的內容圖與風格參考圖 |
| Connect X | Kaggle Connect X | Notebook 內建立純 Python 棋盤與對戰資料，不下載外部資料 |

完整網址、版本、授權備註與認證政策記錄在 [`data/ai_solution_practicum/datasets.json`](data/ai_solution_practicum/datasets.json)。

## 學習成果

完成體驗後，學員應能：

- 用一句話說明資料、模型輸出與使用情境。
- 解釋修改的變因如何影響指標、錯誤或使用者決策。
- 區分模型展示、可用原型與正式部署。
- 指出至少一項資料限制、模型限制與人工覆核需求。

## 教學邊界

- 所有模型輸出都只是課堂決策輔助，不代表真實世界結論。
- 影像風格轉換採快速代理模型，不宣稱在課堂中重新訓練 CycleGAN。
- Connect X 主線比較規則式策略，不宣稱已完成 DQN 訓練。
- 學員不需啟動 Gradio、公開暫時網址或部署服務；結果直接顯示在 Colab cell。

## 教材維護驗證

在 repo 根目錄執行：

```powershell
python scripts\validate_ai_solution_practicum.py
```

這項靜態驗證會拒絕 Kaggle runtime、登入憑證與 Gradio 依賴。正式授課前仍須在全新的 Colab runtime 逐本執行。

最近一次匿名來源連線檢查記錄於 [`reports/ai_solution_practicum_source_probe.json`](reports/ai_solution_practicum_source_probe.json)。
