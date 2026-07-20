# Colab 使用說明

本課程採公開網站作為學生入口，並以 Colab-ready notebooks 作為實作主流程：

https://johnnychao.github.io/python-machine-learning-2026-student/

官方原始 notebook 需要相對路徑圖片與資料檔，因此本教材包在第一格加入 setup cell，會自動 clone：

```text
https://github.com/rasbt/python-machine-learning-book-3rd-edition.git
```

AI 解決方案綜合演練請從 [`AI_SOLUTION_PRACTICUM.md`](AI_SOLUTION_PRACTICUM.md) 開始。該組 Notebook 的資料會由 Colab 直接載入，Kaggle 連結僅供查閱題目出處，不要求學生登入 Kaggle。

注意：
- Colab session 重啟後需重新執行 setup cell。
- 深度學習章節可能需要 GPU runtime。
- Ch17 GAN 與 Ch18 RL 建議依頁面提示使用快速模式。
- 若套件 API 更新造成錯誤，請先查看 `reports/notebook_compatibility_report.json` 或回報錯誤訊息。

## 課前 smoke test

請先在 Colab 開啟：

```text
https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/colab_smoke/00_colab_smoke_all_chapters.ipynb
```

這份 notebook 會快速檢查目前 Colab runtime 的核心套件、官方 repo 來源、傳統 ML、TensorFlow、Gym API wrapper。通過後，再進入各章 Colab-ready notebook。
