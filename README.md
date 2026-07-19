# Python Machine Learning 2026 - 學生實作用 repo

本 repo 是「數據分析暨機器學習應用班 2026」中 *Python Machine Learning, 3rd Ed.* 教材包的學生上課與自主操作用入口。

## Google Colab 主流程

1. 開啟 `practice/CHAPTER_PRACTICE_GUIDE.md`。
2. 找到當天章節，點 Colab-ready notebook 連結。
3. 進入 Colab 後先執行第一個 setup cell。
4. 依序執行 notebook，遇到大型資料或深度學習章節時，依講師指示使用 quick mode。
5. 保存自己的 Colab 副本，作為複習紀錄。

課程後段的 AI 綜合演練請由 [`AI_SOLUTION_PRACTICUM.md`](AI_SOLUTION_PRACTICUM.md) 進入。四個情境都在 Colab 直接載入公開或課程自製素材；Kaggle 只列為題目出處，學員不需要 Kaggle 帳號或 API Token。

## Repo 定位

- 提供 Colab-ready notebooks、環境檢查、練習模板與課程地圖。
- 不收錄原書 PDF、全文抽取、講師私用輸出快取或學生資料。
- 官方程式碼來源與 MIT 授權資訊見 `THIRD_PARTY_NOTICES.md`。

## 課前 Colab smoke test

正式上課前，建議先開啟：

https://colab.research.google.com/github/johnnychao/python-machine-learning-2026-student/blob/main/notebooks/colab_smoke/00_colab_smoke_all_chapters.ipynb

確認目前 Colab runtime、套件版本、官方 repo clone 與各章代表性輕量流程可運作。

## 本機快速開始

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1
```

若只使用 Google Colab，不需要先在本機安裝環境。
