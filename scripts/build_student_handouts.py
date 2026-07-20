#!/usr/bin/env python3
"""Import, render, and validate the 18 public student handouts.

Normal rebuild (uses the tracked student Markdown):
    python scripts/build_student_handouts.py

One-time/controlled refresh from a directory containing CH*.md source files:
    python scripts/build_student_handouts.py --import-source PATH

The script has a deliberately fixed output surface. It will only write the
18 canonical Markdown/PDF files and the validation report inside this repo.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

try:
    from pypdf import PdfReader
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:  # pragma: no cover - startup guidance
    raise SystemExit(
        "缺少 PDF 建置套件。請執行：\n"
        "python -m pip install -r scripts/build_student_handouts.requirements.txt"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
STUDENT_SOURCE_DIR = REPO_ROOT / "handouts" / "student"
PDF_OUTPUT_DIR = REPO_ROOT / "docs" / "handouts"
REPORT_PATH = REPO_ROOT / "reports" / "student_handout_validation.json"

CHAPTER_TITLES = {
    1: "從資料中學習的機器：機器學習基石與視野",
    2: "機器學習分類演算法：從感知器到梯度下降",
    3: "scikit-learn 分類器實務：從直覺觀念到程式應用",
    4: "資料前處理精要",
    5: "資料降維與特徵萃取實戰",
    6: "機器學習模型評估與超參數調校",
    7: "集成學習：從單一模型到團隊預測",
    8: "情緒分析與自然語言處理實戰",
    9: "機器學習模型部署：從實驗到應用程式",
    10: "迴歸分析：從理論到實作",
    11: "非監督式學習：聚類分析",
    12: "從零開始實作多層神經網路：MNIST 手寫辨識",
    13: "TensorFlow 與 Keras：從張量到深度學習",
    14: "TensorFlow 核心機制與客製化實作",
    15: "卷積神經網路：CNN 影像分類",
    16: "循環神經網路：RNN 與序列建模",
    17: "生成對抗網路：從 GAN 到 DCGAN",
    18: "強化學習：AI 的互動與試錯",
}

TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("講師授課完整講義", "學生版講義"),
    ("講師專用教學講義", "學生版講義"),
    ("講師教學講義", "學生版講義"),
    ("講師備課小幫手", "實作小幫手"),
    ("講師手冊", "學習指南"),
    ("給講師的執行建議", "實作執行建議："),
    ("講師轉場口條", "學習轉場"),
    ("講師溫馨提醒", "學習提醒"),
    ("講師提醒", "學習提醒"),
    ("講師叮嚀", "學習提醒"),
    ("講師總結", "本章總結"),
    ("講師檢核表", "實作檢查表"),
    ("講師觀點", "觀念說明"),
    ("導師小撇步", "學習小撇步"),
    ("作為資深導師，我要求各位在實作 DCGAN 時遵循以下鐵律", "實作 DCGAN 時，請遵循以下原則"),
    ("作為導師，我最常看到學生卡在以下兩點", "實作時最常卡在以下兩點"),
    ("在計算特徵值時，講師必須提醒學員", "在計算特徵值時，請特別留意"),
    ("設定具體學習目標能幫助講師追蹤認知進度。對學員而言", "設定具體學習目標能幫助你追蹤學習進度。對學習者而言"),
    ("專家級私藏絕招", "實作延伸"),
    ("內部邏輯分析", "流程邏輯分析"),
    ("參考答案（填補）", "合理填補"),
    ("錯誤排除與驗收", "錯誤排除與自我檢查"),
    ("視覺化驗收", "視覺化檢查"),
    ("教案概覽", "學習概覽"),
    ("教學設計策略", "本章學習路線"),
    ("為學員建立", "幫助你建立"),
    ("本章將協助學員", "本章會協助你"),
    ("我們將帶領學員完成", "你將循序完成"),
    ("根據本課程教材，學員應達成", "完成本章後，你可以達成"),
    ("學員常困惑", "你可能會困惑"),
    ("完成本章學習後，學員應具備", "完成本章後，你將具備"),
    ("完成本講義後，學員應具備", "完成本章後，你將具備"),
    ("完成本實戰講義後，學員應掌握", "完成本章後，你將掌握"),
    ("學員將能掌握", "你將能掌握"),
    ("過去學員可能習慣", "若你過去習慣"),
    ("引導學員", "協助你"),
    ("實作檢查表：學員常犯錯誤", "常見實作錯誤檢查表"),
    ("學員在進入本章前，應確認具備", "開始本章前，請確認你具備"),
    ("作為架構師，我們", "在實作中，我們"),
    ("**初學者警示**：學員常誤以為", "**觀念提醒**：你可能會誤以為"),
    ("本章將帶領各位跨越", "本章將從既有基礎出發，跨越"),
    ("本章節將帶領各位", "本章將帶你"),
    ("我們將帶領學生", "本章會帶你"),
    ("在教學中，使用物件導向 (OOP) 建立類 Scikit-learn API 的類別能讓學生養成標準開發習慣", "在實作中，使用物件導向 (OOP) 建立類 Scikit-learn API 的類別，能幫助你養成標準開發習慣"),
    ("若學生遇到此問題", "若你遇到此問題"),
    ("在課堂示範時將 tokenizer 替換為內建的 `str.split`", "如需縮短執行時間，可將 tokenizer 替換為內建的 `str.split`"),
    ("在等待時引導學生討論 L1 與 L2 正規化在高維文字資料中的稀疏性差異", "在等待時，比較 L1 與 L2 正規化在高維文字資料中的稀疏性差異"),
    ("**自我檢查表**：學生是否能區分", "**自我檢查表**：你是否能區分"),
    ("引導學生觀察", "請觀察"),
    ("請引導學生從", "請從"),
    ("請多引導學生觀察", "請多觀察"),
    ("請多請觀察", "請多觀察"),
    ("掌握工業框架，是從 AI 學生轉變為 AI 工程師的必經之路", "掌握框架能幫助你把模型觀念轉化為可維護的工程實作"),
    ("教學小撇步：如何回應學生的質疑", "觀念釐清：估計值如何逐步變準"),
    ("學生常問", "你可能會問"),
    ("請務必強調", "判讀時請記得"),
    ("ϕ", "phi"),
    ("φ", "phi"),
    ("ϵ", "epsilon"),
    ("ε", "epsilon"),
    ("∼", "~"),
    ("⋅", "·"),
    ("⌊", "floor("),
    ("⌋", ")"),
    ("⟨", "<"),
    ("⟩", ">"),
    ("❗", "!"),
    ("🌟", "重點："),
    ("💡", "提示："),
    ("章節定位與學習導航", "本章學習路線"),
    ("章節定位與學習導覽", "本章學習路線"),
    ("章節定位與教學導航", "本章學習路線"),
    ("章節定位與教學大綱", "本章學習路線"),
    ("章節定位與教學藍圖", "本章學習路線"),
    ("章節定位與學習目標", "本章學習路線與學習目標"),
    ("課程章節定位與學習核心", "本章學習路線與核心觀念"),
    ("課程定位與學習目標", "本章學習路線與學習目標"),
    ("本章定位與學習導航", "本章學習路線"),
    ("課程開端：章節定位與策略價值", "本章學習路線與實務價值"),
    ("章節定位與學習導量", "本章學習路線與學習目標"),
    ("章節導引：序列數據的戰略價值", "本章學習路線：序列資料的實務價值"),
    ("章節定位", "本章學習路線"),
    ("課程定位", "本章學習路線"),
    ("章節導引", "本章學習路線"),
    ("教學藍圖", "學習路線"),
    ("教學導航", "學習導航"),
    ("教學診斷", "常見錯誤"),
    ("教學大綱", "學習大綱"),
    ("教學目標", "學習目標"),
    ("課堂練習", "動手練習"),
    ("課堂總結", "本章總結"),
    ("課堂執行", "實作執行"),
    ("課堂進度", "學習進度"),
    ("權重初始化戰略", "權重初始化方法"),
    ("戰略延伸", "延伸思考"),
    ("戰略重要性", "學習重點"),
    ("戰略價值", "實務價值"),
    ("策略價值", "實務價值"),
    ("戰略地圖", "學習地圖"),
    ("戰略藍圖", "學習藍圖"),
    ("順序即戰略", "順序很重要"),
    ("黃金特徵", "資料關係較明顯的特徵"),
    ("黃金參數", "較佳參數"),
    ("黃金組合", "常用組合"),
    ("白話教室", "白話理解"),
    ("教學", "學習"),
    ("課堂", "動手"),
    ("戰略", "實務"),
    ("黃金", "關鍵"),
    ("本章本章學習路線", "本章學習路線"),
    ("本章學習路線與本章學習路線", "本章學習路線"),
    ("本章學習路線與導航", "本章學習路線"),
    ("課程導引：本章學習路線", "本章學習路線"),
    ("常見錯誤：常見錯誤、排除與動手練習", "常見錯誤與動手練習"),
    ("非線性迴歸：專家技術與正規化", "非線性迴歸：進階技術與正規化"),
    ("專家建議", "實作建議"),
    ("數據中繼站", "資料中繼站"),
)

# Third-pass student-voice cleanup. These replacements intentionally remove
# classroom address, career-level framing, and dramatic metaphors.  The goal is
# to state the mechanism or learning result directly, while keeping technical
# terms such as gradient explosion where they are the accepted name of a
# phenomenon.
TONE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("**「So What?」層級分析：", "**實際意義："),
    ("**So What? 拯救過擬合的參數** C", "**實際意義：C 如何控制過擬合**"),
    ("**So What? 為什麼決策樹不需要特徵縮放？**", "**為什麼決策樹不需要特徵縮放？**"),
    ('技術深度解析 (The "So What?" Layer)', "技術重點與實際意義"),
    ("# So What?", "### 實際意義"),
    ("| So What? |", "| 實際意義 |"),
    ("「So What?」實務意義", "實務意義"),
    ("**「So What?」圖層：", "**實際意義："),
    ("**「So What?」觀念強化：**", "**觀念重點：**"),
    ("真貨", "真實樣本"),
    ("假貨", "生成樣本"),
    ("極爛", "品質很差"),
    ("徹底喪失", "無法保留"),
    ("**承接語**", ""),
    ("**轉場引言：** ", ""),
    ("**轉折銜接：** ", ""),
    ("**轉場銜接：** ", ""),
    (
        "歡迎進入機器學習的核心殿堂。本章節被定位為全書的「觀念羅盤」，其目的並非單純的術語定義，而是要幫助你建立一套正確的「資料思維」。",
        "本章先建立機器學習的基本觀念與資料思維，讓你能在後續章節判斷問題類型、資料形式與合適的學習流程。",
    ),
    (
        "從早期的垃圾郵件過濾，到今日能以近乎人類準確率偵測皮膚癌的深度學習模型，甚至是 DeepMind 開發、徹底改變結構生物學的 **AlphaFold**（精準預測蛋白質三維結構），機器學習正以前所未有的速度轉化原始資料為知識。",
        "機器學習已應用於垃圾郵件過濾、影像分類與蛋白質結構預測等任務，可從資料中找出能支援預測或決策的規律。",
    ),
    (
        "**終結語**本章建立了機器學習的基石。請記住，演算法只是工具，真正的威力來自於你對資料結構的理解與嚴謹的流程控管。準備好，我們即將進入下一章的演算法實作。",
        "**本章總結**本章建立了機器學習的基本架構。演算法是工具，模型結果仍取決於資料品質、問題定義與評估流程。下一章將實作感知器與梯度下降。",
    ),
    ("### 感知器的死穴：收斂限制", "### 感知器的收斂限制"),
    (
        "**結語：**掌握了感知器與梯度下降，你已經打開了機器學習的黑盒子。建議嘗試挑選不同的特徵組合（如花萼寬度 vs. 花瓣寬度），觀察模型產生的決策邊界有何變化。下一章我們將進入 Scikit-learn 的世界，見證這些底層邏輯如何被封裝成強大的工業級工具。",
        "**本章總結：**掌握感知器與梯度下降後，你已能說明模型如何更新權重。請嘗試不同的特徵組合（如花萼寬度與花瓣寬度），比較決策邊界的變化。下一章將使用 scikit-learn 的一致 API 套用這些原理。",
    ),
    (
        "各位同學好，歡迎來到資料科學的實戰殿堂！在上一章，我們像是實驗室裡的工匠，親手一滴一滴地調配藥水（從零撰寫 Perceptron）。而從這一章開始，我們要正式進入「現代化自動化工廠」，裝備資料科學界的「瑞士刀」—— **scikit-learn**。",
        "上一章從零實作 Perceptron；本章改用 **scikit-learn** 的一致 API，完成資料前處理、模型訓練、預測與評估。",
    ),
    (
        "各位同學請注意，scikit-learn 之所以強大，是因為它把背後深奧的數學全部包裝在一致的 API 之下。不論你使用的是簡單的感知器，還是複雜的隨機森林，開發門檻都被大幅降低了。",
        "scikit-learn 將不同演算法包裝成一致的 API。無論使用感知器或隨機森林，都可沿用相同的訓練、預測與評估流程。",
    ),
    (
        "**So What? 為什麼特徵標準化這麼重要？**這涉及到「資料外洩 (Data leakage)」的陷阱。**各位同學請筆記**：我們只能用訓練集來 `fit`（找平均值與標準差），然後用這個「標準」去 `transform` 訓練集與測試集。千萬不要讓測試集的資訊滲透進訓練過程中！",
        "**為什麼特徵標準化很重要？** 為避免資料外洩 (Data leakage)，只能用訓練集 `fit` 平均值與標準差，再用同一組參數 `transform` 訓練集與測試集。測試集資訊不能參與前處理參數的估計。",
    ),
    ("我們開始套用第一把機率武器：邏輯斯迴歸。", "接著套用第一個機率式分類模型：邏輯斯迴歸。"),
    ("### 3. 邏輯斯迴歸 (Logistic Regression)：機率預測大師", "### 3. 邏輯斯迴歸 (Logistic Regression)：機率式分類"),
    ("### 5. 支持向量機 (SVM) 與升維魔法 (Kernel Trick)", "### 5. 支持向量機 (SVM) 與核技巧 (Kernel Trick)"),
    (
        "如果說邏輯斯迴歸是機率專家，那 SVM 就是一位「畫線大師」。它有一種「最大化邊界 (Maximum Margin)」的哲學。",
        "SVM 透過最大化類別間隔 (Maximum Margin) 尋找決策邊界；間隔越大，通常越能容忍新資料的小幅變動。",
    ),
    ("**核心觀念：最寬的馬路與升維魔法**", "**核心觀念：最大間隔與核技巧**"),
    (
        "雖然 SVM 強大，但如果你需要一個老闆也能看懂的「透明決策邏輯」，你需要決策樹。",
        "若需要能直接說明判斷規則的模型，可以考慮決策樹。",
    ),
    ("**這是一個超級重點！**", "**判讀重點：**"),
    ("**是否需要跟不懂程式的老闆解釋邏輯？**", "**是否需要向非技術利害關係人說明判斷規則？**"),
    (
        "各位同學，今天的講義到此結束，大家趕快打開 Colab 動手試試吧！",
        "完成本章後，請開啟 Colab，依序執行分類器範例並比較決策邊界。",
    ),
    ("以統計值（平均值、中位數）補齊缺失資料的藝術。", "以統計值（平均值、中位數）補齊缺失資料的方法。"),
    ("### 2. 缺失值處理：資料的補洞藝術", "### 2. 缺失值處理：缺失值填補"),
    ("**減法藝術的實作**", "**逐步移除特徵的實作**"),
    ("**L1 魔法**", "**L1 的稀疏效果**"),
    ("**SBS 暴力法 (Sequential Backward Selection)**", "**SBS 逐步後向選擇 (Sequential Backward Selection)**"),
    (
        "這是一種類似「淘汰賽」的邏輯，每次踢掉一個對準確率影響最小的特徵。",
        "SBS 每一步移除一個對驗證表現影響最小的特徵，直到剩下指定數量的特徵。",
    ),
    ("### 3. LDA：最佳化類別分離度的「狙擊手」", "### 3. LDA：最佳化類別分離度"),
    ("**核魔法（Kernel Trick）**", "**核技巧（Kernel Trick）**"),
    ("將資料彈射到極高維空間", "將資料映射到較高維空間"),
    (
        "在機器學習的開發旅程中，我們往往會經歷從「寫出程式碼讓模型跑起來」到「確保模型在現實世界有用」的關鍵轉變。本章是整個工作流中的分水嶺，象徵著從**盲目訓練**進階到**科學最佳化**的轉折點。若缺乏嚴謹的評估，模型可能只是對已知資料的「死背」（過擬合），而非具備真正的泛化能力。",
        "模型能在訓練資料上運作，不代表能泛化到新資料。本章建立可重複的評估與超參數搜尋流程，用交叉驗證比較模型，並辨識過擬合與資料外洩。",
    ),
    (
        "在深入演算法前，我們先用直覺的比喻來化解學習障礙。手動調參是不科學且不可靠的，我們需要自動化的「工業級」方案。",
        "在比較模型前，先把資料前處理、訓練與評估固定成可重複執行的流程，避免手動步驟造成資料外洩或評估偏差。",
    ),
    (
        "**Pipeline (管線) —— 「自動化生產線」**：「各位同學，想像一間汽車工廠，零件必須經過噴漆、組裝、檢測。如果手動搬運，你可能在噴漆時不小心把『檢測用』的零件也噴了。Pipeline 就是全自動生產線，確保資料嚴格遵守順序，**保證測試集（期末考卷）在訓練時絕對處於密封狀態**，這就是防範『資料外洩』的終極手段。」",
        "**Pipeline (管線)**：把前處理與模型依固定順序封裝在同一流程中。交叉驗證時，每一折只用該折訓練資料估計前處理參數，可降低資料外洩風險。",
    ),
    (
        "**Grid Search (網格搜索) —— 「機器人暴力破解最佳設定」**：「模型有許多手動開關（超參數）。Grid Search 就像一個不知疲倦的機器人，根據你給的參數菜單，暴力破解所有組合並進行模擬考，最終雙手奉上表現最強的『常用組合』。」",
        "**Grid Search (網格搜尋)**：列出候選超參數組合，對每一組執行交叉驗證，再依指定評估指標選出表現較佳的設定。",
    ),
    ("### 7. 自動調參大師：GridSearchCV 與 Nested CV", "### 7. 自動超參數搜尋：GridSearchCV 與 Nested CV"),
    (
        "**運算耗時**：GridSearch 是乘法級別的爆炸。示範時建議先縮減 `param_range`。",
        "**運算時間**：GridSearch 的組合數會隨參數候選數相乘。初次執行可先縮小 `param_range`，確認流程正確後再擴大範圍。",
    ),
    ("**對決大師**：實作 Nested CV", "**模型比較練習**：實作 Nested CV"),
    (
        "集成學習的核心哲學就是「打群架」：透過策略性地組合多個分類器，建立一個比任何單一成員都更強、更穩定的「元分類器（Meta-classifier）」。這種群體協作的模式，能有效抵銷單一模型的預測偏差，將預測表現推向極致。",
        "集成學習會組合多個分類器，利用投票、平均或加權方式產生最終預測。若成員模型具有足夠差異，組合結果通常比單一模型更穩定。",
    ),
    ("## 2. 核心觀念：打群架的藝術", "## 2. 核心觀念：組合多個模型"),
    (
        "**白話觀念解析**各位同學，想像你要預測股市，只聽一位明星分析師的意見風險極高；但如果你同時請教十位分析師並綜合意見，勝率就會顯著提升。",
        "**白話觀念解析**單一模型可能受抽樣或建模假設影響；組合多個彼此不同的模型，可降低個別模型誤差對最終預測的影響。",
    ),
    (
        "**裝袋法 (Bagging)：** 給不同學生略微不同的練習題庫。例如從大題庫中隨機抽題組成 500 份不同的考卷，讓學生練習，這能避免學生「死背」特定題目，提升應變能力。",
        "**裝袋法 (Bagging)：** 從訓練資料重複進行 bootstrap 抽樣，讓每個基礎模型看到略有不同的樣本，再彙整各模型的預測。",
    ),
    ("但各位請記住一個「實務警訊」", "但需注意一個前提"),
    ("只要模型「不是來亂的」", "只要單一模型的錯誤率低於隨機猜測"),
    ("「打群架」就失去了意義", "組合模型便難以降低誤差"),
    ("是 Bagging 的秘密武器", "是 Bagging 增加模型差異的來源"),
    (
        "**結語：** 集成學習是從資料科學家進階為實戰專家的分水嶺。它教會我們不只是追求演算法的精妙，更要學會如何透過策略性的「團隊協作」來突破預測極限。下一個階段，我們將進入非線性模型的深度探索。",
        "**本章總結：** 集成學習透過模型差異與預測彙整，降低單一模型的不穩定性。完成本章後，你應能說明 Voting、Bagging、Boosting 與隨機森林的差異及適用情境。",
    ),
    (
        "**導言：跨越資料科學家的「大師門檻」**各位同學，本章是你們從資料分析師進化為 AI 工程師的關鍵分水嶺。過去我們處理的是整齊的「數值特徵」，但現實世界中 80% 的資料是以非結構化文字的形式存在。文字是「高維度的雜訊」，而 NLP 的本質就是一套精密的「訊號提取藝術」。掌握情緒分析，不僅是為了判斷影評的好壞，更是為了在海量輿情中挖掘商業實務價值。",
        "**導言**本章處理非結構化文字資料。你將把文字轉成可供模型使用的數值特徵，建立影評情緒分類器，並比較詞袋、TF-IDF 與雜湊表示法。",
    ),
    ("封裝為工業級流程", "封裝為可重複使用的流程"),
    ("### 2. 核心觀念：詞袋模型 (Bag-of-Words) 與權重進化", "### 2. 核心觀念：詞袋模型 (Bag-of-Words) 與詞彙權重"),
    ("**IDF 的 Log 魔法**", "**IDF 的對數縮放**"),
    ("**本章學習路線分析**本章是先前技術邏輯的集大成：", "**本章學習路線**本章會串接前面學過的步驟："),
    ("有效壓低「菜市場名」的影響力", "降低常見詞對模型的影響"),
    ("我們將暴力測試以下組合", "我們將系統化測試以下組合"),
    ("**HashingVectorizer 的雜湊魔法**", "**HashingVectorizer 的固定維度表示**"),
    (
        "**結語**掌握了本章，你就擁有了將「混亂文字」轉化為「結構化洞察」的武器。無論是社交媒體監控還是自動化客服系統，這套 NLP 實戰框架都將是你職業生涯中的核心競爭力。",
        "**本章總結**完成本章後，你能把文字轉成數值特徵、訓練情緒分類器，並依資料量與記憶體限制選擇合適的向量化方法。",
    ),
    ("為模型進化建立「回饋迴路」", "建立模型更新所需的「回饋迴路」"),
    ("### 6. 模型進化論：線上學習與系統防護", "### 6. 模型更新：線上學習與系統防護"),
    ("LinearRegression 作為基礎武器，RANSAC 作為篩選外殼", "LinearRegression 作為基礎估計器，RANSAC 負責篩選離群值"),
    (
        "各位同學，在之前的章節中，我們已經掌握了「監督式學習」的精髓——利用現有的標準答案（標籤）來訓練模型。然而，現實世界的商業場景往往沒那麼仁慈。想像一下，當老闆交給你一包十萬筆的客戶消費紀錄，卻沒有告訴你誰是 VIP、誰是潛在流失客，而要求你「進行客群分群」時，你該如何應對？",
        "前面的監督式學習使用已知標籤訓練模型；本章改處理沒有標籤的資料。你將使用聚類方法找出客戶消費紀錄中的群組結構，並比較不同分群結果。",
    ),
    ("具有決定性的實務意義", "有助於理解前向傳播、權重更新與反向傳播的計算流程"),
    ("才迎來現代深度學習的技術突破", "並成為現代深度學習的重要基礎"),
    (
        "本章將引領各位進入 **TensorFlow 與 Keras** 的世界。這不僅是軟體工具的轉換，更是運算思維的躍遷：從傳統 Python 的單執行緒序列運算，轉化為利用 GPU 千核並行的運算能力。",
        "本章介紹 **TensorFlow 與 Keras**。你將使用張量運算、自動微分與 GPU 加速，把前一章的神經網路觀念改寫成可維護的框架實作。",
    ),
    ("像堆疊樂高積木般快速建構、編譯與擬合工業級模型", "使用一致的介面建構、編譯與訓練模型"),
    (
        "各位同學，面對「張量」與「框架」這些冷冰冰的術語，請不必畏難。實際上，TensorFlow 的設計初衷是為了將你從繁瑣的數學與記憶體管理中解放出來。今天我們要學習的是如何「駕駛一輛自動排檔的超級跑車」，而非繼續低頭修理變速箱。",
        "TensorFlow 以張量為資料單位，並提供自動微分、計算圖與硬體加速。你仍需理解數學原理，但不必手動撰寫每一個梯度與記憶體操作。",
    ),
    ("### 白話觀念說明：手排檔車 vs. 超級跑車", "### 白話觀念說明：手寫 NumPy 與 TensorFlow 的分工"),
    (
        "如果「手刻 NumPy 網路」是**手排檔車**，它能讓你看清引擎與齒輪的連動，但要在高速公路上處理大資料，你會疲憊不堪。**TensorFlow** 則是一輛**超級跑車**，它扮演「高效編譯官」的角色，能將你的 Python 指令翻譯給顯卡上的數千個核心，讓原本需要訓練一週的模型，縮短至數小時內完成。",
        "手寫 NumPy 網路適合觀察每一步計算；TensorFlow 則負責自動微分、運算排程與硬體加速。實際加速幅度取決於模型、資料量與執行環境。",
    ),
    ("參數數量將會呈現爆炸式增長", "參數數量會快速增加"),
    ("在工業級開發中，當資料量大到記憶體塞不下", "當資料量大到無法一次放入記憶體"),
    ("### 「致命順序陷阱」與 Buffer Size", "### 資料順序與 Buffer Size"),
    (
        "**結語**：恭喜你踏入工業級開發領域。本章介紹的張量操作與資料管線是未來所有大型專案（如影像辨識、生成對抗網路）的根基。請務必多加練習 Keras 的模型堆疊，我們下一章將深入探討權重更新的底層機械原理。加油！",
        "**本章總結**：本章介紹張量操作、Keras 模型與資料管線。請用不同批次大小重跑範例，觀察訓練時間與結果差異；下一章將進一步拆解權重更新與客製化模型。",
    ),
    ("**工業級資料管線：**", "**可部署的資料管線：**"),
    ("### 6. 第四模組：工業級特徵管線與部署", "### 6. 第四模組：特徵管線與部署"),
    ("加速魔法：@tf.function 與圖編譯", "圖編譯加速：@tf.function"),
    ("**非線性魔法：**", "**非線性轉換：**"),
    ("**Model Subclassing（極致自由）：**", "**Model Subclassing（高度自訂）：**"),
    ("更會導致參數量的劇烈爆炸", "也會讓參數量快速增加"),
    ("極大幅度地降低模型複雜度", "明顯降低模型複雜度"),
    ("最終實現一個工業級的影像分類模型", "最後建立一個可重複訓練與評估的影像分類模型"),
    ("對抗「參數爆炸」", "控制參數數量"),
    ("**專家洞察：**", "**機制說明：**"),
    ("參數會以 (n1×n2)2 的規模爆炸", "參數會以 (n1×n2)2 的規模快速增加"),
    ("具備壓倒性優勢", "具有計算效率優勢"),
    ("避免參數爆炸", "控制參數數量"),
    ("架構徹底顛覆了 NLP 領域", "架構改變了 NLP 的建模方式"),
    ("它拋棄了循環結構", "它不使用循環結構"),
    (
        "在深度學習的廣大版圖中，生成對抗網路（Generative Adversarial Networks, GANs）的出現被譽為近十年來最具突破性的進展。過去，判別式模型（Discriminative Models）教導電腦如何分辨是非真偽；而 GAN 則帶領我們跨越門檻，進入生成式模型（Generative Models）的領域，賦予電腦「創造」的能力。我們不再只是分類影像，而是要從無到有合成出符合真實資料分佈的新樣本。本章將帶你從自動編碼器的壓縮邏輯出發，最終掌握讓兩大神經網路相互搏擊、共同進化的核心技術。",
        "生成對抗網路（Generative Adversarial Networks, GANs）使用生成器與判別器交替訓練，目標是產生接近訓練資料分佈的新樣本。本章從自動編碼器的壓縮表示開始，再實作 GAN 與 DCGAN 的訓練流程。",
    ),
    ("AE 的真正威力在於非線性映射", "AE 的主要優勢在於非線性映射"),
    (
        "各位同學，GAN 的訓練極度依賴運算資源。如果你的電腦沒有高效能 GPU，請務必按照以下步驟設定 Google Colab，這將節省你數小時的等待時間。",
        "GAN 訓練需要較多運算資源。若本機沒有可用 GPU，請依以下步驟設定 Google Colab，以縮短執行時間。",
    ),
    ("**祝各位實作順利，在 GAN 的博弈世界中找到平衡點！**", "**完成實作後，請比較生成器與判別器損失的變化，並檢查生成影像是否逐步穩定。**"),
    ("使其成為解決複雜問題（如機器人控制、自動駕駛、策略遊戲）的終極方案", "可用於機器人控制、自動駕駛與策略遊戲等序列決策問題"),
    ("**理解探索與利用**：學會平衡「尋找更好可能」與「執行已知最佳方案」的決策藝術", "**理解探索與利用**：說明如何平衡「嘗試未知動作」與「採用目前較佳動作」"),
    ("AI 的終極任務", "代理人的學習目標"),
    ("## 3. 決策的藝術：探索", "## 3. 探索"),
    ("## 7. 查表大師：Q-Learning 與方格世界", "## 7. 表格式方法：Q-Learning 與方格世界"),
    ("這時我們需要進化到深度學習版本", "這時可改用深度學習近似價值函數"),
    (
        "**目標值 (Target) 計算**：這是「左腳踩右腳」的魔法。我們用模型預測「下一狀態的最高分」，配合環境回傳的「真實獎勵」組成標籤，來訓練同一個模型。",
        "**目標值 (Target) 計算**：用目標網路估計下一狀態的最高 Q 值，再與環境回傳的獎勵組合成訓練目標。",
    ),
    ("學習過程中的「坑洞」進行防禦性預警", "常見錯誤與檢查方式進行整理"),
    ("梯度下降路徑像喝醉酒一樣", "梯度下降路徑會大幅震盪"),
    (
        "在開始動手寫程式之前，我先送大家一個核心實務觀念：**「天下沒有白吃的午餐 (No Free Lunch Theorem)」**。這是由 David Wolpert 提出的著名定理，簡單來說：沒有任何一個演算法能完美解決所有的分類問題。這就是為什麼我們今天不只學一種模型，而是要一口氣掌握五大分類器，因為你必須根據資料的特性（雜訊多寡、是否線性可分、特徵維度等）來挑選最合適的兵器。",
        "**No Free Lunch Theorem** 提醒我們：沒有單一演算法適合所有分類問題。因此，本章比較五種分類器，並依雜訊、線性可分性與特徵維度等資料特性選擇模型。",
    ),
    (
        "**特徵標準化 (**`StandardScaler`**)**：大家想像一下，如果一個特徵是「年薪（幾百萬）」，另一個是「年齡（兩位數）」，年薪的數值會產生巨大的支配力，導致模型誤判。",
        "**特徵標準化 (**`StandardScaler`**)**：若一個特徵是年薪、另一個是年齡，兩者數值尺度差距很大；依賴距離或梯度的模型可能因此偏向數值較大的特徵。",
    ),
    (
        "雖然名字裡有「迴歸」，但請大家記住：**它是一個貨真價實的分類器！** 它是業界最常用的演算法之一，特別擅長告訴你它對答案有多少「把握」。",
        "邏輯斯迴歸雖以「迴歸」命名，實際用於分類，並可輸出樣本屬於各類別的估計機率。",
    ),
    (
        "**模型訓練 (**`fit`**)**：這是最神聖的一行程式碼。呼叫 `fit(X_train, y_train)`，電腦就開始從資料中尋找權重。",
        "**模型訓練 (**`fit`**)**：呼叫 `fit(X_train, y_train)` 後，模型會從訓練資料估計參數。",
    ),
    ("邏輯斯迴歸 (Logistic Regression)：機率預測大師", "邏輯斯迴歸 (Logistic Regression)：機率式分類"),
    ("支持向量機 (SVM) 與升維魔法 (Kernel Trick)", "支持向量機 (SVM) 與核技巧 (Kernel Trick)"),
    (
        "**核技巧 (Kernel Trick)**：如果有兩群資料長得像「同心圓」，你在 2D 平面怎麼畫直線都切不開。**想像你把這些點往 3D 空間一拋**，中間的點飛得高、外圈的點留得低，你這時只要拿一張紙在空中水平切過，就能完美分開它們。這就是非線性決策邊界的奧秘！",
        "**核技巧 (Kernel Trick)**：同心圓資料無法在原始 2D 空間以直線分開。核函數可隱式計算較高維空間中的相似度，使 SVM 建立非線性決策邊界。",
    ),
    ("大家可以根據以下邏輯來選擇模型", "你可以根據以下條件選擇模型"),
    ("**直接撕掉（刪除）**：若一題沒寫就撕掉整張考卷（整列）或整大題（整行）。", "**直接刪除**：移除含缺失值的資料列或欄位。"),
    (
        "**提示： 專家專業建議 (Pro-Tip)**雖然 pandas 的 `fillna` 很方便，但在實務開發中，我們強烈建議使用 scikit-learn 的 `SimpleImputer`。原因在於 `SimpleImputer` 是一個完整的 Transformer 類別，能完美整合進 Scikit-Learn 的 **Pipeline (管線)** 流程中，這對於生產環境的自動化部署至關重要。",
        "**實作建議**：pandas 的 `fillna` 可直接填補缺失值；若要把填補納入 scikit-learn Pipeline，請使用實作 Transformer 介面的 `SimpleImputer`。",
    ),
    ("**! 專家必備知識：縮放無關性****請記住：", "**縮放與樹模型：**"),
    (
        "**本章總結語**資料前處理是資料科學家的靈魂。完成這些步驟後，你就擁有了精簡、準確且公平的訓練集。別忘了，前處理做對了，模型開發就成功了一半！",
        "**本章總結**資料前處理會直接影響後續模型的輸入品質。完成本章後，你應能處理缺失值、類別特徵、資料切分、縮放與特徵選擇。",
    ),
    ("| 中文術語 | 英文術語 | 專家定義 |", "| 中文術語 | 英文術語 | 定義 |"),
    ("專家級技術筆記", "技術筆記"),
    ("專家警示", "使用限制"),
    ("**專家解釋**", "**原因說明**"),
    ("LDA：最佳化類別分離度的「狙擊手」", "LDA：最佳化類別分離度"),
    ("陷阱三：KPCA 的 Gamma 崩壞", "常見錯誤三：KPCA 的 Gamma 設定不當"),
    ("決策邊界如何發生劇烈崩壞", "不同 gamma 值造成的決策邊界變化"),
    ("模型看診：學習曲線與驗證曲線診斷", "使用學習曲線與驗證曲線診斷模型"),
    (
        "**結語：**掌握模型評估與調校，是從開發者邁向專業資料科學家的必經之路。科學的「看診」與自動化的「調優」，將確保你的模型在面對未知資料時依然穩健可靠。讓我們開始動手實作吧！",
        "**本章總結：**本章整理交叉驗證、學習曲線、驗證曲線、超參數搜尋與模型比較。請接著完成 Colab 練習，檢查評估流程是否避免資料外洩。",
    ),
    (
        "在機器學習的實戰中，我們經常會面臨單一模型的預測瓶頸。無論你如何精雕細琢一棵決策樹，它的泛化能力終究有其極限。從「單兵作戰」進階到「集成學習（Ensemble Learning）」，是技術成長的必經之路，也是在 Kaggle 等高水平競賽中爭取獎項、提升模型穩健性的核心戰術。",
        "單一模型的泛化表現可能受抽樣結果與模型假設限制。集成學習（Ensemble Learning）透過組合多個模型，提高預測穩定性並降低部分估計誤差。",
    ),
    (
        "**本章學習路線導讀**本章在機器學習路徑中扮演著「關鍵橋樑」的角色。它將我們之前學過的基礎工具（如決策樹、SVM、KNN）視為「基底學習器（Base Learners）」，並透過投票、裝袋或提升等高階框架進行封裝與最佳化。掌握了集成學習，你才真正具備了將「堪用模型」轉化為「頂尖預測系統」的工程實力。",
        "**本章學習路線**延續決策樹、SVM 與 KNN，本章使用投票、裝袋與提升方法，比較單一模型與組合模型的表現及穩定性。",
    ),
    (
        "為什麼集結多個「普通專家」的意見，通常能產出比單一「頂尖專家」更穩健的結果？因為群體決策可以相互抵銷個別專家的偏見與偶然性錯誤。",
        "當基礎模型的錯誤不完全相關時，投票或平均可降低個別模型的偏差與偶然誤差。",
    ),
    (
        "在開發初期，部署複雜的資料庫伺服器會增加維運成本。**SQLite** 的實務優勢在於其「無伺服器 (Serverless)」特性——整個資料庫就是一個檔案。這提供了「零設定」的部署體驗，是輕量級應用程式收集回饋的完美方案。",
        "在開發初期，管理獨立資料庫伺服器會增加維運成本。**SQLite** 將資料庫存成單一檔案，不需另行管理伺服器，適合輕量應用程式收集回饋。",
    ),
    ("**學習轉場**：", ""),
    ("我們要拿出一把直尺，找出那條穿過資料叢林的最完美直線", "接著使用線性迴歸估計特徵與目標值之間的線性關係"),
    (
        "**完美的誤差分佈**：殘差點應均勻、隨機地散佈在 0 線上下，看起來像「電視機的雪花雜訊」。這代表模型已經榨乾了特徵中的所有線性資訊。",
        "**殘差分佈**：理想情況下，殘差應在 0 線上下隨機分布，且不呈現明顯結構；若出現曲線或漏斗形狀，表示模型可能遺漏非線性或變異數不等的關係。",
    ),
    ("模型表現跟「盲目猜平均值」一樣爛", "模型表現與使用平均值作為基準預測相近"),
    ("**維度地雷**", "**輸入形狀要求**"),
    (
        "本章將帶領大家從有標準答案的考古題練習，轉向「在沒有解答的世界尋找規律」。非監督式學習（Unsupervised Learning）的核心價值在於**資料探索**，它能自動找出資料中隱藏的結構。**聚類分析（Clustering）** 正是其中的核心工具，它在客戶行為分群、檔案主題分類及推薦系統的基礎建立中，扮演著不可或缺的實務角色。我們不再追求「預測準確度」，而是追求如何將特徵相似的物件歸類，發現資料中那雙「看不見的手」。",
        "本章由監督式學習轉向非監督式學習（Unsupervised Learning）。聚類分析（Clustering）會依特徵相似度將資料分組，可用於客戶分群、文章主題探索與推薦系統前處理。",
    ),
    ("為了讓大家直觀理解演算法，我們將複雜的邏輯轉化為生活中的情境：", "K-means 可拆成以下反覆執行的步驟："),
    ("**找組員**：大家計算自己與各組長的歐幾里得距離，跑向最近的那一組。", "**指派群集**：計算每筆資料與各群集中心的歐幾里得距離，指派給最近的中心。"),
    ("**重複動作**：重複直到大家的位置都不再變動。", "**重複更新**：反覆執行指派與更新，直到群集結果收斂。"),
    ("設得太小，大家都變成了噪音（孤兒）；設得太大，全班都會被合併成同一群", "設得太小會增加噪音點；設得太大則可能合併原本不同的群集"),
    ("從「滿地雜訊」演變成「完美兩群」", "從較多噪音點逐步形成兩個主要群集"),
    (
        "記住，分群的靈魂來自於你對業務領域的理解。下一章，我們將進入具備強大預測能力的領域——**神經網路**。",
        "分群結果仍需配合領域知識、視覺化與評估指標解讀。下一章將介紹多層神經網路。",
    ),
    ("機器學習的「專家決策系統」", "多層感知器的結構"),
    ("而 MLP 則是由多位專家（神經元）層層傳遞訊息的系統", "MLP 則由多個神經元依層次傳遞並轉換訊號"),
    (
        "**結語：** 掌握了從零實作的邏輯，你就掌握了神經網路的靈魂。這份底氣將使你在未來操作 TensorFlow 或 PyTorch 等複雜框架時，能更精準地定位問題並最佳化模型。",
        "**本章總結：**理解從零實作的前向傳播與反向傳播後，你能更有依據地診斷 TensorFlow 或 PyTorch 模型的訓練問題。",
    ),
    (
        "在深度學習的學習路徑上，我們正處於一個從「理論理解」邁向「工業生產」的關鍵轉折點。在此之前，我們透過手刻 NumPy 神經網路，像是在研究室裡拆解引擎，親手推導每一行反向傳播的微積分公式。這對打好基礎至關重要，但當我們面對動輒數百萬參數的現代模型與海量資料時，單靠 CPU 的序列運算已無法負荷。",
        "前一章以 NumPy 拆解神經網路的計算流程；本章改用 TensorFlow 與 Keras 處理參數較多、適合平行運算的模型，並建立可重複執行的訓練流程。",
    ),
    ("GPU 擁有壓倒性的運算性價比", "在適合平行運算的工作負載下，GPU 通常具有較高效能"),
    ("理解硬體潛能後，我們必須學習這台跑車唯一認可的資料燃料——張量。", "接著先理解 TensorFlow 的基本資料單位：張量。"),
    ("_專家技術提示_", "_技術提示_"),
    ("在掌握這台跑車的操作前，我們必須先理解，為什麼傳統的處理方式已經跑不動了。", "使用框架前，先比較 NumPy 手刻流程與 TensorFlow 在計算及資料管線上的差異。"),
    (
        "**專家提示：** 永遠優先設定 `from_logits=True`。這在數學上能讓交叉熵公式中的特定項互相抵消，避免直接計算機率值（Sigmoid/Softmax）帶來的精確度丟失與數值不穩定問題。",
        "**參數設定：** 若輸出層未套用 Sigmoid 或 Softmax，請設定 `from_logits=True`；若輸出已是機率，則設定為 `False`。兩者必須與模型輸出形式一致。",
    ),
    (
        "讓我們進入一個博弈賽局：場上有兩名玩家，一位是「偽鈔製造者 (Generator)」，另一位是「鑑定專家 (Discriminator)」。",
        "GAN 包含生成器 (Generator) 與判別器 (Discriminator)：生成器產生樣本，判別器判斷樣本來自真實資料或生成模型。",
    ),
    ("佔據了極其獨特的實務地位", "處理序列決策問題"),
    ("強化學習的靈魂：互動迴圈與 MDP", "代理人與環境的互動迴圈：MDP"),
    ("訓練初期 AI 什麼都不懂，我們讓 epsilon 很大進行瘋狂探索；隨著訓練進行，AI 變聰明了，我們就逐漸減少隨機性，讓它穩定執行高品質決策", "訓練初期使用較大的 epsilon 增加探索；之後逐步降低 epsilon，提高採用目前較佳動作的比例"),
    ("這是強化學習的靈魂公式", "這是動作價值更新公式"),
    ("如遊戲破關或死掉", "例如完成一個 episode 或進入終止狀態"),
    ("本本章學習路線", "本章學習路線"),
    ("詞袋模型 (Bag-of-Words) 與權重進化", "詞袋模型 (Bag-of-Words) 與詞彙權重"),
    ("模型進化論：線上學習與系統防護", "模型更新：線上學習與系統防護"),
    (
        "本章學習路線為從「簡單機器學習演算法（如 Adaline）」跨越到「現代深度學習架構」的核心橋樑。透過手動建立權重矩陣與實作鏈式法則，你將能掌握模型在收斂困難時的底層邏輯，而非僅僅在超參數的迷霧中盲目摸索。",
        "本章從 Adaline 延伸到多層神經網路；手動建立權重矩陣並實作鏈式法則，能幫助你理解收斂問題與超參數影響。",
    ),
    ("資料的補洞藝術", "缺失值填補"),
    ("取一個合理的統計數字來「補洞」", "使用合適的統計值填補缺失值"),
    ("決策的藝術：探索 (Exploration) 與利用 (Exploitation)", "探索 (Exploration) 與利用 (Exploitation) 的權衡"),
    ("與 PCA 的「盲目」不同，LDA 是監督式學習。它「睜開眼看標籤」", "PCA 不使用標籤；LDA 則是監督式學習，會使用類別標籤"),
    ("流程確定後，我們需要 Python 生態系強大的工具鏈來落實。", "接著使用 Python 生態系的常用套件完成這些步驟。"),
    ("這是一個強大的懲罰機制", "這項權重設計會降低常見詞的影響"),
    ("具備強大優勢", "可將輸出解讀為機率"),
    ("比盲目堆疊多項式次方更具備泛化能力", "比直接增加多項式次方更容易控制模型複雜度"),
    ("掌握了大觀念的實務價值後，我們將定義具體的學習目標，作為衡量你掌握程度的基準。", "接下來列出本章學習目標，方便你逐項自我檢查。"),
    ("白話觀念是第一步，接下來我們必須進入專業的技術術語體系，建立嚴謹的學術溝通語言。", "以下整理本章常用術語，方便你閱讀後續內容。"),
    ("建立術語基礎後，我們將探討資料在電腦中的「數學長相」。", "下一節說明特徵矩陣與目標向量的表示方式。"),
    ("掌握資料的數學結構後，我們將進入標準開發流程，看資料如何轉化為模型。", "接著整理從資料前處理到模型評估的標準流程。"),
    ("工具就緒後，最後要對常見錯誤與檢查方式進行整理。", "最後整理常見錯誤與自我檢查方式。"),
    ("**精通數學表示法**", "**使用數學表示法**"),
    ("重要術語中英對照與深度剖析", "重要術語中英對照與說明"),
    ("機器學習開發管線 (Roadmap) 深度導讀", "機器學習開發管線 (Roadmap)"),
    ("工具鏈與 Colab 實戰操作指南", "工具鏈與 Colab 操作指南"),
    ("實現了極速的向量化操作。以下是本書環境的「關鍵標準」", "提供高效率的向量化操作。以下列出範例使用的套件版本"),
    ("嚴格禁止在開發過程中使用測試集進行調優", "不得在開發過程中使用測試集調整模型"),
    ("**開發紅線**", "**評估原則**"),
    ("**絕對不可以使用**", "**不應使用**"),
    ("**哲學思考**", "**延伸思考**"),
    ("掌握這些基礎演算法是通往深度學習的必經之路；現代深層神經網路的本質，正是由成千上萬個此類基礎神經元連接而成的龐大系統。", "這些基礎演算法有助於理解深度學習；現代深層神經網路由大量神經元依層次連接而成。"),
    ("實戰操作指南：鳶尾花資料集與特徵縮放", "操作指南：鳶尾花資料集與特徵縮放"),
    (
        "請先記住一個核心原則：**模型的價值在於其能提供的真實服務**。即便你的演算法在 Jupyter Notebook 中擁有 99% 的準確率，若無法將其轉化為穩定、可縮放且低延遲的服務介面，它對企業與使用者而言仍只是尚未完成的實驗成果。本講義旨在引導你跨越「模型研發」與「生產工程」之間的鴻溝，建立具備商業價值的預測系統。",
        "模型在 Notebook 中取得良好指標後，仍需包裝成穩定且回應時間可接受的服務。本章將模型串接到網頁介面與資料庫，並說明部署後的更新流程。",
    ),
    ("使用 **核外學習 (Out-of-core Learning)** 與 **雜湊特徵 (Hashing Trick)** 處理海量大資料。", "使用 **核外學習 (Out-of-core Learning)** 與 **雜湊特徵 (Hashing Trick)** 分批處理大量資料。"),
    ("讓模型在有限資源下也能消化海量資料", "讓模型在有限記憶體下分批處理大量資料"),
    ("本章將從既有基礎出發，跨越傳統全連接網路的侷限，進入現代電腦視覺的基石", "本章比較傳統全連接網路與卷積神經網路，並說明 CNN 如何保留影像的空間結構"),
    ("為了從根本解決問題，LSTM", "為了緩解長期依賴與梯度消失問題，LSTM"),
    ("理解為何僅能「還原」的 AE 無法直接用於「憑空創造」", "理解 AE 的重建目標與生成模型的取樣目標有何差異"),
    ("若要「憑空創造」，我們需要引入隨機性，這正是 GAN 的舞台。", "若要產生不同的新樣本，模型還需要可取樣的隨機輸入；下一節介紹 GAN。"),
    ("訓練 DQN 極度耗費資源。在使用 Colab 時，請務必開啟 **GPU 加速**，否則 AI 可能要花數小時才能學會平衡棍子。", "DQN 訓練需要較多運算資源。在 Colab 中請開啟 **GPU 加速**，以縮短 CartPole 範例的訓練時間。"),
    ("請務必", "請"),
    ("千萬不要", "不要"),
    ("海量", "大量"),
    ("極大幅度", "明顯"),
    ("深度剖析", "計算說明"),
    ("深度導讀", "流程說明"),
    ("查表大師", "表格式方法"),
    ("自動調參大師", "自動超參數搜尋"),
    ("對決大師", "模型比較"),
    ("畫線大師", "最大間隔分類器"),
    ("機率預測大師", "機率式分類"),
    ("升維魔法", "核技巧"),
    ("核魔法", "核技巧"),
    ("IDF 的 Log 魔法", "IDF 的對數縮放"),
    ("雜湊魔法", "雜湊映射"),
    ("加速魔法", "圖編譯加速"),
    ("非線性魔法", "非線性轉換"),
    ("秘密武器", "主要機制"),
    ("工業級工具", "具一致介面的工具"),
    ("工業級方案", "自動化方案"),
    ("工業級流程", "可重複使用的流程"),
    ("工業級模型", "可維護的模型"),
    ("工業級開發", "正式專案開發"),
    ("工業級資料管線", "適合大量資料的輸入管線"),
    ("工業級特徵管線", "可部署的特徵管線"),
    ("打群架的藝術", "組合多個模型"),
    ("打群架", "組合模型"),
    ("突破預測極限", "改善預測穩定性"),
    ("推向極致", "進一步改善"),
    ("進化為 AI 工程師", "建立可維護的模型實作"),
    ("大師門檻", "進階主題"),
    ("分水嶺", "轉換階段"),
    ("核心殿堂", "核心主題"),
    ("實戰殿堂", "實作主題"),
    ("殿堂", "主題"),
    ("致命", "常見"),
    ("狙擊手", "分類方法"),
    ("超級跑車", "深度學習框架"),
    ("終極手段", "主要方法"),
    ("終極方案", "適用方法"),
    ("終極任務", "學習目標"),
    ("暴力破解", "逐一評估"),
    ("暴力測試", "系統化測試"),
    ("暴力法", "逐步搜尋法"),
    ("武器", "方法"),
    ("魔法", "機制"),
    ("大師", "進階方法"),
    ("靈魂", "核心"),
    ("工業級", "可重複使用的"),
    ("老闆", "非技術利害關係人"),
    ("大家", "你"),
    ("各位同學請注意，", "請注意，"),
    ("各位同學請筆記", "請記住"),
    ("各位同學好，", ""),
    ("各位同學，", ""),
    ("各位同學", "你"),
    ("各位", "你"),
    ("同學", "你"),
)

TONE_REWRITE_COUNTS: dict[int, int] = {}

FORMAT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (
        "當特徵單位差異巨大（如公分 vs. 毫米）時，SSE 成本函數的等高線會呈現扁平的**「橢圓形」**，導致梯度下降路徑會大幅震盪大幅震盪。****透過標準化（平均值 0、標準差 1），我們可以將等高線拉回**「正圓形」**，讓權重更新的路徑筆直指向谷底，大幅加速收斂。",
        "當特徵單位差異很大（如公分與毫米）時，SSE 成本函數的等高線會呈狹長橢圓形，使梯度下降路徑大幅震盪，降低收斂效率。\n\n透過標準化（平均值 0、標準差 1），等高線會較接近圓形，權重更新路徑也會更直接。",
    ),
    ("**「So What?」深度解析****平均值填補 (Mean Imputation)**", "**平均值填補 (Mean Imputation)**"),
    ("**序列式（Sequential）****降低偏差（Bias）**", "**序列式（Sequential），主要降低偏差（Bias）**"),
    ("**embedding_column：****（關鍵）**", "**embedding_column（關鍵）：**"),
    ("**embedding\\_column：****（關鍵）**", "**embedding_column（關鍵）：**"),
    (
        "**環境需求表 (Environment Requirements)**| 套件 | 版本 | 實務角色 || :--- | :--- | :--- || **NumPy** | 1.17.4 | 多維陣列與底層數學運算 || **SciPy** | 1.3.1 | 科學計算與矩陣最佳化 || **pandas** | 0.25.3 | 表格化資料操作與整理 || **Matplotlib** | 3.1.0 | 資料視覺化與趨勢觀察 || **scikit-learn** | 0.22.0 | 機器學習演算法核心庫 |",
        "**環境需求表 (Environment Requirements)**\n\n| 套件 | 版本 | 實務角色 |\n| --- | --- | --- |\n| **NumPy** | 1.17.4 | 多維陣列與底層數學運算 |\n| **SciPy** | 1.3.1 | 科學計算與矩陣最佳化 |\n| **pandas** | 0.25.3 | 表格化資料操作與整理 |\n| **Matplotlib** | 3.1.0 | 資料視覺化與趨勢觀察 |\n| **scikit-learn** | 0.22.0 | 機器學習演算法核心套件 |",
    ),
    (
        "**混淆矩陣 (Confusion Matrix)**：| | 預測負類 (Benign) | 預測正類 (Malignant) || :--- | :--- | :--- || **真實負類** | TN | **FP (錯殺：誤診)** || **真實正類** | **FN (漏放：漏診)** | TP |",
        "**混淆矩陣 (Confusion Matrix)**\n\n| 實際類別 / 預測類別 | 預測負類 (Benign) | 預測正類 (Malignant) |\n| --- | --- | --- |\n| **真實負類** | TN | FP（誤判為正類） |\n| **真實正類** | FN（誤判為負類） | TP |",
    ),
    ("**\\[此處插入 Pipeline 流向圖，參考 SOURCE\\_IMAGE\\_2\\]**", "Pipeline 順序：標準化 → PCA → 分類器。"),
    ("**\\[此處插入學習曲線對照圖，參考 SOURCE\\_IMAGE\\_6\\]**", "閱讀學習曲線時，請同時比較訓練分數、驗證分數及兩者差距。"),
    ("**\\[此處插入驗證曲線圖，參考 SOURCE\\_IMAGE\\_9\\]**", ""),
    ("**\\[參考 SOURCE\\_IMAGE\\_12\\]**", ""),
    (" `[SOURCE_IMAGE_8]`", ""),
    (" `[SOURCE_IMAGE_9]`", ""),
    (" `\\[SOURCE\\_IMAGE\\_13\\]`**：**", "："),
)

FORMAT_REWRITE_COUNTS: dict[int, int] = {}

BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    ("teacher_terms", r"講師|導師|備課|講者備忘|教師專用"),
    ("answer_markers", r"參考答案|標準答案\s*[:：]|內部解答|解答區"),
    ("internal_markers", r"內部檢核|TEACHER_WORKFLOW|INSTRUCTOR_WORKFLOW"),
    ("private_repo", r"python-machine-learning-2026-instructor|github\.com/[^\s)]+/[^\s)]*instructor"),
    ("local_uri", r"file:///|local_path|/content/drive/MyDrive"),
    ("windows_path", r"(?i)(?<![A-Za-z])[A-Z]:[\\/][^\s`)]*"),
    ("embedded_data", r"data:image/|<svg\b|</svg>"),
    (
        "student_voice",
        r"學員|教案|教學|授課|備課|課堂|戰略|黃金|套件呼叫工|作為資深|我必須向各位強調|請務必強調|我們將帶領學生|引導學生|學生是否能",
    ),
    ("classroom_address", r"各位|同學|大家|承接語"),
    (
        "inflated_tone",
        r"殿堂|大師|分水嶺|工業級|打群架|死穴|致命|狙擊手|魔法|進化為 AI 工程師|突破預測極限|推向極致|沒那麼仁慈|老闆|超級跑車|武器|終極(?:手段|方案|任務)|暴力|靈魂",
    ),
    (
        "tone_audit",
        r"必經之路|職業生涯中的核心競爭力|頂尖預測系統|請務必|千萬不要|趕快|極其獨特|極大幅度|壓倒性|憑空創造|神聖|深度剖析|深度導讀|本本章|補洞藝術|決策的藝術",
    ),
    ("markdown_artifact", r"\\\*\\\*|\*{4}|SOURCE\\?_IMAGE|\|[^\n]*\|\|[^\n]*\|"),
    ("hidden_format", r"[\u200b\u200c\u200d\u2060\ufeff\ufe0f]"),
    ("unsupported_glyph", r"[ϕϵ∼⋅⌊⌋❗⟨⟩🌟💡]"),
)

TAIWAN_LOCALIZATION: tuple[tuple[str, str, str], ...] = (
    ("數據", r"數據", "資料"),
    ("算法", r"(?<!演)算法", "演算法"),
    ("優化", r"優化", "最佳化"),
    ("構建", r"構建", "建立"),
    ("配置", r"配置", "設定"),
    ("文件", r"文件", "檔案"),
    ("代碼", r"代碼", "程式碼"),
    ("運行", r"運行", "執行"),
    ("導入", r"導入", "匯入"),
    ("導出", r"導出", "匯出"),
)

FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"),
    Path(r"C:\Windows\Fonts\msjh.ttf"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
)


@dataclass(frozen=True)
class ChapterArtifact:
    chapter: int
    markdown_path: Path
    pdf_path: Path
    pages: int
    markdown_sha256: str
    pdf_sha256: str
    extracted_chars: int


def ensure_inside_repo(path: Path) -> Path:
    """Resolve a write target and reject anything outside this student repo."""
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"拒絕寫入 student repo 以外的位置：{resolved}") from exc
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_text(text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for code, pattern in BANNED_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            excerpt = re.sub(r"\s+", " ", text[max(0, match.start() - 30) : match.end() + 45])
            findings.append({"code": code, "excerpt": excerpt})
    return findings


def _inline_code_parts(line: str) -> list[str]:
    """Split one Markdown line while retaining `inline code` delimiters."""
    return re.split(r"(`[^`]*`)", line)


def localize_taiwan_prose(markdown: str) -> str:
    """Localize prose without changing fenced code or inline API literals."""
    output: list[str] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            output.append(line)
            continue
        if in_fence:
            output.append(line)
            continue
        parts = _inline_code_parts(line)
        for index in range(0, len(parts), 2):
            for _, pattern, replacement in TAIWAN_LOCALIZATION:
                parts[index] = re.sub(pattern, replacement, parts[index])
        output.append("".join(parts))
    return "\n".join(output)


def scan_localization_prose(markdown: str) -> list[dict[str, object]]:
    """Return non-Taiwan terms that remain outside code/API literals."""
    findings: list[dict[str, object]] = []
    in_fence = False
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = "".join(_inline_code_parts(line)[::2])
        for term, pattern, _ in TAIWAN_LOCALIZATION:
            if re.search(pattern, prose):
                findings.append({"line": line_number, "term": term, "excerpt": prose[:180]})
    return findings


def count_localization_code_exceptions(markdown: str) -> dict[str, int]:
    """Count protected terms that remain only in code fences/inline literals."""
    counts = {term: 0 for term, _, _ in TAIWAN_LOCALIZATION}
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        literals = line if in_fence else " ".join(part[1:-1] for part in _inline_code_parts(line)[1::2])
        for term, pattern, _ in TAIWAN_LOCALIZATION:
            counts[term] += len(re.findall(pattern, literals))
    return {term: count for term, count in counts.items() if count}


def find_import_files(source_dir: Path) -> dict[int, Path]:
    if not source_dir.is_dir():
        raise ValueError("--import-source 必須是存在的資料夾。")
    found: dict[int, Path] = {}
    for path in source_dir.glob("CH*.md"):
        match = re.match(r"CH(\d{2})", path.name, flags=re.IGNORECASE)
        if not match:
            continue
        chapter = int(match.group(1))
        if chapter not in CHAPTER_TITLES:
            continue
        if chapter in found:
            raise ValueError(f"CH{chapter:02d} 有多個來源 Markdown，請先消除歧義。")
        found[chapter] = path
    missing = sorted(set(CHAPTER_TITLES) - set(found))
    if missing:
        raise ValueError(f"來源缺少章節：{missing}")
    if len(found) != 18:
        raise ValueError(f"預期 18 章，實際找到 {len(found)} 章。")
    return found


def strip_export_preamble(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\A---\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    lines = text.splitlines()
    first_section = next(
        (index for index, line in enumerate(lines) if re.match(r"^#{2,3}\s+\d+\\?\.", line)),
        None,
    )
    if first_section is None:
        raise ValueError("找不到章節內容的第一個編號段落。")
    title_indices = [index for index, line in enumerate(lines[:first_section]) if line.startswith("# ")]
    start = title_indices[-1] + 1 if title_indices else first_section
    return "\n".join(lines[start:]).strip()


def repair_embedded_formulae(chapter: int, body: str) -> str:
    svg_pattern = r"!\[\]\(data:image/svg\+xml;.*?</svg>\)\s*"
    if chapter == 10:
        body = re.sub(svg_pattern, "√", body, flags=re.DOTALL)
        body = body.replace("MEDV√", "√MEDV")
    elif chapter == 15:
        body = re.sub(svg_pattern, " → ", body, flags=re.DOTALL)
        body = re.sub(
            r"\*\*維度演變：\*\*.*?(?=\n\s*\n|\n##)",
            "**維度演變：** 28×28×1 → 14×14×32 → 7×7×64 → Flatten",
            body,
            flags=re.DOTALL,
        )
    elif chapter == 16:
        body = re.sub(svg_pattern, "√", body, flags=re.DOTALL)
        body = re.sub(
            r"計算公式為：.*?(?=\n\s*\n|\n##|\n###)",
            "計算公式為：`Attention(Q, K, V) = softmax((QK^T) / √d_k) V`。其中 `√d_k` 用來縮放點積，避免數值過大讓 softmax 過度集中。",
            body,
            flags=re.DOTALL,
        )
    body = re.sub(svg_pattern, "[公式符號] ", body, flags=re.DOTALL)
    return body


def clean_student_tone(chapter: int, body: str) -> str:
    """Apply reproducible plain-language rewrites and record source edits."""
    rewrite_count = 0
    for old, new in TONE_REPLACEMENTS:
        occurrences = body.count(old)
        if occurrences:
            body = body.replace(old, new)
            rewrite_count += occurrences
    TONE_REWRITE_COUNTS[chapter] = rewrite_count
    return body


def normalize_markdown_artifacts(chapter: int, body: str) -> str:
    """Repair escaped emphasis, broken bold boundaries, and collapsed tables."""
    rewrite_count = body.count(r"\*\*")
    body = body.replace(r"\*\*", "**")
    for old, new in FORMAT_REPLACEMENTS:
        occurrences = body.count(old)
        if occurrences:
            body = body.replace(old, new)
            rewrite_count += occurrences
    FORMAT_REWRITE_COUNTS[chapter] = rewrite_count
    return body


def studentize_source(chapter: int, source_text: str) -> str:
    body = strip_export_preamble(source_text)
    body = repair_embedded_formulae(chapter, body)
    for old, new in TEXT_REPLACEMENTS:
        body = body.replace(old, new)

    if chapter == 2:
        body = re.sub(
            r"\*\*學習提醒：\*\*\s*UCI 官方網址.*?`pd\.read_csv\('local_path/iris\.data', header=None\)`。",
            "**學習提醒：** 本課程 Colab 直接載入公開鳶尾花資料，不需要準備本機 CSV。",
            body,
        )
    if chapter == 8:
        body = re.sub(
            r"\*\*實作執行建議：\*\*\s*NLP 運算極重，請務必掌握(?:課堂|動手)節奏。",
            "**實作執行建議：** NLP 運算量較大，請依照 Colab 的執行進度分段完成。",
            body,
        )
    if chapter == 9:
        body = body.replace(
            "作為資深 AI 工程教育專家與系統架構師，我必須向各位強調：",
            "請先記住一個核心原則：",
        ).replace("僅是無效的實驗室產物", "仍只是尚未完成的實驗成果")
    if chapter == 14:
        body = re.sub(
            r"在本章中，(?:我們將帶領學員完成|你將循序完成).*?(?=\n\s*\n)",
            "本章從 Keras 高階 API 的使用經驗出發，帶你理解 TensorFlow 底層機制，並練習自訂損失函數、特殊神經層與可部署的資料流程。",
            body,
            count=1,
            flags=re.DOTALL,
        )
        body = re.sub(
            r"本章設計的核心在於.*?(?=\n\s*\n)",
            "本章聚焦於「拆解底層機制」：不只學會呼叫 API，也要理解背後的數學邏輯與架構權衡。掌握這些機制後，你就能面對客製化需求，做出有依據的設計決策。",
            body,
            count=1,
            flags=re.DOTALL,
        )

    body = body.replace("學員", "你")
    body = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff\ufe0f]", "", body)
    body = localize_taiwan_prose(body)
    body = clean_student_tone(chapter, body)
    body = normalize_markdown_artifacts(chapter, body)

    body = body.replace("\\[ \\]", "- [ ]")
    body = re.sub(r"^(#{2,6}\s+\d+)\\\.", r"\1.", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    title = f"# 第 {chapter:02d} 章｜{CHAPTER_TITLES[chapter]}"
    notice = "> 學生版公開講義｜請搭配本課程 Colab，依照段落逐步操作與自我檢查。"
    source_note = (
        "> 來源說明：課程參考《Python Machine Learning, 3rd Edition》；原始範例程式碼採 MIT License。"
        "本檔由恩恩統計家教整理為學生版學習摘要，不含原書 PDF 或掃描內容。"
    )
    result = f"{title}\n\n{notice}\n\n{source_note}\n\n{body}\n"
    findings = scan_text(result)
    if findings:
        raise ValueError(f"CH{chapter:02d} 學生化後仍含禁止內容：{findings}")
    return result


def import_student_sources(source_dir: Path) -> None:
    source_files = find_import_files(source_dir)
    output_dir = ensure_inside_repo(STUDENT_SOURCE_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    for chapter, source_path in sorted(source_files.items()):
        source_text = source_path.read_text(encoding="utf-8-sig")
        student_text = studentize_source(chapter, source_text)
        target = ensure_inside_repo(output_dir / f"ch{chapter:02d}.md")
        target.write_text(student_text, encoding="utf-8", newline="\n")
        print(f"IMPORTED CH{chapter:02d}: {target.relative_to(REPO_ROOT)}")


def choose_font(explicit_font: Path | None) -> Path:
    candidates = (explicit_font,) if explicit_font else FONT_CANDIDATES
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "找不到支援繁體中文的字型。請以 --font 指定 Noto Sans TC/CJK 字型檔。"
    )


def register_fonts(font_path: Path) -> tuple[str, str]:
    regular_name = "StudentHandoutSans"
    bold_name = "StudentHandoutSansBold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, str(font_path)))
        pdfmetrics.registerFont(TTFont(bold_name, str(font_path)))
        pdfmetrics.registerFontFamily(
            "StudentHandoutSans",
            normal=regular_name,
            bold=bold_name,
            italic=regular_name,
            boldItalic=bold_name,
        )
    return regular_name, bold_name


def inline_markup(value: str) -> str:
    value = value.replace("\\_", "_").replace("\\=", "=")
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<font color="#A34327">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#1E5D78">\1</link>', escaped)
    return escaped


def make_styles(font_name: str, bold_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "HandoutTitle",
            parent=base["Title"],
            fontName=bold_name,
            fontSize=23,
            leading=32,
            textColor=colors.HexColor("#102A43"),
            alignment=TA_LEFT,
            spaceAfter=10 * mm,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "HandoutH2",
            parent=base["Heading2"],
            fontName=bold_name,
            fontSize=16,
            leading=23,
            textColor=colors.HexColor("#C65D2E"),
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "HandoutH3",
            parent=base["Heading3"],
            fontName=bold_name,
            fontSize=12.5,
            leading=19,
            textColor=colors.HexColor("#1E5D78"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "HandoutBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.7,
            leading=16,
            textColor=colors.HexColor("#243B53"),
            spaceAfter=2.2 * mm,
            wordWrap="CJK",
            allowWidows=0,
            allowOrphans=0,
        ),
        "notice": ParagraphStyle(
            "HandoutNotice",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#6B3D20"),
            backColor=colors.HexColor("#FFF1DD"),
            borderColor=colors.HexColor("#E8A35D"),
            borderWidth=0.6,
            borderPadding=8,
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "HandoutBullet",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=15.5,
            textColor=colors.HexColor("#243B53"),
            leftIndent=5 * mm,
            firstLineIndent=-3.5 * mm,
            bulletIndent=1.2 * mm,
            spaceAfter=1.5 * mm,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "HandoutCode",
            parent=base["Code"],
            fontName=font_name,
            fontSize=7.8,
            leading=11.5,
            textColor=colors.HexColor("#16324F"),
            backColor=colors.HexColor("#EFF5F8"),
            borderColor=colors.HexColor("#CBDCE5"),
            borderWidth=0.5,
            borderPadding=6,
            leftIndent=2 * mm,
            rightIndent=2 * mm,
            spaceBefore=1.5 * mm,
            spaceAfter=3 * mm,
            wordWrap="CJK",
        ),
        "table": ParagraphStyle(
            "HandoutTableText",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7.7,
            leading=11.5,
            textColor=colors.HexColor("#243B53"),
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "HandoutTableHeader",
            parent=base["BodyText"],
            fontName=bold_name,
            fontSize=7.8,
            leading=11.5,
            textColor=colors.white,
            wordWrap="CJK",
        ),
    }


def wrap_code(value: str, width: int = 88) -> str:
    wrapped: list[str] = []
    for line in value.splitlines() or [""]:
        if len(line) <= width:
            wrapped.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        pieces = textwrap.wrap(
            line,
            width=width,
            subsequent_indent=" " * min(indent + 2, 12),
            replace_whitespace=False,
            drop_whitespace=False,
        )
        wrapped.extend(pieces or [line])
    return "<br/>".join(html.escape(line, quote=False).replace(" ", "&nbsp;") for line in wrapped)


def parse_table(lines: Sequence[str], styles: dict[str, ParagraphStyle], usable_width: float) -> Table:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    data = [
        [Paragraph(inline_markup(cell), styles["table_header"] if index == 0 else styles["table"]) for cell in row]
        for index, row in enumerate(normalized)
    ]
    widths = [usable_width / column_count] * column_count
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E5D78")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8CAD4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def markdown_story(markdown: str, styles: dict[str, ParagraphStyle], usable_width: float) -> list[object]:
    lines = markdown.splitlines()
    story: list[object] = []
    index = 0
    in_code = False
    code_lines: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            value = " ".join(part.strip() for part in paragraph_lines).strip()
            if value:
                story.append(Paragraph(inline_markup(value), styles["body"]))
            paragraph_lines.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Paragraph(wrap_code("\n".join(code_lines)), styles["code"]))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not line.strip():
            flush_paragraph()
            index += 1
            continue
        if line.strip() in {"---", "***", "* * *"}:
            flush_paragraph()
            story.append(Spacer(1, 2.5 * mm))
            index += 1
            continue
        if line.startswith("| ") or (line.startswith("|") and line.endswith("|")):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            if len(table_lines) >= 2:
                story.extend([parse_table(table_lines, styles, usable_width), Spacer(1, 3 * mm)])
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            value = inline_markup(heading.group(2).replace("\\.", "."))
            if level == 1:
                story.append(Paragraph(value, styles["title"]))
            elif level == 2:
                story.append(Paragraph(value, styles["h2"]))
            else:
                story.append(Paragraph(value, styles["h3"]))
            index += 1
            continue
        if line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:].strip()), styles["notice"]))
            index += 1
            continue
        bullet = re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$", line)
        if bullet:
            flush_paragraph()
            story.append(Paragraph(inline_markup(bullet.group(1)), styles["bullet"], bulletText="•"))
            index += 1
            continue
        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    if in_code and code_lines:
        story.append(Paragraph(wrap_code("\n".join(code_lines)), styles["code"]))
    return story


def render_pdf(chapter: int, markdown_path: Path, pdf_path: Path, font_path: Path) -> None:
    font_name, bold_name = register_fonts(font_path)
    styles = make_styles(font_name, bold_name)
    output = ensure_inside_repo(pdf_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    usable_width = A4[0] - 34 * mm

    def footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.setLineWidth(0.45)
        canvas.line(17 * mm, 14 * mm, A4[0] - 17 * mm, 14 * mm)
        canvas.setFont(font_name, 7.6)
        canvas.setFillColor(colors.HexColor("#627D98"))
        canvas.drawString(17 * mm, 9.5 * mm, "恩恩統計家教｜Python 機器學習 2026・學生版")
        canvas.drawRightString(A4[0] - 17 * mm, 9.5 * mm, f"CH{chapter:02d} · {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=19 * mm,
        title=f"CH{chapter:02d} {CHAPTER_TITLES[chapter]}",
        author="恩恩統計家教",
        subject="Python 機器學習 2026 學生版公開講義",
        creator="student handout build pipeline",
        pageCompression=1,
    )
    markdown = markdown_path.read_text(encoding="utf-8")
    story = markdown_story(markdown, styles, usable_width)
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def verify_chapter(chapter: int, markdown_path: Path, pdf_path: Path) -> ChapterArtifact:
    if not markdown_path.is_file():
        raise ValueError(f"缺少學生 Markdown：{markdown_path.relative_to(REPO_ROOT)}")
    markdown = markdown_path.read_text(encoding="utf-8")
    source_findings = scan_text(markdown)
    if source_findings:
        raise ValueError(f"CH{chapter:02d} Markdown 內容掃描失敗：{source_findings}")
    localization_findings = scan_localization_prose(markdown)
    if localization_findings:
        raise ValueError(f"CH{chapter:02d} 台灣用語掃描失敗：{localization_findings}")
    if CHAPTER_TITLES[chapter] not in markdown:
        raise ValueError(f"CH{chapter:02d} Markdown 缺少標準章名。")
    if not pdf_path.is_file() or pdf_path.stat().st_size < 20_000:
        raise ValueError(f"CH{chapter:02d} PDF 缺失或檔案過小。")
    if pdf_path.read_bytes()[:5] != b"%PDF-":
        raise ValueError(f"CH{chapter:02d} PDF 標頭錯誤。")

    reader = PdfReader(str(pdf_path))
    extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
    pdf_findings = scan_text(extracted)
    if pdf_findings:
        raise ValueError(f"CH{chapter:02d} PDF 文字掃描失敗：{pdf_findings}")
    if len(extracted) < 500:
        raise ValueError(f"CH{chapter:02d} PDF 可抽取文字過少：{len(extracted)}")
    if "學生版公開講義" not in extracted:
        raise ValueError(f"CH{chapter:02d} PDF 缺少學生版識別。")
    return ChapterArtifact(
        chapter=chapter,
        markdown_path=markdown_path,
        pdf_path=pdf_path,
        pages=len(reader.pages),
        markdown_sha256=sha256_file(markdown_path),
        pdf_sha256=sha256_file(pdf_path),
        extracted_chars=len(extracted),
    )


def write_report(artifacts: Iterable[ChapterArtifact], font_path: Path | None, mode: str) -> None:
    rows = list(artifacts)
    code_exceptions: dict[str, int] = {}
    for row in rows:
        chapter_counts = count_localization_code_exceptions(row.markdown_path.read_text(encoding="utf-8"))
        for term, count in chapter_counts.items():
            code_exceptions[term] = code_exceptions.get(term, 0) + count
    report = {
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "repo_guard": {
            "repo_root_name": REPO_ROOT.name,
            "fixed_source_dir": "handouts/student",
            "fixed_pdf_dir": "docs/handouts",
            "output_containment": "PASS",
        },
        "counts": {
            "chapters": len(rows),
            "markdown": sum(row.markdown_path.is_file() for row in rows),
            "pdf": sum(row.pdf_path.is_file() for row in rows),
        },
        "scan": {
            "banned_pattern_groups": [code for code, _ in BANNED_PATTERNS],
            "markdown_findings": 0,
            "pdf_text_findings": 0,
        },
        "taiwan_localization": {
            "profile": "speak-human-tw",
            "prose_findings": 0,
            "protected_code_or_api_exceptions": code_exceptions,
        },
        "student_tone_cleanup": {
            "profile": "speak-human-tw-round-3",
            "source_rewrites": sum(TONE_REWRITE_COUNTS.values()),
            "by_chapter": {
                f"ch{chapter:02d}": count
                for chapter, count in sorted(TONE_REWRITE_COUNTS.items())
            },
            "remaining_findings": 0,
        },
        "markdown_format_cleanup": {
            "source_rewrites": sum(FORMAT_REWRITE_COUNTS.values()),
            "by_chapter": {
                f"ch{chapter:02d}": count
                for chapter, count in sorted(FORMAT_REWRITE_COUNTS.items())
            },
            "remaining_findings": 0,
        },
        "font_file": font_path.name if font_path else None,
        "chapters": [
            {
                "chapter": row.chapter,
                "markdown": row.markdown_path.relative_to(REPO_ROOT).as_posix(),
                "pdf": row.pdf_path.relative_to(REPO_ROOT).as_posix(),
                "pages": row.pages,
                "extracted_chars": row.extracted_chars,
                "markdown_sha256": row.markdown_sha256,
                "pdf_sha256": row.pdf_sha256,
            }
            for row in rows
        ],
    }
    target = ensure_inside_repo(REPORT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--import-source",
        type=Path,
        help="讀取含 CH01...CH18 Markdown 的來源資料夾，學生化後寫入 handouts/student。",
    )
    parser.add_argument("--font", type=Path, help="指定支援繁體中文的 TTF/TTC 字型。")
    parser.add_argument("--verify-only", action="store_true", help="只掃描既有 Markdown/PDF，不重新渲染。")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if REPO_ROOT.name != "python-machine-learning-2026-student":
        raise SystemExit("安全檢查失敗：此腳本只能在 public student repo 執行。")
    for directory in (STUDENT_SOURCE_DIR, PDF_OUTPUT_DIR, REPORT_PATH.parent):
        ensure_inside_repo(directory)

    if args.import_source and args.verify_only:
        raise SystemExit("--import-source 與 --verify-only 不可同時使用。")
    if args.import_source:
        import_student_sources(args.import_source.resolve())

    font_path: Path | None = None
    if not args.verify_only:
        font_path = choose_font(args.font.resolve() if args.font else None)
        for chapter in CHAPTER_TITLES:
            markdown_path = ensure_inside_repo(STUDENT_SOURCE_DIR / f"ch{chapter:02d}.md")
            pdf_path = ensure_inside_repo(PDF_OUTPUT_DIR / f"ch{chapter:02d}.pdf")
            render_pdf(chapter, markdown_path, pdf_path, font_path)
            print(f"RENDERED CH{chapter:02d}: {pdf_path.relative_to(REPO_ROOT)}")

    artifacts = [
        verify_chapter(
            chapter,
            ensure_inside_repo(STUDENT_SOURCE_DIR / f"ch{chapter:02d}.md"),
            ensure_inside_repo(PDF_OUTPUT_DIR / f"ch{chapter:02d}.pdf"),
        )
        for chapter in CHAPTER_TITLES
    ]
    write_report(artifacts, font_path, "verify" if args.verify_only else "build")
    print(f"PASS: {len(artifacts)}/18 student handouts validated")
    print(f"REPORT: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
