---
title: "Context Packing"
date: 2026-05-14
description: "RAG retrieve 後把 chunks 去重、排序、壓縮、標來源，再塞進 prompt 的組裝決策"
weight: 1
tags: ["llm", "knowledge-cards", "rag", "retrieval", "context"]
---

Context packing 的核心概念是「**retrieve 拿到候選 chunks 後，決定哪些內容、以什麼順序、帶哪些 metadata 塞進 prompt**」。它是 [RAG](/llm/knowledge-cards/rag/) 在 retrieval 與 generation 之間的 context 組裝層，有別於 retrieval 本身。

## 跟其他概念的關係

Context packing 位在 top-k retrieval 結果與 LLM prompt 之間。它跟 [retrieval source](/llm/knowledge-cards/retrieval-source/) 相鄰，因為來源 metadata 會影響引用；也跟 [lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/) 相鄰，因為 chunk 順序會影響模型注意力。

## 可觀察訊號與例子

常見 packing 決策包含 dedup 重複 chunk、把最相關內容放前後、按 document order 保留段落流、摘要或壓縮過長 chunks、在每段前加 source path 與 score。這些決策會改變答案品質、token cost 與可追溯性。

## 判斷條件與後果

Context packing 的每個決策都在答案品質、token cost 與可追溯性之間取捨，哪一項優先由場景決定：

- **答案要能追溯來源時**（引用、稽核）：chunk 前沒有 source path，答案就指不出依據是哪份文件；保留 metadata 的代價是每段多佔一些 token。
- **prompt 很長時**：放在中間的 chunk 較容易被模型忽略（[lost-in-the-middle](/llm/knowledge-cards/lost-in-the-middle/)），最相關的 chunk 排在中間時，答案可能沒用到它，所以最相關的內容排在前後。
- **延遲敏感時**：top-k 越大 prompt 越長，每多一次 summarization 或 compression call 就多一次模型往返，兩者都直接加在回應時間上，所以這類場景的 top-k 與 compression call 數量要設上限。
