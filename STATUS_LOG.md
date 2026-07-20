# Status Log

## 2026-07-20｜學生公開課程網站整合

狀態：**本機驗收通過，等待推送與建立 PR 的明確同意。**

已完成：

- 建立首頁、五個每日頁、綜合實作頁與課後延伸頁。
- 以 `course-catalog.json` 管理 18 章、18 份 PDF 與 26 個 Colab 入口，並同步產生 `COURSE_MAP.md`。
- 建立 18 章公開學生 Markdown 與 18 份可抽取文字的 PDF，共 76 頁。
- 完成學生語氣、臺灣用語、來源聲明、禁止內容與 Markdown 格式清理。
- 保留四幕電影故事、恩恩老師插圖與 Snow Globe CC0 配樂；一般課程頁維持安靜。
- 通過入口靜態 39/39、入口瀏覽器 150/150、綜合實作靜態 66/66、綜合實作瀏覽器 46/46。
- 完成 76/76 PDF 全頁視覺檢查。
- 即時確認學生版為 Public、教師版為 Private；教師版工作樹仍乾淨且版本未變。

待完成：

- GitHub Pages 設定 API 暫時回覆 HTTP 503，發布前需重新確認來源為 `main` 的 `docs/`。
- 尚未 push、建立 PR、合併或發布。

詳細證據見 `reports/student_course_portal_acceptance.md`。
