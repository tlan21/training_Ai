"""Sinh AI_SERVICE_KEY format sk-local-... — chạy: python -m app.gen_key

Key là chuỗi bí mật ngẫu nhiên (KHÔNG phải JWT, không hết hạn). Đặt cùng giá trị
ở env inference-service và gateway. Đổi key = revoke: mọi request cũ 401.
"""

import secrets


def generate_key() -> str:
    return "sk-local-" + secrets.token_urlsafe(32)


if __name__ == "__main__":
    print(generate_key())
