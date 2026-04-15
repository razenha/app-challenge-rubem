from playhouse.db_url import connect

from app.config import DATABASE_URL

db = connect(DATABASE_URL)
