# Lab Guide: Multi-Agent Research System

## Scenario

Bạn cần xây dựng một research assistant có thể nhận câu hỏi dài, tìm thông tin, phân tích và viết câu trả lời cuối cùng. Lab yêu cầu so sánh hai cách làm:

1. **Single-agent baseline**: một agent làm toàn bộ.
2. **Multi-agent workflow**: Supervisor điều phối Researcher, Analyst, Writer, Critic.

## Quy tắc quan trọng

- Không thêm agent nếu không có lý do rõ ràng.
- Mỗi agent phải có responsibility riêng.
- Shared state phải đủ rõ để debug.
- Phải có trace hoặc log cho từng bước.
- Phải benchmark, không chỉ nhìn output bằng cảm tính.

## Milestone 1: Baseline

Đã hoàn thành trong:
- `src/multi_agent_research_lab/cli.py`
- `src/multi_agent_research_lab/services/llm_client.py`

## Milestone 2: Supervisor

Đã hoàn thành trong:
- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/graph/workflow.py`

Routing policy:
- `researcher` ➔ `analyst` ➔ `writer` ➔ `critic` ➔ `done` (kèm `MAX_ITERATIONS = 6` guardrail).

## Milestone 3: Worker agents

Đã hoàn thành trong:
- `src/multi_agent_research_lab/agents/researcher.py`
- `src/multi_agent_research_lab/agents/analyst.py`
- `src/multi_agent_research_lab/agents/writer.py`
- `src/multi_agent_research_lab/agents/critic.py`

## Milestone 4: Trace và benchmark

Đã hoàn thành trong:
- `src/multi_agent_research_lab/observability/tracing.py`
- `src/multi_agent_research_lab/evaluation/benchmark.py`
- `src/multi_agent_research_lab/evaluation/report.py`

Benchmark tối thiểu:

| Metric | Cách đo gợi ý | Kết quả thực nghiệm |
|---|---|---|
| Latency | wall-clock time | Baseline: 10.59s \| Multi-Agent: 26.16s |
| Cost | token usage hoặc provider usage | Baseline: $0.0005 \| Multi-Agent: $0.0021 |
| Quality | rubric 0-10 do peer review | Baseline: 8.0/10 \| Multi-Agent: 10.0/10 |
| Citation coverage | số claims có source / tổng claims chính | Baseline: 0% \| Multi-Agent: 100% |
| Failure rate | số query fail / tổng query | 0% (Không phát sinh lỗi) |

## Exit ticket

### 1. Case nào nên dùng multi-agent? Vì sao?
- **Nên dùng:** Cho các bài toán phức tạp đòi hỏi nhiều giai đoạn xử lý riêng biệt và độ chính xác/xác thực thông tin cao (ví dụ: Nghiên cứu khoa học, tổng hợp tài liệu chuyên sâu, phân tích tài chính/thị trường, review code và kiểm thử tự động).
- **Vì sao:** Vì Multi-Agent phân chia trách nhiệm rõ ràng (Separation of Concerns: Search ➔ Analysis ➔ Synthesis ➔ Verification), kiểm soát chất lượng qua từng chốt chặn, hạn chế tràn bộ nhớ context và loại bỏ triệt để ảo giác (hallucination) nhờ trích dẫn nguồn có kiểm chứng.

### 2. Case nào không nên dùng multi-agent? Vì sao?
- **Không nên dùng:** Cho các tác vụ đơn giản, hội thoại chatbot cơ bản, trích xuất thực thể, dịch thuật ngắn, hoặc các ứng dụng yêu cầu phản hồi theo thời gian thực (latency < 1-2s).
- **Vì sao:** Vì Multi-Agent tạo thêm độ trễ do gọi nhiều LLM và xử lý đồ thị, tiêu tốn chi phí token gấp 3-5 lần và làm tăng độ phức tạp trong bảo trì mà không mang lại giá trị gia tăng tương xứng cho các tác vụ đơn giản.
