import os
from datetime import datetime, timezone
from contextlib import contextmanager

from sqlalchemy import Column, Float, Integer, Text, create_engine, delete, select, update
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

from app_logger import get_logger
from paths import db_path
from utiles import build_video_display_title


logger = get_logger()
Base = declarative_base()


class FavoriteModel(Base):
	__tablename__ = "favorite"

	id = Column(Integer, primary_key=True)
	title = Column(Text, nullable=False)
	display_title = Column(Text, nullable=False)
	url = Column(Text, nullable=False)
	is_live = Column(Integer, nullable=False)
	channel_name = Column(Text, nullable=False)
	channel_url = Column(Text, nullable=False)


class ContinueModel(Base):
	__tablename__ = "continue"

	id = Column(Integer, primary_key=True)
	url = Column(Text, nullable=False)
	position = Column(Float, nullable=False)


class ViewHistoryModel(Base):
	__tablename__ = "view_history"

	id = Column(Integer, primary_key=True)
	title = Column(Text, nullable=False)
	display_title = Column(Text, nullable=False)
	url = Column(Text, nullable=False)
	views = Column(Text, nullable=True)
	upload_date = Column(Text, nullable=True)
	channel_name = Column(Text, nullable=True)
	channel_url = Column(Text, nullable=True)
	played_at = Column(Text, nullable=False)


def db_init():
	try:
		logger.info("Opening database. path=%s", db_path)
		os.makedirs(os.path.dirname(db_path), exist_ok=True)
		return create_engine(
			URL.create("sqlite", database=db_path),
			connect_args={"check_same_thread": False, "timeout": 30},
			future=True,
		)
	except Exception:
		logger.exception("Could not open database. path=%s", db_path)
		return None


def is_valid(function):
	def rapper(*args, **kwargs):
		if con is not None:
			return function(*args, **kwargs)
	return rapper


@contextmanager
def session_scope():
	session = Session()
	try:
		yield session
		session.commit()
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()


@is_valid
def prepare_tables():
	logger.info("Preparing database tables")
	Base.metadata.create_all(con)


@is_valid
def disconnect():
	logger.info("Closing database")
	con.dispose()


class Favorite:
	@is_valid
	def add_favorite(self, data):
		with session_scope() as session:
			session.add(FavoriteModel(
				title=data["title"],
				display_title=data["display_title"],
				url=data["url"],
				is_live=data["live"],
				channel_name=data["channel_name"],
				channel_url=data["channel_url"],
			))

	@is_valid
	def remove_favorite(self, url):
		with session_scope() as session:
			session.execute(delete(FavoriteModel).where(FavoriteModel.url == url))

	@is_valid
	def get_all(self):
		with session_scope() as session:
			rows = session.execute(
				select(
					FavoriteModel.title,
					FavoriteModel.display_title,
					FavoriteModel.url,
					FavoriteModel.is_live,
					FavoriteModel.channel_name,
					FavoriteModel.channel_url,
				)
			).all()
		return [
			{
				"title": title,
				"display_title": display_title,
				"url": url,
				"live": live,
				"channel_name": channel_name,
				"channel_url": channel_url,
			}
			for title, display_title, url, live, channel_name, channel_url in rows
		]


class Continue:
	@classmethod
	@is_valid
	def new_continue(self, url, position):
		with session_scope() as session:
			session.add(ContinueModel(url=url, position=position))

	@classmethod
	@is_valid
	def get_all(self):
		with session_scope() as session:
			rows = session.execute(select(ContinueModel.url, ContinueModel.position)).all()
		return {url: position for url, position in rows}

	@classmethod
	@is_valid
	def update(self, url, position):
		with session_scope() as session:
			session.execute(
				update(ContinueModel)
				.where(ContinueModel.url == url)
				.values(position=position)
			)

	@classmethod
	@is_valid
	def remove_continue(self, url):
		with session_scope() as session:
			session.execute(delete(ContinueModel).where(ContinueModel.url == url))


class ViewHistory:
	@is_valid
	def add(self, data):
		played_at = datetime.now(timezone.utc).isoformat()
		title = data.get("title") or data.get("display_title") or data.get("url")
		views = data.get("views")
		upload_date = data.get("upload_date")
		channel_name = data.get("channel_name")
		channel_url = data.get("channel_url")
		display_title = build_video_display_title(
			title,
			channel_name or "",
			views or "",
			upload_date or "",
			played_at,
		)
		with session_scope() as session:
			existing_rows = session.execute(
				select(ViewHistoryModel)
				.where(ViewHistoryModel.url == data["url"])
				.order_by(ViewHistoryModel.id.desc())
			).scalars().all()
			if existing_rows:
				row = existing_rows[0]
				row.title = title
				row.display_title = display_title
				row.views = views
				row.upload_date = upload_date
				row.channel_name = channel_name
				row.channel_url = channel_url
				row.played_at = played_at
				for duplicate in existing_rows[1:]:
					session.delete(duplicate)
			else:
				session.add(ViewHistoryModel(
					title=title,
					display_title=display_title,
					url=data["url"],
					views=views,
					upload_date=upload_date,
					channel_name=channel_name,
					channel_url=channel_url,
					played_at=played_at,
				))

	@is_valid
	def remove(self, history_id):
		with session_scope() as session:
			url = session.execute(
				select(ViewHistoryModel.url).where(ViewHistoryModel.id == history_id)
			).scalar_one_or_none()
			if url is None:
				session.execute(delete(ViewHistoryModel).where(ViewHistoryModel.id == history_id))
			else:
				session.execute(delete(ViewHistoryModel).where(ViewHistoryModel.url == url))
				session.execute(delete(ContinueModel).where(ContinueModel.url == url))

	@is_valid
	def clear(self):
		with session_scope() as session:
			urls = session.execute(select(ViewHistoryModel.url)).scalars().all()
			session.execute(delete(ViewHistoryModel))
			if urls:
				session.execute(delete(ContinueModel).where(ContinueModel.url.in_(urls)))

	@is_valid
	def get_all(self):
		with session_scope() as session:
			rows = session.execute(
				select(
					ViewHistoryModel.id,
					ViewHistoryModel.title,
					ViewHistoryModel.display_title,
					ViewHistoryModel.url,
					ViewHistoryModel.views,
					ViewHistoryModel.upload_date,
					ViewHistoryModel.channel_name,
					ViewHistoryModel.channel_url,
					ViewHistoryModel.played_at,
				).order_by(ViewHistoryModel.played_at.desc())
			).all()
		history = []
		seen_urls = set()
		for history_id, title, display_title, url, views, upload_date, channel_name, channel_url, played_at in rows:
			if url in seen_urls:
				continue
			seen_urls.add(url)
			history.append({
				"id": history_id,
				"title": title,
				"display_title": build_video_display_title(title, channel_name, views, upload_date, played_at),
				"url": url,
				"views": views,
				"upload_date": upload_date,
				"channel_name": channel_name or "",
				"channel_url": channel_url or "",
				"played_at": played_at,
			})
		return history


con = db_init()
Session = sessionmaker(bind=con, future=True) if con is not None else None
prepare_tables()
