import json
import zipfile
from io import BytesIO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.operations import create_backup_export


def test_backup_export_contains_manifest_and_table_snapshots() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        seed_default_accounts(db)

        filename, content = create_backup_export(db)

    assert filename.startswith("intelliartai-bookkeeping-export-")
    assert filename.endswith(".zip")
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "README.txt" in names
        assert "data/accounts.json" in names
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        accounts = json.loads(archive.read("data/accounts.json").decode("utf-8"))

    assert manifest["format"] == "json-table-export-v1"
    assert any(table["name"] == "accounts" and table["rows"] == len(accounts) for table in manifest["tables"])
    assert any(account["code"] == "1010" for account in accounts)
