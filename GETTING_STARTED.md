# 快速開始

## Colab

學生請先從公開課程網站進入當天頁面：

https://johnnychao.github.io/python-machine-learning-2026-student/

每章頁面會同時提供學生版 PDF 講義與 Colab-ready notebook。Notebook 的第一格會自動 clone 官方 repo、切換章節目錄並檢查套件。

要進行 CNN、RNN、影像風格轉換與強化學習的綜合演練，請進入網站的「五日課程壓軸」，或閱讀 [`AI_SOLUTION_PRACTICUM.md`](AI_SOLUTION_PRACTICUM.md)。全程只需 Google Colab，不需要 Kaggle 帳號或憑證。

## 本機

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1
.\.venv\Scripts\activate
jupyter lab
```

先開：

```text
notebooks/00_environment_check.ipynb
notebooks/01_practice_template.ipynb
```
