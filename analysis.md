# Phân tích kết quả Benchmark

Sau khi thực hiện chạy bài kiểm tra, chúng ta có thể rút ra một số kết luận rõ ràng như sau để so sánh giữa hai Agent:

## 1. Vì sao Advanced có recall tốt hơn Baseline?
Trong Baseline, Agent sẽ "quên" hoàn toàn mọi ngữ cảnh cũ ngay khi đổi sang phiên làm việc mới (thread mới). Ngược lại, Advanced Agent tích hợp cơ chế ghi nhớ các dữ liệu cốt lõi vào file `User.md` thông qua Persistent Memory. Do đó, khi qua các thread mới, Advanced Agent vẫn luôn kèm theo profile này vào đầu prompt, giúp nhớ được sở thích, tên, nghề nghiệp của User. Điều này giúp điểm số Cross-session recall tăng lên đáng kể ở Advanced Agent.

## 2. Vì sao Advanced có thể tốn Token hơn ở hội thoại ngắn?
Dù vượt trội về ghi nhớ, Advanced Agent phải liên tục truyền bộ khung ngữ cảnh (bao gồm toàn bộ nội dung trong `User.md` và Context Summary ngắn) vào từng câu lệnh (prompt load). Trong những hội thoại quá ngắn, Baseline chỉ phải nạp những câu hỏi-đáp trước đó của chính phiên, trong khi Advanced phải mang vác thêm hành trang Persistent Memory. Vì vậy, `Prompt tokens processed` của Advanced thường bị đội lên ở `Standard Benchmark`.

## 3. Vì sao Compact giúp Advanced có lợi thế ở hội thoại dài?
Khi chuyển sang bài test `Long-Context Stress Benchmark`, số lượng câu nói trong 1 phiên có thể rất dài và lan man. 
- Baseline Agent sẽ đưa toàn bộ nội dung từ đầu chí cuối của cuộc hội thoại vào Prompt, khiến số lượng Token tăng theo cấp số cộng phi mã (~38000 tokens).
- Advanced Agent kích hoạt Compact Memory: khi ngữ cảnh vượt quá số lượng Tokens cho phép, hệ thống sẽ tiến hành "nén" (summarize) những câu chat cũ lại thành 1 đoạn tóm tắt siêu ngắn và chỉ giữ lại vài tin nhắn gần nhất. Nhờ việc "dọn dẹp" này, số tokens tiết kiệm được ở các lượt chat sau là khổng lồ (~8800 tokens, chỉ bằng khoảng 1/4 so với Baseline), bất chấp việc hội thoại có dài tới đâu.

## 4. File memory tăng trưởng ra sao và rủi ro gì đi kèm?
Mỗi khi có thông tin cá nhân mới, file memory (`User.md`) sẽ tăng trưởng lên theo số lượng Byte ghi nhận (`Memory growth`). Rủi ro lớn nhất ở đây là việc **lưu sai Fact** (User chỉ hỏi, không khẳng định nhưng Agent hiểu nhầm thành Fact và lưu), hoặc bị **xung đột Fact** (Người dùng đổi chỗ ở mới, nhưng hệ thống lại ghi đè sai hoặc lưu cả 2). Việc phình to User.md quá mức cũng có thể làm đội chi phí token nếu không có chiến lược cắt giảm hoặc bốc tách (Entity extraction) rõ ràng.
