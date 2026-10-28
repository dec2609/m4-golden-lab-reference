# Bàn giao M4 — Huỳnh Hồng Ánh Tuyết

### A. Bối cảnh và cách dùng reference

Golden Lab là **sandbox tích hợp nội bộ của Thuận**, nay công bố thành [repository tham chiếu Private](https://github.com/dec2609/m4-golden-lab-reference). Nó không phải repository nhóm, `origin/main` của nhóm hoặc một dependency bắt buộc phải copy. Source/patch chỉ để đối chiếu behavior; sửa implementation và gửi PR tại **https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental**. Không copy cả candidate, không cherry-pick assembled commit hoặc dùng historical evidence làm current PASS.

Clone tham chiếu ở thư mục riêng (cần Thuận cấp quyền đọc Private repo; không dùng token trong URL):

~~~bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
~~~

**Publication source/evidence SHA bất biến: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.** Đây là commit mới trong repo tham chiếu; khác candidate checkpoint local `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef` và local package checkpoint `5cba5d2e45f946865737dfec5762427e8a7de6e5`. Không yêu cầu checkout các SHA local đó trên GitHub. Handoffs được bổ sung ở commit publication sau source pin; khi cần đọc đúng source dùng GitHub `/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/...` hoặc `git show 4c35990241e96f8d1d35de7e2615e12c55cf673b:candidate/<path>` trong clone tham chiếu. Links tương đối dưới đây hoạt động ở bản publication chứa handoffs.

Bạn có thể hiểu việc cần làm từ file này và contract chính thức; không phải xin thư mục máy Thuận để biết semantics. Reference source là một cách triển khai đã thử, **không yêu cầu giữ tên private helper hoặc tên file regression giống sandbox** nếu behavior tương đương đã được chứng minh. Không tự coi một tên hàm thiếu là finding.

Tuyết phụ trách backend/Orders/PostgreSQL/readiness; PR14 đã merge theo metadata28/10. Nhiệm vụ này chỉ thu evidence an toàn cơ bản của existing runtime. Không yêu cầu implement adapter hoặc các helpers của Golden Lab.

### B. Contract và giao diện liên quan

Contract chính thức: **m4-contract-1.0**, [PR17](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/pull/17), commit **`9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d`**. Metadata đọc ngày28/10/2026 cho thấy PR17 đã merge; đây không phải một cuộc audit lại source hoặc CI.

- [CONTRACT.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/CONTRACT.md)
- [SCHEMA.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/SCHEMA.md)
- [WORKFLOW.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/WORKFLOW.md)
- [ACCEPTANCE.md](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/ACCEPTANCE.md)

Contract quy định interface/behavior, không tự đưa runtime fixes vào main. Bản read-only giống commit trên nằm trong `contract-spec/` của repo tham chiếu. Không đổi schema/acceptance hoặc thêm policy ngoài contract.

Chỉ giữ Orders/readiness interface và phân biệt application behavior với release approval. Emitter/gate/resource helpers/test harness là việc integration owners, không phải checklist port của Tuyết.

### C. Vấn đề cần đối chiếu

Cần tách source inspection, Flask DB-double tests và PostgreSQL runtime. Một response generic/unitmock không chứng minh mọi error response an toàn; health200 không chứng minh DB ready. Hạn chế runtime lịch sử không tự là lỗi ở current source. Không kéo việc viết report thành một pentest mới.

### D. Evidence hiện có và giới hạn

[final-backend.json](../evidence/final-backend.json) và [log](../evidence/final-backend.log) ghi18 selected tests exit0 tại53f18d8: DB doubles, loại `test_get_orders`/`test_create_order_and_read_back` cần DB thật. [Backend owner report](../evidence/backend-author-report.md) ngày21–22/10 ghi POST/GET, boundaries, restart/persistence, readiness200→503→200 và runtime role permissions; đây là author-reported historical evidence, cần raw logs/identity trước khi dùng cho current runtime. Một số limitation về pin/version trong báo cáo cũ khác source reference mới hơn: không chuyển chúng thành lỗi mới hoặc sửa report cũ.

Publication không chạy lại backend/Docker; không gọi log18 là real PostgreSQL PASS. Không yêu cầu Tuyết tải whole Golden Lab hoặc đưa toàn bộ reference vào repo nhóm.

### E. Hướng dẫn kỹ thuật tự đầy đủ

**Nhiệm vụ nhỏ: Backend Security Verification — Existing Runtime.** Không auth mới, scanner/WAF/pentest framework, migration/stack mới, security gate, staging/rollback hoặc thay architecture. Ưu tiên evidence đã có; bổ sung khoảng6–8 requests representative trên runtime được phép nếu sẵn sàng. Không cần chờ pipeline hoàn tất để điền `docs/report-input/TUYET.md` trong ngày.

Source: [app.py](../candidate/ma-nguon/order-app/app.py), [test_app.py](../candidate/ma-nguon/order-app/tests/test_app.py), [Dockerfile](../candidate/ma-nguon/order-app/Dockerfile), [Compose](../candidate/docker-compose.yml), [runtime SQL](../candidate/ma-nguon/database/002-runtime-role.sql). Đây là source tham chiếu, đối chiếu SHA/môi trường của mình trước khi áp oracle.

| Endpoint | Oracle theo source, không là kết quả đã chạy hôm nay |
|---|---|
| GET /health | 200/status=ok; không đo DB |
| GET /ready | SELECT1;200 ready/database connected, lỗi503 unready/database unreachable |
| GET /orders | 200/orders array; DB/query lỗi500 generic Internal server error |
| POST /orders | JSON object; customer_name/product_name chuỗi không trắng; quantity int1..2147483647, bool bị từ chối; hợp lệ201, validation400, DBerror500 generic |

Xác minh URL/port trước; backend trực tiếp không tự có `/api/orders` (đó là proxy khi cấu hình). POST chỉ trên runtime riêng được phép hoặc xin chủ môi trường; dữ liệu synthetic nhãn BSV, không dữ liệu cá nhân.

| Test ID | Mục tiêu | Kiểm nhỏ cần làm | Observation/evidence/status |
|---|---|---|---|
| BSV-01 | Valid request | POST một order rồi GET readback nếu được phép ghi; hoặc trích runtime logs cũ đúng source/date | [Tuyết điền HTTP/body/ID/path; PASS/FAIL/NOT VERIFIED/N/A] |
| BSV-02 | Input validation | Thiếu customer; quantity string/bool;0 hoặc2147483648; malformed JSON. Chọn đại diện, không fuzz | [Tuyết điền từng case/layer/status] |
| BSV-03 | Error exposure | Đọc generic handler/tests DB exception, quan sát actual response an toàn: traceback, DSN, credentials/internal details có lộ không | [Tách unit/actual; chưa có DB-error response ghi NOT VERIFIED] |
| BSV-04 | Readiness/DB failure | GET healthy; dùng existing outage/recovery evidence trước. Chỉ gây outage ở runtime riêng được phép | [Healthy/outage/recovery ghi riêng; không stop DB chung] |
| BSV-05 | Configuration | Env mechanism/dev defaults/debug/auth assumptions; đọc Dockerfile/Compose/SQL đúng SHA | [Static vs effective runtime, không auto-PASS] |

Source/SQL/Compose có development-password defaults/literals: không viết “không hardcode secrets” chỉ vì dùng getenv. Không dump Config.Env/DSN/password công khai. App không bật debug tường minh chưa chứng minh effective environment; TESTING=True trong unit không là runtime debug. Routes không có auth trong source đọc: nêu giới hạn sample app, proxy auth nếu thực sự có evidence; không xây auth mới hoặc tự đánh dấu authorization PASS. SQL parameterization/source role grants không thay runtime enforcement proof.

Generic500/ready503 đúng expected contract có thể là case PASS khi có evidence, không tự là defect. Với curl, tách transport exit và HTTP400/503 expected. Nếu thấy bug, ghi reproduction/evidence redact gửi Thuận **trước**, không tự sửa implementation. Không bắt buộc tắt/restart DB hoặc lặp persistence nếu gây gián đoạn.

### F. Git và phối hợp trên GitHub

Trong repo nhóm, ghi `git status --short`, `git rev-parse HEAD`, môi trường và quyền sử dụng runtime; giữ dirty work. PR14 đã merge: viết report trên branch tài liệu riêng/branch đang làm phù hợp, không recreate PR14 hay copy reference code. Không cần fetch/merge một lab checkpoint. Phối hợp Thuận về scope runtime và evidence, Quang về staging boundaries; không chạm Ngân/Trâm.

Lưu observations vào thư mục run mới, không ghi đè evidence cũ; mỗi case có exact command, source/run/time, HTTP/body redacted và SHA256. Không stop/restart DB chung, chạy migrations/Compose/build/rollback hoặc down-v/prune trong task này. Nếu không có runtime riêng, dùng existing evidence đúng label và ghi NOT VERIFIED cho nhánh chưa được phép.

Điền `docs/report-input/TUYET.md` A–J trên repo nhóm: A source/branch; B–D implementation/architecture; E BSV methods/results; F bugs/status; G limits; H evidence-based contribution; I logs/links; J AI declaration cá nhân. Không sửa TEMPLATE/bao-cao.md hoặc viết kết luận thay người khác. Gửi PR tài liệu theo quy trình nhóm khi đã review.

### G. Kiểm thử và checklist hoàn thành

Trạng thái: PASS có observation/evidence đúng layer; FAIL có behavior không đáp ứng oracle; NOT VERIFIED là chưa đủ evidence/chưa chạy/bị chặn; NOT APPLICABLE phải có lý do. Không điền sẵn PASS ở bảng BSV.

Nếu cần thêm unit proof và môi trường đã có Flask/psycopg, từ `ma-nguon/order-app/` có thể chọn subset hiện có, không full Golden Lab:

~~~bash
PYTHONPATH=tests python -B -m unittest -v   test_app.OrderApiTestCase.test_missing_customer_name   test_app.OrderApiTestCase.test_invalid_quantity_values   test_app.OrderApiTestCase.test_malformed_json   test_app.OrderApiTestCase.test_get_orders_database_failure   test_app.OrderApiTestCase.test_create_order_database_failure   test_app.OrderApiTestCase.test_ready_connection_failure
~~~

Chỉ chạy khi các names tồn tại; đó là DB doubles. Full suite có hai DB thật nên không gọi discover khi chưa có isolated DB. Không bắt chạy lại tests đã có evidence đúng scope nếu không đổi source. Thiếu prerequisites ghi NOT VERIFIED, không cài thêm hệ thống bảo mật.

- [ ] BSV01–05 có observations hoặc lý do chưa xác minh, ghi từng subcase/layer.
- [ ] Source SHA/môi trường/URL/run/time và evidence rõ; sensitive values redact.
- [ ] Không nâng DB doubles/historical report thành current runtime PASS.
- [ ] Không gây gián đoạn DB chung hoặc tự sửa implementation; bugs báo Thuận.
- [ ] TUYET.md A–J có nội dung, limitations và AI declaration thật.

Hoàn thành nhiệm vụ thu evidence khi gửi đủ bảng+limits; còn NOT VERIFIED không được gọi nhánh runtime đó đã nghiệm thu. Không cần tất cả ô PASS mới bắt đầu viết báo cáo trong ngày.

### H. Bàn giao lại cho Thuận

~~~text
Người thực hiện / branch / PR URL:
Source SHA40 đã kiểm / base main SHA / ngày:
Contract: m4-contract-1.0 @ 9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d
Reference source publication SHA: 4c35990241e96f8d1d35de7e2615e12c55cf673b
Behavior đã đáp ứng (file:function + test/evidence):
Behavior còn thiếu hoặc chưa xác minh:
Khác biệt có chủ đích với reference và vì sao tương đương:
Dependency đang chờ owner khác (PR/SHA/API):
Command | exit | pass/fail/skip/error | unit/double/actual/runtime:
Evidence relative path/link + hash + source/run/artifact identity:
Giới hạn runtime / thông tin thiếu:
Việc Thuận cần kiểm khi tích hợp:
~~~

Không gửi credentials/private keys hoặc tự xác nhận approval. Chỉ commit/push branch thuộc mình theo quy trình nhóm khi đã review; không merge main thay nhóm.

Bổ sung bảng BSV01–05, quyền dùng môi trường, source/image identity nếu biết, phần đã điền TUYET.md và phần chờ Thuận xác nhận. Đây là basic backend verification, không security gate mới hoặc full M4 acceptance.

