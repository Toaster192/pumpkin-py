from __future__ import annotations
from typing import Optional

from sqlalchemy import Column, BigInteger, Boolean, DateTime, ARRAY
from sqlalchemy.sql import func

from pie.database import database, session


class History(database.base):
    __tablename__ = "cetge_history"

    user_ids = Column(ARRAY(BigInteger), primary_key=True)
    u1_blocked = Column(Boolean, default=False)
    u2_blocked = Column(Boolean, default=False)
    last_matched = Column(DateTime, default=func.now())

    @staticmethod
    def add(user_id1: int, user_id2: int) -> History:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = History(
            user_id1=user_id1,
            user_id2=user_id2,
        )
        session.add(query)
        session.commit()
        return query

    def update(self):
        self.last_matched = func.now()

    @staticmethod
    def get(user_id1: int, user_id2: int) -> Optional[History]:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = (
            session.query(History)
            .filter_by(
                user_id1=user_id1,
                user_id2=user_id2,
            )
            .one_or_none()
        )
        return query

    @staticmethod
    def remove(user_id1: int, user_id2: int) -> int:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = (
            session.query(History)
            .filter_by(
                user_id1=user_id1,
                user_id2=user_id2,
            )
            .delete()
        )
        return query

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} user_id1="{self.user_id1}" '
            f'user_id2="{self.user_id2}" u1_blocked="{self.u1_blocked}" '
            f'u2_blocked="{self.u2_blocked}" last_matched="{self.last_matched}">'
        )

    def dump(self) -> dict:
        return {
            "user_id1": self.user_id1,
            "user_id2": self.user_id2,
            "u1_blocked": self.u1_blocked,
            "u2_blocked": self.u2_blocked,
            "last_matched": self.last_matched,
        }


class Match(database.base):
    __tablename__ = "cetge_match"

    user_id1 = Column(BigInteger, primary_key=True)
    user_id2 = Column(BigInteger, primary_key=True)

    @staticmethod
    def add(user_id1: int, user_id2: int) -> History:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = Match(
            user_id1=user_id1,
            user_id2=user_id2,
        )
        session.add(query)
        session.commit()
        return query

    @staticmethod
    def get_all():
        query = session.query(History).all()
        return query

    @staticmethod
    def get(user_id1: int, user_id2: int) -> Optional[History]:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = (
            session.query(History)
            .filter_by(
                user_id1=user_id1,
                user_id2=user_id2,
            )
            .one_or_none()
        )
        return query

    @staticmethod
    def remove(user_id1: int, user_id2: int) -> int:
        user_id1, user_id2 = sorted([user_id1, user_id2])
        query = (
            session.query(History)
            .filter_by(
                user_id1=user_id1,
                user_id2=user_id2,
            )
            .delete()
        )
        return query

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} user_id1="{self.user_id1}" '
            f'user_id2="{self.user_id2}" '
        )

    def dump(self) -> dict:
        return {
            "user_id1": self.user_id1,
            "user_id2": self.user_id2,
        }
