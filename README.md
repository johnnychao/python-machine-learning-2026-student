# Python Machine Learning 2026 - 學生實作用 repo

本 repo 是「數據分析暨機器學習應用班 2026」的公開學生入口，提供五日課程地圖、學生版講義與 Colab-ready notebooks。

## 學生公開網站

https://johnnychao.github.io/python-machine-learning-2026-student/

- Day 1–5：Ch01–Ch15，每章同時提供學生版 PDF 與 Colab。
- 五日課程壓軸：四個 AI 解決方案故事情境，完成跨章節綜合實作。
- 課後延伸：Ch16–Ch18，供學生依興趣自主探索。

## Google Colab 主流程

1. 開啟學生公開網站，進入當天 Day 頁面。
2. 先閱讀學生版講義，再點 Colab-ready notebook 連結。
3. 進入 Colab 後先執行第一個 setup cell。
4. 依序執行 notebook；遇到大型資料或深度學習章節時，依頁面提示使用快速模式。
5. 保存自己的 Colab 副本，作為複習紀錄。

課程後段的 AI 綜合演練請由網站的「五日課程壓軸」或 [`AI_SOLUTION_PRACTICUM.md`](AI_SOLUTION_PRACTICUM.md) 進入。四個情境都在 Colab 直接載入公開或課程自製素材；Kaggle 只列為題目出處，學生不需要 Kaggle 帳號或 API Token。

## Repo 定位

- 提供公開學生版講義、Colab-ready notebooks、環境檢查、練習模板與課程地圖。
- 不收錄原書 PDF、全文抽取、教師備課內容、內部答案或學生資料。
- 公開邊界與發布規則見 [`PUBLIC_CONTENT_POLICY.md`](PUBLIC_CONTENT_POLICY.md)。
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

## 教材維護與驗收

`docs/assets/course-catalog.json` 是網站與課程地圖的單一資料來源。修改後依序執行：

```powershell
python .\scripts\build_student_course_portal.py
python .\scripts\build_student_course_portal.py --check
python .\scripts\validate_student_course_portal.py
```

若要重建學生講義 PDF，先安裝 `scripts/build_student_handouts.requirements.txt` 所列的免費套件，再執行 `scripts/build_student_handouts.py`。所有建置腳本只允許寫入本 student repo。
