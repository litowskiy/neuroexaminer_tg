"""
Persistent storage for user-uploaded knowledge base materials.
Materials are stored as JSON files under user_data/{user_id}/materials.json
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

USER_DATA_DIR = Path("user_data")


def _user_dir(user_id: int) -> Path:
    p = USER_DATA_DIR / str(user_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _materials_file(user_id: int) -> Path:
    return _user_dir(user_id) / "materials.json"


def _load(user_id: int) -> list[dict]:
    f = _materials_file(user_id)
    if not f.exists():
        return []
    try:
        with open(f, encoding="utf-8") as fp:
            return json.load(fp)
    except (json.JSONDecodeError, OSError):
        return []


def _dump(user_id: int, materials: list[dict]) -> None:
    with open(_materials_file(user_id), "w", encoding="utf-8") as fp:
        json.dump(materials, fp, ensure_ascii=False, indent=2)


def save_material(user_id: int, name: str, text: str) -> dict:
    """Save a new material and return it."""
    materials = _load(user_id)
    material = {
        "id": str(uuid.uuid4()),
        "name": name,
        "text": text,
        "created_at": datetime.now().isoformat(),
        "char_count": len(text),
    }
    materials.append(material)
    _dump(user_id, materials)
    return material


def list_materials(user_id: int) -> list[dict]:
    """Return all materials for a user."""
    return _load(user_id)


def get_material(user_id: int, material_id: str) -> dict | None:
    """Return a material by ID, or None if not found."""
    for m in _load(user_id):
        if m["id"] == material_id:
            return m
    return None


def delete_material(user_id: int, material_id: str) -> bool:
    """Delete a material by ID. Returns True if deleted."""
    materials = _load(user_id)
    new = [m for m in materials if m["id"] != material_id]
    if len(new) == len(materials):
        return False
    _dump(user_id, new)
    return True
