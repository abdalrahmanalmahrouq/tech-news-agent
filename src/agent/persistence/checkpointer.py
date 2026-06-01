import os

def get_db_path():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, "data", "checkpoints.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path