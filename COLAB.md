# Colab 使用說明

本課程採 Colab-ready notebooks 作為上課主流程。官方原始 notebook 需要相對路徑圖片與資料檔，因此本教材包在第一格加入 setup cell，會自動 clone：

```text
https://github.com/rasbt/python-machine-learning-book-3rd-edition.git
```

注意：
- Colab session 重啟後需重新執行 setup cell。
- 深度學習章節可能需要 GPU runtime。
- Ch17 GAN 與 Ch18 RL 建議使用 quick mode 或由講師示範。
- 若套件 API 更新造成錯誤，請先查看 `reports/notebook_compatibility_report.json` 或回報錯誤訊息。

## 課前 smoke test

請先在 Colab 開啟：

```text
https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/colab_smoke/00_colab_smoke_all_chapters.ipynb
```

這份 notebook 會快速檢查目前 Colab runtime 的核心套件、官方 repo 來源、傳統 ML、TensorFlow、Gym API wrapper。通過後，再進入各章 Colab-ready notebook。
