"""场景包模块冒烟测试：TestClient 直连 app，不占端口。

覆盖：种子同步 → 注册/登录 → 列表 → 创建（校验失败/成功）→ validate →
导出 → 导入回环（覆盖/改名/旧包拒绝）→ 知识上传/分节 → 发布/统计互动 →
权限（builtin 只读、他人场景不可见）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ 注入 sys.path

import io
import json
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)  # startup 钩子会执行种子同步

# ---- 测试前置：清空场景相关表（用户表保留），保证脚本可重复执行 ----
from sqlalchemy import text

from app.core.database import engine

with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for table in ("chunks", "documents", "scene_stats", "scene_user_stats", "scenes"):
        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    conn.commit()

from app.core.database import Base

Base.metadata.create_all(bind=engine)
from app.scenes.registry import sync_seeds
from app.core.database import SessionLocal

with SessionLocal() as db:
    sync_seeds(db)


def check(name: str, cond: bool, extra: str = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + (f"  → {extra}" if extra and not cond else ""))
    assert cond, name


# ---- 游客列表（仅 builtin）----
r = client.get("/api/scenes")
check("游客列表仅内置", r.status_code == 200 and len(r.json()["items"]) == 4, r.text[:200])

# ---- 注册两个用户 ----
import random

suffix = random.randint(1000, 9999)
u1, u2 = f"alice{suffix}", f"bob{suffix}"
r1 = client.post("/api/auth/register", json={"username": u1, "password": "password1"})
r2 = client.post("/api/auth/register", json={"username": u2, "password": "password2"})
check("注册两个用户", r1.status_code == 201 and r2.status_code == 201, r1.text[:200])
t1, t2 = r1.json()["access_token"], r2.json()["access_token"]
auth1 = {"Authorization": f"Bearer {t1}"}
auth2 = {"Authorization": f"Bearer {t2}"}

# ---- 模板列表 + 从模板创建 ----
r = client.get("/api/scenes/templates")
check("模板列表 4 个", len(r.json()["items"]) == 4)
r = client.post("/api/scenes/from-template", json={"template_id": "cafe_ordering"}, headers=auth1)
check("从模板创建", r.status_code == 201 and r.json()["id"] == "cafe_ordering_custom", r.text[:200])

# ---- 校验失败：非法表达式 ----
bad = json.loads(json.dumps(client.get("/api/scenes/cafe_ordering").json()["package"]))
bad["meta"]["id"] = "bad_expr_scene"
bad["finish"]["when"] = "state.nonexistent == true"
r = client.post("/api/scenes/validate", json=bad, headers=auth1)
check("validate 拦截未声明 state 键", r.status_code == 422 and "nonexistent" in r.text, r.text[:300])

bad["finish"]["when"] = "state.confirmed == true and __import__('os').system('x') == 0"
r = client.post("/api/scenes/validate", json=bad, headers=auth1)
check("validate 拦截危险表达式", r.status_code == 422)

# ---- 创建自定义场景 ----
r = client.get("/api/scenes/cafe_ordering")
pkg = json.loads(json.dumps(r.json()["package"]))
pkg["meta"]["id"] = "my_flight"
pkg["meta"]["name"] = "我的航班沟通"
r = client.post("/api/scenes", json=pkg, headers=auth1)
check("创建自定义场景", r.status_code == 201 and r.json()["status"] == "private", r.text[:300])

# ID 冲突
r = client.post("/api/scenes", json=pkg, headers=auth1)
check("创建冲突 409", r.status_code == 409 and r.json()["error"]["code"] == "SCENE_ID_CONFLICT", r.text[:200])

# ---- 他人不可见私有场景；发布后可见 ----
r = client.get("/api/scenes/my_flight", headers=auth2)
check("他人私有场景不可见", r.status_code == 404)
r = client.post("/api/scenes/my_flight/publish", headers=auth1)
check("发布场景", r.status_code == 200 and r.json()["status"] == "published", r.text[:200])
r = client.get("/api/scenes/my_flight", headers=auth2)
check("发布后他人可见", r.status_code == 200)

# ---- 知识资料：上传 md → 分节 → 可见性 ----
md = "# Drinks\nLatte: $4.5\nMocha: $5.0\n\n# Staff Notes\nToday out of croissants."
r = client.post(
    "/api/scenes/my_flight/knowledge",
    files={"file": ("menu.md", md.encode(), "text/markdown")},
    params={"visibility": "user"},
    headers=auth1,
)
check("上传资料", r.status_code == 201 and r.json()["chunk_count"] >= 2, r.text[:200])
doc_id = r.json()["id"]
r = client.get("/api/scenes/my_flight/knowledge/sections", headers=auth1)
check("分节概览", r.status_code == 200 and len(r.json()["sections"]) >= 2, r.text[:200])
r = client.patch(
    "/api/scenes/my_flight/knowledge/sections/Staff Notes",
    json={"visibility": "ai_only"},
    headers=auth1,
)
check("修改分节可见性", r.status_code == 200 and r.json()["updated_chunks"] >= 1, r.text[:200])
r = client.get("/api/scenes/my_flight/knowledge")
check("学习者可见分节不含 ai_only", all(s["section"] != "Staff Notes" for s in r.json()["sections"]))
r = client.delete(f"/api/scenes/my_flight/knowledge/{doc_id}", headers=auth1)
check("删除资料", r.status_code == 200)

# 上传不支持的类型
r = client.post(
    "/api/scenes/my_flight/knowledge",
    files={"file": ("virus.exe", b"MZ...", "application/octet-stream")},
    headers=auth1,
)
check("拒绝不支持的文件类型", r.status_code == 400 and r.json()["error"]["code"] == "SCENE_UNSUPPORTED_FILE", r.text[:200])

# ---- 导出 → 导入回环 ----
r = client.get("/api/scenes/my_flight/export", headers=auth1)
check("导出 ZIP", r.status_code == 200 and r.headers["content-type"] == "application/zip")
zip_bytes = r.content
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    names = zf.namelist()
check("导出含 manifest + scene.yaml", "manifest.json" in names and "scene.yaml" in names, str(names))
check("导出不含向量索引", not any(n.endswith(".index") for n in names))

# 他人导入（改名）
r = client.post("/api/scenes/import?resolve=rename", files={"file": ("scene.zip", zip_bytes, "application/zip")}, headers=auth2)
check("他人导入改名", r.status_code == 200 and r.json()["action"] == "renamed" and r.json()["scene"]["id"].startswith("my_flight_"), r.text[:300])

# 再次导入无 resolve → 409
r = client.post("/api/scenes/import", files={"file": ("scene.zip", zip_bytes, "application/zip")}, headers=auth2)
check("导入冲突 409", r.status_code == 409 and r.json()["error"]["code"] == "SCENE_ID_CONFLICT")

# 他人覆盖他人场景 → 仍冲突（只能覆盖自己的）
r = client.post("/api/scenes/import?resolve=overwrite", files={"file": ("scene.zip", zip_bytes, "application/zip")}, headers=auth2)
check("他人覆盖他人场景仍冲突", r.status_code == 409 and r.json()["error"]["code"] == "SCENE_ID_CONFLICT")

# 作者覆盖导入
r = client.post("/api/scenes/import?resolve=overwrite", files={"file": ("scene.zip", zip_bytes, "application/zip")}, headers=auth1)
check("作者覆盖导入", r.status_code == 200 and r.json()["action"] == "overwritten", r.text[:200])

# 内置 ID 强制改名
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    data = json.loads(zf.read("scene.yaml").decode() if False else "{}")  # 占位，直接改包
import yaml as yaml_mod

with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    scene_data = yaml_mod.safe_load(zf.read("scene.yaml"))
scene_data["meta"]["id"] = "cafe_ordering"  # 顶撞内置 ID
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("scene.yaml", yaml_mod.safe_dump(scene_data, allow_unicode=True))
    zf.writestr("manifest.json", json.dumps({"format": "echotalk-scene", "version": 2, "scene_id": "cafe_ordering", "min_app": "2.0.0", "files": ["scene.yaml"], "checksums": {}}))
r = client.post("/api/scenes/import?resolve=overwrite", files={"file": ("x.zip", buf.getvalue(), "application/zip")}, headers=auth2)
check("内置 ID 拒绝覆盖 409", r.status_code == 409 and "内置" in r.json()["error"]["message"], r.text[:200])
r = client.post("/api/scenes/import?resolve=rename", files={"file": ("x.zip", buf.getvalue(), "application/zip")}, headers=auth2)
check("内置 ID 强制改名", r.status_code == 200 and r.json()["scene"]["id"].startswith("cafe_ordering_"), r.text[:300])

# 旧 1.0 包拒绝
old_buf = io.BytesIO()
with zipfile.ZipFile(old_buf, "w") as zf:
    zf.writestr("scene_config.json", json.dumps({"id": "legacy"}))
    zf.writestr("legacy.index", b"\x00\x01")
r = client.post("/api/scenes/import", files={"file": ("old.zip", old_buf.getvalue(), "application/zip")}, headers=auth2)
check("旧包拒绝 422", r.status_code == 422 and "1.0" in r.json()["error"]["message"], r.text[:200])

# ---- 点赞 / 收藏 / 下载统计 ----
r = client.post("/api/scenes/my_flight/like", headers=auth2)
check("点赞", r.status_code == 200 and r.json()["likes"] == 1 and r.json()["liked"] is True)
r = client.post("/api/scenes/my_flight/like", headers=auth2)
check("重复点赞去重", r.json()["likes"] == 0 and r.json()["liked"] is False)
r = client.post("/api/scenes/my_flight/favorite", headers=auth2)
check("收藏", r.json()["favorites"] == 1 and r.json()["favorited"] is True)
r = client.post("/api/scenes/cafe_ordering/like", headers=auth1)
check("内置场景可点赞", r.status_code == 200 and r.json()["likes"] == 1)

before = client.get("/api/scenes/my_flight", headers=auth2).json()["stats"]["downloads"]
client.get("/api/scenes/my_flight/export", headers=auth2)  # 他人导出 → 计数
after = client.get("/api/scenes/my_flight", headers=auth2).json()["stats"]["downloads"]
check("他人导出计入下载量", after == before + 1, f"{before} → {after}")
before_author = client.get("/api/scenes/my_flight", headers=auth1).json()["stats"]["downloads"]
client.get("/api/scenes/my_flight/export", headers=auth1)  # 作者导出 → 不计数
after_author = client.get("/api/scenes/my_flight", headers=auth1).json()["stats"]["downloads"]
check("作者导出不计下载量", after_author == before_author)

# ---- 权限：builtin 不可改删；他人场景不可改 ----
r = client.put("/api/scenes/cafe_ordering", json=pkg, headers=auth1)
check("builtin 只读 409", r.status_code == 409 and r.json()["error"]["code"] == "SCENE_BUILTIN_READONLY")
r = client.put("/api/scenes/my_flight", json=pkg, headers=auth2)
check("他人场景不可改 403/404", r.status_code in (403, 404))
r = client.delete("/api/scenes/cafe_ordering", headers=auth1)
check("builtin 不可删除", r.status_code == 409)

# 取消发布后他人不可见
r = client.post("/api/scenes/my_flight/unpublish", headers=auth1)
check("取消发布", r.status_code == 200)
r = client.get("/api/scenes/my_flight", headers=auth2)
check("取消发布后他人不可见", r.status_code == 404)

# ---- 删除自己的场景 ----
r = client.delete("/api/scenes/my_flight", headers=auth1)
check("删除自己的场景", r.status_code == 200)

print("\n全部冒烟通过 ✓")
