import pytest

from scripts.migrate import MigrationError, discover, pending


def write(directory, name, sql="SELECT 1;"):
    (directory / name).write_text(sql, encoding="utf-8")


def test_discover_orders_by_version(tmp_path):
    write(tmp_path, "V0002__second.sql")
    write(tmp_path, "V0001__first.sql")

    assert [m.version for m in discover(tmp_path)] == ["0001", "0002"]


@pytest.mark.parametrize(
    "name",
    ["0001__DDL__old_style.sql", "V1__short.sql", "V0001__CamelCase.sql", "V0001_one_underscore.sql"],
)
def test_discover_rejects_bad_names(tmp_path, name):
    write(tmp_path, name)

    with pytest.raises(MigrationError, match="fora do padrão"):
        discover(tmp_path)


def test_discover_rejects_repeated_version(tmp_path):
    write(tmp_path, "V0001__a.sql")
    write(tmp_path, "V0001__b.sql")

    with pytest.raises(MigrationError, match="repetida"):
        discover(tmp_path)


def test_pending_returns_everything_on_empty_db(tmp_path):
    write(tmp_path, "V0001__a.sql")

    assert [m.version for m in pending(discover(tmp_path), {})] == ["0001"]


def test_pending_skips_applied(tmp_path):
    write(tmp_path, "V0001__a.sql")
    write(tmp_path, "V0002__b.sql")
    first, _ = discover(tmp_path)

    result = pending(discover(tmp_path), {"0001": first.checksum})

    assert [m.version for m in result] == ["0002"]


def test_pending_nothing_when_all_applied(tmp_path):
    write(tmp_path, "V0001__a.sql")
    applied = {m.version: m.checksum for m in discover(tmp_path)}

    assert pending(discover(tmp_path), applied) == []


def test_pending_fails_when_applied_migration_changed(tmp_path):
    write(tmp_path, "V0001__a.sql")
    applied = {m.version: m.checksum for m in discover(tmp_path)}
    write(tmp_path, "V0001__a.sql", "SELECT 2;")

    with pytest.raises(MigrationError, match="mudou depois de aplicada"):
        pending(discover(tmp_path), applied)


def test_pending_fails_when_applied_migration_is_missing(tmp_path):
    write(tmp_path, "V0002__b.sql")

    with pytest.raises(MigrationError, match="não está no disco"):
        pending(discover(tmp_path), {"0001": "abc"})
