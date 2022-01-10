import sqlite3 as sql
from paths import db_path
import os

def db_init():
	try:
		con = sql.connect(db_path)
	except Exception as e:
		print(e)
		con = None
	return con


def is_valid(function):
	def rapper(*args, **kwargs):
		if con is not None:
			return function(*args, **kwargs)
	return rapper

@is_valid
def prepare_tables():
	favorites_query = """create table if not exists favorite (id integer primary key, title text not null, display_title text not null, url text not null, is_live integer not null, channel_name text not null, channel_url not null)"""
	con.execute(favorites_query)
	con.commit()
	continue_quiry = "create table if not exists continue (id integer primary key, url text not null, position real not null)"
	con.execute(continue_quiry)
	con.commit()

@is_valid
def disconnect():
	con.close()

class Favorite:
	@is_valid
	def add_favorite(self, data):
		query = f"""insert into favorite (title, display_title, url, is_live, channel_name, channel_url) 
values ("{data['title']}", "{data['display_title']}" ,"{data['url']}", {data['live']}, "{data['channel_name']}", "{data['channel_url']}")"""
		con.execute(query)
		con.commit()

	@is_valid
	def remove_favorite(self, url):
		con.execute(f'delete from favorite where url="{url}"')
		con.commit()
	@is_valid
	def get_all(self):
		cursor = con.execute("select title, display_title, url, is_live, channel_name, channel_url from favorite").fetchall()
		data = []
		for title, display_title, url, live, channel_name, channel_url in cursor:
			row = {
				"title": title,
				"display_title": display_title,
				"url": url,
				"live": live,
				"channel_name": channel_name,
				"channel_url": channel_url
			}
			data.append(row)
		return data


class Continue:
	@classmethod
	@is_valid
	def new_continue(self, url, position):
		quiry = f"""insert into continue (url, position)
values ("{url}", {position})"""
		con.execute(quiry)
		con.commit()
	@classmethod
	@is_valid
	def get_all(self):
		cursor = con.execute("select url, position from continue").fetchall()
		data = {}
		for url, position in cursor:
			data[url] = position
		return data

	@classmethod
	@is_valid
	def update(self, url, position):
		quiry = f"""update continue 
set position={position} where url="{url}"
"""
		con.execute(quiry)
		con.commit()

	@classmethod
	@is_valid
	def remove_continue(self, url):
		con.execute(f'delete from continue where url="{url}"')
		con.commit()


con = db_init()
prepare_tables()