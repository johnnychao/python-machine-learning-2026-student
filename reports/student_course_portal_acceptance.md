# 學生公開課程網站驗收紀錄

- 驗收日期：2026-07-20
- 工作分支：`agent/student-course-portal`
- 基準版本：`07937a7deb66367dea443efeb621fa9bab47e0f2`
- 本機狀態：通過
- 發布狀態：尚未推送、建立 PR、合併或發布

## 驗收結果

| 驗收項目 | 結果 | 證據 |
| --- | --- | --- |
| 首頁、五個每日入口、綜合實作、課後延伸 | 通過 | 靜態驗證 39/39；瀏覽器驗證 150/150 |
| Ch01–Ch18 章節對應 | 通過 | `docs/assets/course-catalog.json` |
| 18 份學生 Markdown 與 18 份 PDF | 通過 | `reports/student_handout_validation.json` |
| PDF 標頭、文字抽取、非空與禁止內容掃描 | 通過 | 18/18；共 76 頁 |
| PDF 全頁視覺檢查 | 通過 | 76/76；未見裁切、重疊、黑方塊或缺字 |
| 26 個公開 Colab 入口 | 通過 | Ch01–12 各一份；Ch13、Ch14 各三份；Ch15 三份；Ch16、Ch17 各兩份；Ch18 一份 |
| 綜合實作四幕故事、插圖與音訊 | 通過 | 靜態驗證 66/66；瀏覽器回歸 46/46 |
| 桌機、360px 手機、鍵盤與縮減動態 | 通過 | `scripts/qa_course_portal.cjs` 與 `scripts/qa_storybook_page.cjs` |
| 公開內容邊界與建置輸出限制 | 通過 | 55 個提交文字檔掃描；建置目標 containment guard 通過 |
| 學生／教師 repository 可見性 | 通過 | 2026-07-20 唯讀查詢：學生版 Public、教師版 Private |
| 教師 repository 不受影響 | 通過 | 工作樹乾淨，且版本與實作前基線相同 |
| Pages 發布來源即時複核 | 待發布前重試 | GitHub Pages 設定 API 連續回覆 HTTP 503，未把此項誤列為通過 |

## 可重現命令

```powershell
python scripts\build_student_course_portal.py --check
python scripts\validate_student_course_portal.py
python scripts\validate_ai_solution_practicum.py
```

PDF 重建需先安裝 `scripts/build_student_handouts.requirements.txt` 所列套件，再執行：

```powershell
python scripts\build_student_handouts.py
```

## 發布閘門

目前只完成本機實作與驗收。下一步必須先取得明確同意，才可推送此 student 分支並建立 PR；合併與 GitHub Pages 發布仍需另行確認。發布前須再次確認 Pages 來源為 `main` 的 `docs/`，並再次檢查教師 repository 工作樹維持乾淨。
