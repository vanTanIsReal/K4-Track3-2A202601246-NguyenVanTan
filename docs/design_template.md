# Design Document: Multi-Agent Research System

## 1. Problem Definition
Xây dựng một hệ thống trợ lý nghiên cứu tự động (AI Research Assistant) có khả năng tiếp nhận các câu hỏi nghiên cứu phức tạp, tự động tìm kiếm tài liệu từ web và kho dữ liệu nội bộ, phân tích đa chiều, tổng hợp câu trả lời chuyên sâu kèm nguồn trích dẫn đầy đủ và kiểm định chất lượng để chống ảo giác (hallucination).

## 2. Why Multi-Agent?
1. **Separation of Concerns:** Phân tách rõ ràng giữa việc thu thập thông tin (Researcher), phân tích luận điểm (Analyst), biên soạn nội dung (Writer) và thẩm định độc lập (Critic).
2. **Context Hygiene:** Ngăn chặn việc dồn toàn bộ prompt vào một lượt gọi LLM duy nhất gây nhiễu context và suy giảm chú ý.
3. **Traceability & Debugging:** Dễ dàng phát hiện lỗi sai phát sinh từ khâu nào nhờ shared state và tracing hooks.
4. **Factual Grounding:** Đạt độ phủ trích dẫn 100% thay vì câu trả lời phỏng đoán của single-agent.

## 3. Agent Roles Specification

| Agent | Responsibility | Input | Output | Failure Mode & Recovery |
|---|---|---|---|---|
| **Supervisor** | Điều phối vòng đời workflow, quyết định node kế tiếp | `ResearchState` | `route_history`, `iteration` | Infinite Loop ➔ Giới hạn `MAX_ITERATIONS` |
| **Researcher** | Tìm kiếm web (Tavily) hoặc kho tri thức offline | `state.request` | `state.sources`, `state.research_notes` | Không có kết quả ➔ Fallback local corpus |
| **Analyst** | Phân tích ưu/nhược điểm, trích xuất luận điểm | `state.sources`, `state.research_notes` | `state.analysis_notes` | Thiếu evidence ➔ Ghi nhận thiếu sót |
| **Writer** | Viết bài tổng hợp có trích dẫn inline `[1]`, `[2]` | `state.analysis_notes`, `state.sources` | `state.final_answer` | Format sai ➔ Prompting schema ràng buộc |
| **Critic** | Thẩm định chéo, rà soát hallucination | `state.final_answer`, `state.sources` | `AgentResult(critic)` | Điểm thấp ➔ Báo cáo chất lượng |

## 4. Shared State Schema
Sử dụng `ResearchState` (Pydantic):
- `request`: Câu hỏi gốc, số lượng nguồn tối đa, đối tượng độc giả.
- `iteration`: Bộ đếm vòng lặp chống loop.
- `route_history`: Lịch sử các bước router điều hướng.
- `sources`: Danh sách tài liệu tra cứu được.
- `research_notes` & `analysis_notes`: Ghi chú trung gian giữa các agent.
- `final_answer`: Kết quả cuối cùng.
- `agent_results` & `trace`: Đo lường chi phí, token và timeline.

## 5. Routing Policy & Graph Flow
Đồ thị `StateGraph` xây dựng trên **LangGraph**:
`supervisor` ➔ `researcher` ➔ `supervisor` ➔ `analyst` ➔ `supervisor` ➔ `writer` ➔ `supervisor` ➔ `critic` ➔ `supervisor` ➔ `END`.

## 6. Guardrails
- **Max iterations:** Cố định `MAX_ITERATIONS = 6`.
- **Timeout:** Cấu hình 60s cho mỗi lời gọi API.
- **Retry:** Tự động retry 3 lần với exponential backoff qua `tenacity`.
- **Fallback:** Tự động chuyển đổi sang tìm kiếm nội bộ và heuristic synthesis khi mạng lỗi.
- **Validation:** Toàn bộ dữ liệu được validate chặt chẽ qua Pydantic schema.

## 7. Benchmark Plan
- **Query thử nghiệm:** `"Research GraphRAG state-of-the-art and write a comprehensive summary"`.
- **Chỉ số đo lường:** Latency (s), Token Cost (USD), Quality Score (0-10), Citation Coverage (%), Failure Rate (%).
