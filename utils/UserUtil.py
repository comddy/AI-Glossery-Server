import hashlib
import time
import uuid


# 生成唯一标识
def generate_hex_id():
    return hashlib.sha256(str(time.time()).encode() + uuid.uuid4().bytes).hexdigest()[:16]