# TASK M4 — Huỳnh Hồng Ánh Tuyết

## A. Mục tiêu cá nhân

**Vai trò:** Backend Security Verification — Existing Orders API, PostgreSQL & Readiness.

Thu thập đủ evidence và giới hạn về an toàn cơ bản của backend hiện tại để viết báo cáo trong ngày. Ưu tiên tests/logs sẵn có, chỉ bổ sung requests nhỏ được phép. Không xây auth/JWT, scanner/WAF/pentest framework, thay architecture/gate, chạy staging/rollback hoặc full Golden Lab.

## B. Chuẩn bị môi trường và clone reference

1. Bạn chỉ cần TASK này, HANDOFF của mình và contract/repo chính thức; không cần TASK của người khác.
2. Clone repository tham chiếu **Private** ở thư mục riêng. Nếu403/404, nhờ Thuận cấp quyền đọc, không đổi sang tài khoản/organization khác hoặc dùng token trong URL.

```bash
git clone https://github.com/dec2609/m4-golden-lab-reference.git m4-golden-lab-reference
```

- Publication commit: `31fdb6e8fc51a08aa94e8d9d386cb970019676fc`.
- Source/evidence reference commit: `4c35990241e96f8d1d35de7e2615e12c55cf673b`.
- Contract **m4-contract-1.0**: commit `9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d` tại [PR17](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/pull/17).
- Repository chính thức: [https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental).

**Golden Lab là kho tham khảo, không phải nơi sửa/nộp implementation. Không push code của bạn vào Golden Lab.** Candidate SHA local cũ không thay main của nhóm; không copy cả candidate, không cherry-pick assembled commit hoặc áp nguyên owner patch. So behavior với code hiện tại, giữ phần đã hoàn thành có evidence tương đương. Helpers/tests có thể khác tên.

3. Mở checkout repo nhóm **khác** với reference. Nếu chưa có checkout, clone repo nhóm vào thư mục mới; không clone đè thư mục đang có. Kiểm remote/status/branch/HEAD trước sửa. Commands dưới dùng Bash/Git Bash; ghi môi trường thực tế, không chạy chúng trong clone reference.
4. Với Tuyết, chỉ đối chiếu phần Orders/readiness và giới hạn liên quan; tài liệu dưới đây là nguồn tra cứu, không yêu cầu triển khai release pipeline. Có thể viết báo cáo ngay dù phần gate còn pending. Xem [contract](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/CONTRACT.md), [schema](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/SCHEMA.md), [workflow](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/WORKFLOW.md), [acceptance](https://github.com/UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental/blob/9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d/docs/m4-contract/ACCEPTANCE.md). Contract là chuẩn bắt buộc; implementation reference chỉ là ví dụ.

## C. Những file cần đọc

Trước hết đọc [HANDOFF-TUYET.md](https://github.com/dec2609/m4-golden-lab-reference/blob/31fdb6e8fc51a08aa94e8d9d386cb970019676fc/M4-TEAM-HANDOFF/HANDOFF-TUYET.md) của mình. Sau đó đọc các mục sau tại source/evidence pin; không cần xin đường dẫn máy local của Thuận.

| File tại reference | Cần lấy thông tin gì |
|---|---|
| [candidate/ma-nguon/order-app/app.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/ma-nguon/order-app/app.py) | GET /health, /ready, GET/POST /orders; validation/error/env config. |
| [candidate/ma-nguon/order-app/tests/test_app.py](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/ma-nguon/order-app/tests/test_app.py) | DB doubles và các tests cần DB thật; không đánh đồng. |
| [candidate/ma-nguon/order-app/Dockerfile](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/ma-nguon/order-app/Dockerfile) | Startup/debug/user assumptions. |
| [candidate/docker-compose.yml](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/docker-compose.yml) | Runtime service/ports/environment/volumes tham khảo. |
| [candidate/ma-nguon/database/001-init.sql](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/ma-nguon/database/001-init.sql) | Orders schema đã có, không yêu cầu migration mới. |
| [candidate/ma-nguon/database/002-runtime-role.sql](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/candidate/ma-nguon/database/002-runtime-role.sql) | Dedicated runtime role/permissions tham khảo. |
| [evidence/final-backend.json](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/final-backend.json) | Selected18 DB-double tests tại lab SHA, không actual PG proof. |
| [evidence/final-backend.log](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/final-backend.log) | Historical test log, không kết quả vừa chạy. |
| [evidence/backend-author-report.md](https://github.com/dec2609/m4-golden-lab-reference/blob/4c35990241e96f8d1d35de7e2615e12c55cf673b/evidence/backend-author-report.md) | Owner runtime report cũ; cần raw evidence/source/date nếu tái sử dụng. |

Các source paths trong cột đầu bỏ tiền tố `candidate/` là path đích trong repo nhóm khi tương ứng đã có. Patches không là file phải đưa vào implementation PR. Reference evidence là lịch sử, không kết quả đã chạy trên branch bạn. Source pin và publication SHA nêu trên bất biến; current main có thể đã thay đổi.

## D. Công việc cần thực hiện theo thứ tự

### D.1. Ghi baseline và chọn evidence trước

**Thực hiện:** Xác nhận SHA/môi trường/backend URL đang được phép dùng; đối chiếu source thật của mình với các endpoints/rules reference. Chọn logs có sẵn đúng scope, ghi historical hoặc current rõ.

**Đầu ra để chuyển bước:** Bảng baseline; danh sách case có evidence và case chưa được phép/chưa có môi trường.

### D.2. BSV-01 — Valid request

**Thực hiện:** Trên runtime riêng được phép ghi, POST JSON {customer_name,product_name,quantity:1} rồi GET readback theo ID; chỉ dùng nhãn synthetic BSV. Source reference mong201/200; kiểm actual response. Nếu môi trường chung, xin phép trước POST hoặc trích evidence hợp lệ.

**Đầu ra để chuyển bước:** Exact command, HTTP/body/ID/run/source; không giả PASS từ source hoặc DB-double test.

### D.3. BSV-02 — Invalid input

**Thực hiện:** Chọn đại diện: thiếu customer_name, quantity string/bool,0 hoặc2147483648, malformed JSON. Rules reference: strings không trắng, integer1..2147483647, bool bị từ chối; JSON object required. Đối chiếu code hiện tại trước dùng oracle, không fuzzing lớn.

**Đầu ra để chuyển bước:** Từng request/status/body và expected vs observed; dự kiến400 theo source không là kết quả đã chạy.

### D.4. BSV-03 — Error exposure

**Thực hiện:** Đọc generic error handlers và tests DB exception, quan sát error responses an toàn. Tìm traceback/DSN/credentials/internal details; không cố gây lỗi môi trường chung. Có thể chỉ dùng DB-double proof và ghi thiếu actual error-response verification.

**Đầu ra để chuyển bước:** Response/log đã redact và layer; generic500 đúng expected không tự là defect, không dump env/secrets.

### D.5. BSV-04 — Readiness/PostgreSQL

**Thực hiện:** GET /ready khi ready; không dùng /health200 thay DB readiness. Reference /ready200 với ready/database connected,503 với unready/database unreachable. Ưu tiên outage/recovery logs có sẵn; chỉ stop/restart DB riêng khi đã được phép, không bắt buộc gây outage.

**Đầu ra để chuyển bước:** Healthy/outage/recovery ghi riêng và source/time/identity; nhánh chưa kiểm ghi NOT_VERIFIED, không dựng stack mới.

### D.6. BSV-05 — Security configuration

**Thực hiện:** Đọc current app/Dockerfile/Compose/SQL: env mechanism, dev-password defaults/literals, effective debug/startup, runtime-role/auth assumptions. getenv không chứng minh không hardcode secrets; TESTING=True không là production debug. Auth chưa có phải công khai giới hạn, không tự xây thêm.

**Đầu ra để chuyển bước:** Static observations dẫn file:function@SHA; runtime env chưa biết ghi rõ; không in Config.Env/DSN/password.

### D.7. Tổng hợp và báo lỗi trước khi sửa

**Thực hiện:** Lập bảng BSV01–05, gắn evidence, phân loại PASS/FAIL/NOT_VERIFIED/NOT_APPLICABLE. Bug thật báo Thuận với reproduction; chỉ sửa sau khi được xác nhận scope. Điền TUYET.md ngay, không chờ pipeline.

**Đầu ra để chuyển bước:** Báo cáo ngắn đủ viết backend verification; không yêu cầu mọi runtime case PASS.

## E. Kiểm thử và evidence

Mỗi BSV có mục tiêu/oracle, exact command, actual HTTP/body/log, source/run/time, file/hash và layer. PASS có execution/evidence phù hợp; FAIL là behavior không đạt oracle; NOT_VERIFIED là chưa đủ chứng cứ/chưa được phép; NOT_APPLICABLE phải có lý do. DB-double exception tests không chứng minh PG runtime/persistence/recovery. Source có20 methods nhưng historical lab chỉ chạy18 selected, không lấy count nguồn làm test result. /health không kiểm DB. Curl transport exit và expected HTTP400/503 cần ghi riêng; không coi expected negative status là unexpected failure.

**Lệnh chọn lọc khi thực sự cần xác minh hoặc sau thay đổi:**

```bash
# Từ ma-nguon/order-app/, chỉ nếu dependencies đã có và các tests tồn tại:
PYTHONPATH=tests python -B -m unittest -v \
  test_app.OrderApiTestCase.test_missing_customer_name \
  test_app.OrderApiTestCase.test_invalid_quantity_values \
  test_app.OrderApiTestCase.test_malformed_json \
  test_app.OrderApiTestCase.test_get_orders_database_failure \
  test_app.OrderApiTestCase.test_ready_connection_failure
```

Không chạy lại suite đã có log đúng SHA nếu không đổi code hoặc còn concern chưa giải quyết. Kiểm tên tests tồn tại trước khi gọi; thiếu evidence thì ghi NOT_VERIFIED và gửi Thuận, không tự viết thêm tests hoặc sửa code trong task này. Không cần port harness Golden Lab, chạy tests/contracts hay ép count giống sandbox. Không sửa assertions/xóa tests để che lỗi.

| Case / ID | Mục tiêu và oracle | Command / môi trường | Actual exit / HTTP / counts | Layer | Evidence / source SHA / run / hash | Verdict / limit |
|---|---|---|---|---|---|---|
| [Bạn điền] | | | | static / unit / contract / double / actual runtime | | PASS / FAIL / NOT_VERIFIED / NOT_APPLICABLE |

Giữ raw evidence cũ; run mới/output/cache ngoài measured source khi contract yêu cầu. Không ghi secret/private key/DSN thật vào log công bố. Golden Lab historical255/17/68/18 hoặc expected negative block không chứng minh current release positive, CI hoặc full M4 PASS. Không chạy full Golden Lab trong task này.

## F. Git/PR trên repository chính thức

Trong checkout **repo nhóm**:

```bash
git remote -v
git status --short
git branch --show-current
git rev-parse HEAD
# Chỉ đồng bộ refs trong checkout của mình khi đã kiểm remote:
git fetch origin main
```

Origin phải trỏ `UEH-CSS-26C/CSS-26C-N08-SaiGon-Continental`, không phải `dec2609/m4-golden-lab-reference`. Dirty/untracked chưa bảo toàn thì dừng mutation hoặc dùng checkout sạch; không reset/clean/force-push, không ghi đè commits hiện có. Fetch không tự merge. Đối chiếu source/API của đúng SHA đang kiểm; Tuyết không đổi contract/interface và không phải chờ contract conformance để bắt đầu viết report input. Nếu thấy khác biệt ảnh hưởng oracle, ghi lại cho Thuận xác nhận.

PR14 đã merge theo handoff snapshot. Task mặc định là evidence/tài liệu: dùng branch tài liệu phù hợp từ main hoặc branch đang có và mở PR vào repo nhóm. Chỉ sửa docs/report-input/TUYET.md và evidence đã được thống nhất; không overwrite report chính hoặc source. Nếu phát hiện bug, gửi Thuận trước; PR sửa lỗi tách riêng chỉ sau khi Thuận xác nhận cần thiết. Không tự port backend reference.

Review diff/file list và stage explicit paths thuộc mình trước commit/push. PR vào **repo nhóm** có source SHA, tests/evidence/limits và shared changes cần owner review. Không merge main, không push/mời cộng tác vào repo tham chiếu. Mọi thay đổi implementation chính thức nằm ở repo nhóm, không trong clone Golden Lab.

## G. Báo cáo cá nhân A–J

Hoàn thiện **`docs/report-input/TUYET.md`** trong repository nhóm, có thể viết song song với các bước kỹ thuật. Không thay `TEMPLATE.md`, file của người khác hoặc `docs/bao-cao.md`; Thuận tổng hợp báo cáo chính sau.

| Mục | Nội dung bạn phải điền |
|---|---|
| A | Họ tên/vai trò, branch/PR, source SHA40, trạng thái implementation và ngày/môi trường |
| B | 100–150 từ: vấn đề phần mình giải quyết, input/output và ranh giới đóng góp |
| C | Thiết kế/module/công cụ và interfaces thực sự có; tách phần dự kiến |
| D | File:function, quyết định và commit triển khai/review/integration; không nhận công của merge toàn bộ code |
| E | Methods, positive/negative cases, commands/exits/counts/HTTP, actual observations và evidence đúng SHA/layer |
| F | Triệu chứng, nguyên nhân, xử lý, verification sau sửa hoặc trạng thái còn mở |
| G | Giới hạn môi trường/coverage/runtime và hướng cải tiến; không biến proposal thành implemented |
| H | 100–150 từ kết luận đóng góp cá nhân có căn cứ, không tự kết luận full M4 READY |
| I | PR/commit/source/log/report/screenshot links, source/run/time và hashes khi có |
| J | AI/LLM thực sự dùng, mục đích/phần hỗ trợ, quyết định của mình/cách kiểm đầu ra, người khai/ngày/xác nhận; không điền giả |

PASS chỉ khi có evidence; thiếu dữ liệu ghi rõ NOT_VERIFIED/NOT_RUN/BLOCKED theo mẫu, không bịa kết quả. Không yêu cầu sửa code chỉ để có nội dung báo cáo. Evidence ngoài repo cần link nhóm đọc được, không chỉ absolute path máy cá nhân.

## H. Tiêu chí hoàn thành và mẫu phản hồi cho Thuận

- [ ] Bảng BSV01–05 có observations hoặc lý do chưa xác minh cụ thể, evidence và limits đủ viết báo cáo.
- [ ] Không làm gián đoạn DB chung; không tạo security feature/gate/framework hoặc tự sửa implementation.
- [ ] Không nâng historical/DB-double logs thành current PG/runtime PASS; không bắt mọi case PASS.
- [ ] TUYET.md A–J và PR tài liệu đã bàn giao; bug nếu có chờ Thuận quyết định scope.

**Đầu ra bắt buộc:** branch/PR repo nhóm (PR code nếu có thay đổi cần thiết), source SHA đã kiểm, test commands/counts/exits, evidence paths/hashes, behavior đã đáp ứng/còn thiếu, dependency owner/PR/SHA và report input A–J. Không làm lại phần đã chứng minh tương đương chỉ để khớp reference.

```text
Người thực hiện:
Repository nhóm / Branch / PR URL:
HEAD40 đã test / main base / ngày:
Contract: m4-contract-1.0 @ 9f1469f64d6a9ae8d5ef4b2758e878a2dfed5e1d
Reference publication: 31fdb6e8fc51a08aa94e8d9d386cb970019676fc
Reference source/evidence: 4c35990241e96f8d1d35de7e2615e12c55cf673b
Các bước D đã hoàn thành và file:function/commit tương ứng:
Behavior đã có từ trước và evidence tái sử dụng:
Behavior còn thiếu / khác reference có chủ đích:
Command | exit/HTTP | pass/fail/skip/error | layer:
Evidence paths + source/run/time/hash; redaction:
Dependency chờ ai, PR/SHA/API/input cụ thể:
NOT_VERIFIED/NOT_APPLICABLE/NOT_RUN và lý do:
Report input docs/report-input/TUYET.md A–J đã điền / phần còn thiếu:
Việc Thuận cần kiểm khi tích hợp / bug cần quyết định:
```

Task completion chỉ áp dụng phạm vi đã kiểm và evidence đã bàn giao; **không tự là nghiệm thu full runtime M4 hoặc production-ready**.
