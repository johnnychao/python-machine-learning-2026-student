# AI 解決方案綜合實作｜ImageGen 資產紀錄

- 產生日期：2026-07-19
- 產生工具：OpenAI ImageGen（Codex `image_gen`）
- 角色參考：使用者提供的 `恩恩老師01.jpg`
- 共通限制：不產生文字、Logo、浮水印或平台介面；角色固定為黑短髮、黑框眼鏡、丹寧外套、白色紫菇上衣。
- 品牌色：`#2C3E50`、`#5D6D7E`、`#F39C12`、`#EAEDEF`

> 原始 PNG 保存於 `data/ai_solution_practicum/assets/`；網頁使用的 WebP 由 `scripts/optimize_storybook_assets.py` 產生。品牌人物與既有貼圖的公開使用權仍應由素材所有人於發布前確認。

## 1. 故事封面

- 網頁檔：`cover-ai-story-lab.webp`
- 原始檔 SHA-256：`66fa71de37f5887aee77f2911d8077b9fc2b86bda29491f09261aad15ce7e30f`
- 提示詞：

```text
Create a polished wide storybook cover illustration for a Taiwanese data-science classroom website, using the supplied character sheet as the exact visual reference for the recurring teacher character. Teacher Enen sits beside an oversized open picture book on a warm classroom desk. From the pages rise four interconnected story worlds: a friendly cat-and-dog adoption shelter, a safe message-sorting desk with colored trays, a cozy impressionist art studio, and a Connect-Four-style strategy board. The teacher warmly gestures for students to enter the stories. Patient, curious, reassuring, hands-on learning; premium hand-painted gouache and colored-pencil texture, layered cut-paper depth, restrained details, adult-friendly storybook quality. Brand palette navy #2C3E50, slate #5D6D7E, orange #F39C12, pale paper #EAEDEF. 16:9 landscape, teacher and book right of center, generous negative space on the left. No words, letters, numbers, logos, watermark, UI, duplicate teacher, or incorrect hands.
```

## 2. CNN｜毛孩照片分流

- 網頁檔：`story-cnn-pet-shelter.webp`
- 原始檔 SHA-256：`ca31b390a72754c18d2c7f6372c6f74f25833bba71f89cd3698e07e2b469367b`
- 提示詞：

```text
Create a 4:3 adult-friendly Taiwanese storybook illustration. At a welcoming animal adoption center, Teacher Enen helps two adult students organize pet photos into cat and dog groups. Show unlabeled photo cards, two trays indicated only by pictograms, and one ambiguous pet photo that makes the group pause and compare. Suggest image classification, baseline comparison, and checking mistakes without code or screen text. Premium gouache and colored-pencil texture, subtle cut-paper layers and paper grain; navy #2C3E50, slate #5D6D7E, orange #F39C12, pale paper #EAEDEF, muted green. Teacher on the right, pets on the left, negative space upper left. No words, logos, watermark, UI, distress, duplicate teacher, or incorrect hands.
```

## 3. RNN｜訊息優先確認

- 網頁檔：`story-rnn-message-triage.webp`
- 原始檔 SHA-256：`fd568da20167a53922643e990f36b06255015bc6f29bc8bfeb1a22964505eb03`
- 提示詞：

```text
Create a 4:3 adult-friendly Taiwanese storybook illustration. In a calm community information center during heavy rain, Teacher Enen helps two adult students sort many short message cards into three colored trays: urgent to verify, needs context, and routine. Use only abstract line marks and safe icons, no readable text. Show rain and a distant city but no victims, destruction, gore, panic, or sensational disaster. Teacher compares two similar cards, suggesting language classification, uncertainty, and human review. Premium gouache and colored-pencil storybook with paper grain; navy, slate, orange, pale paper, muted teal. No words, logos, watermark, UI, duplicate teacher, or incorrect hands.
```

## 4. 風格轉換｜旅行照片工作室

- 網頁檔：`story-gan-art-studio.webp`
- 原始檔 SHA-256：`926c9ae8b4ea9d6622690cc630dbd3129f014b0c4e8f27bfa35b24c1b508c83e`
- 提示詞：

```text
Create a 4:3 adult-friendly Taiwanese storybook illustration. In a warm art-and-data studio, Teacher Enen and two adult students compare one Taiwanese coastal travel scene in three visual stages: clean reference, basic color-transfer experiment, and expressive impressionist-style result. Show the three images side by side, paint swatches, a laptop seen from the back, a magnifying glass, and a student writing observations. Suggest style transfer, baseline versus candidate, and careful comparison without copying a recognizable artwork or artist. Premium gouache and colored-pencil storybook, cut-paper depth and paper grain; brand navy, slate, orange, pale paper, lavender and muted teal. No words, logos, watermark, readable UI, duplicate teacher, or incorrect hands.
```

## 5. RL｜四連棋策略

- 網頁檔：`story-rl-strategy-board.webp`
- 原始檔 SHA-256：`5a7bd41e016f4236e3b4900cba16667db8f8810f25f46f35967dd996c6b50079`
- 提示詞：

```text
Create a 4:3 adult-friendly Taiwanese storybook illustration. Teacher Enen and two adult students study a generic upright four-in-a-row board with navy and orange discs. One student is about to place a disc while the teacher compares two next moves with removable arrow tokens. Show a paper trail of previous board states and abstract win/loss tally shapes. Communicate reinforcement learning, trying strategies, comparing outcomes, and learning from repeated games; no gambling. Premium gouache and colored-pencil storybook, subtle cut-paper layers and paper grain; navy, slate, orange, pale paper, muted teal and lavender. No words, readable numbers, product branding, logos, watermark, UI, duplicate teacher, or incorrect hands.
```

## 6. 風格轉換內容圖｜海岸與單車

- Notebook 原始檔：`data/ai_solution_practicum/assets/style-content-coast.png`
- SHA-256：`ce9c4616b8ce872e340a1942b0d407294986d715490accb88a21b8f68a89ba35`
- 提示詞：

```text
Create an original content image for a neural style-transfer classroom exercise: a peaceful east-coast Taiwan-inspired seaside landscape viewed from a hillside path, with layered green mountains, a small harbor, rocky shoreline, bright blue water, summer clouds, and one orange bicycle beside a wooden railing. Do not depict a specific recognizable photograph or landmark. Use a polished editorial travel illustration with realistic depth, natural colors, restrained gouache and colored-pencil texture, and clear large shapes. 4:3 landscape. No people, words, logos, watermark, frame, or UI.
```

## 7. 風格轉換參考圖｜海風色彩

- Notebook 原始檔：`data/ai_solution_practicum/assets/style-reference-sea-wind.png`
- SHA-256：`79509f7a3bc5d15c38cce18f1cdf91e1e4f736200edc5c5b8c9a5b0a4bfa7574`
- 提示詞：

```text
Create an original abstract style-reference image for a neural style-transfer classroom exercise. Do not imitate or name any specific artist and do not reproduce an existing artwork. Make an abstract dream of sea wind at sunset using layered gouache strokes, broken color patches, curved wave rhythms, lavender cloud shapes, and orange-gold highlights. No recognizable people, buildings, objects, landscape, or text. Palette: deep navy #2C3E50, slate blue #5D6D7E, orange #F39C12, lavender, muted teal, pale paper #EAEDEF. Square, edge-to-edge, visible paper grain, balanced texture. No signature, logo, or watermark.
```
