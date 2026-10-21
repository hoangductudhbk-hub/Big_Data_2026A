"""
NHÃN DO NGƯỜI KIỂM TRA (ground truth) dùng để đánh giá record linkage.

Tiêu chí gán nhãn "cùng một tên đường":
  - Chỉ khác lỗi chính tả (thiếu/thừa/đảo ký tự) hoặc khoảng trắng.
  - KHÁC con số (40 STREET ≠ 90 STREET), KHÁC hướng (EAST 117 ≠ WEST 117), KHÁC tầng (UPPER ≠ LOWER),
    KHÁC bang (NJ ≠ NY), hoặc là 2 tên thật khác nhau (ARDEN ≠ BORDEN) → KHÔNG cùng.

Quy trình: liệt kê mọi cặp có Levenshtein similarity ≥ 0,75 trên 373 tên (sau chuẩn hóa ở bước 08),
người kiểm tra đọc từng cặp và đánh dấu các cặp dưới đây là đúng. Mọi cặp còn lại trong danh sách là sai.
"""

TRUE_NAME_PAIRS = [
    ("BLOOMINGDALE ROAD", "BLOOMUINGDALE ROAD"),
    ("BLLOMINGDALE ROAD", "BLOOMINGDALE ROAD"),
    ("BLLOMINGDALE ROAD", "BLOOMUINGDALE ROAD"),
    ("WALKER STREET", "WLAKER STREET"),
    ("DE KALB AVENUE", "DEKALB AVENUE"),
]

# Cặp (đoạn đếm lưu lượng, tuyến tốc độ) là CÙNG một đoạn đường — kiểm tra bằng tên + bản đồ
TRUE_ROAD_LINKS = [
    ("136811", "4616332"),   # FDR DRIVE  ↔  FDR S 63RD - 25TH ST              (cách 4,7 m)
    ("66035", "4616232"),    # BROOKLYN QUEENS EXPWY ET 34 WB ↔ BQE S 46TH STREET - LEONARD STREET (11,6 m)
]
