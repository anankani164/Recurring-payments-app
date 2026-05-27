from datetime import datetime, timedelta

from app.main import acquire_distributed_lock, release_distributed_lock
from app.models import SchedulerLock


class DummyQueryResult:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value


class DummyDB:
    def __init__(self, lock=None):
        self.lock = lock
        self.added = None
        self.deleted = None

    def execute(self, _):
        return DummyQueryResult(self.lock)

    def add(self, obj):
        self.added = obj
        self.lock = obj

    def delete(self, obj):
        self.deleted = obj
        self.lock = None

    def commit(self):
        return None


def test_acquire_distributed_lock_new_lock():
    db = DummyDB()
    ok = acquire_distributed_lock(db, "embedded_worker", "owner-1", ttl_minutes=1)
    assert ok is True
    assert db.added is not None


def test_acquire_distributed_lock_active_lock_rejected():
    lock = SchedulerLock(name="embedded_worker", owner_id="owner-a", expires_at=datetime.utcnow() + timedelta(minutes=5))
    db = DummyDB(lock=lock)
    ok = acquire_distributed_lock(db, "embedded_worker", "owner-b", ttl_minutes=1)
    assert ok is False


def test_release_distributed_lock_owner_only():
    lock = SchedulerLock(name="embedded_worker", owner_id="owner-a", expires_at=datetime.utcnow() + timedelta(minutes=5))
    db = DummyDB(lock=lock)
    release_distributed_lock(db, "embedded_worker", "owner-a")
    assert db.deleted is not None

