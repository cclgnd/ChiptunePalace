from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, MetaData, Table, UniqueConstraint, event, text
from sqlalchemy.orm import sessionmaker

# Initialize Metadata
metadata = MetaData()

# Define Tables
tracks_table = Table('tracks', metadata,
    Column('track_id', Integer, primary_key=True, autoincrement=True),
    Column('title', String, nullable=False),
    Column('artist', String),
    Column('duration_seconds', Integer),
    Column('file_path', String, nullable=False),
    Column('is_zipped', Integer, default=0),
    Column('member_name', String),
    Column('fingerprint', String, unique=True),
    Column('source_url', String),
    Column('album', String),
    Column('genre', String),
    UniqueConstraint('file_path', 'member_name', name='uq_path_member')
)

playlists_table = Table('playlists', metadata,
    Column('playlist_id', Integer, primary_key=True, autoincrement=True),
    Column('name', String, nullable=False, unique=True)
)

playlist_songs_table = Table('playlist_songs', metadata,
    Column('playlist_song_id', Integer, primary_key=True, autoincrement=True),
    Column('playlist_id', Integer, ForeignKey('playlists.playlist_id'), nullable=False),
    Column('track_id', Integer, ForeignKey('tracks.track_id'), nullable=False),
    Column('order_index', Integer),
    UniqueConstraint('playlist_id', 'track_id', name='uq_playlist_track')
)


class DatabaseManager:
    def __init__(self, db_path='chiptunepalace/db/chiptunepalace.db'):
        try:
            self.engine = create_engine(
                f'sqlite:///{db_path}',
                connect_args={"check_same_thread": False}
            )

            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

            metadata.create_all(self.engine)
        except Exception as e:
            print(f"FATAL DB INIT ERROR: {e}")
            self.engine = None

    def _conn(self):
        """Return a raw connection from the engine."""
        if not self.engine:
            print("FATAL: DB engine is disabled.")
            return None
        return self.engine.connect()

    def add_track(self, title, artist, file_path, album=None, genre=None, duration=None, fingerprint=None, source_url=None, is_zipped=0, member_name=None):
        conn = self._conn()
        if conn is None:
            return None
        try:
            # 1. Check for path + member duplicate
            query = tracks_table.select().where(
                (tracks_table.c.file_path == file_path) & 
                (tracks_table.c.member_name == member_name)
            )
            row = conn.execute(query).fetchone()
            if row:
                return row[0]

            # 2. Check for content duplicate (fingerprint)
            if fingerprint:
                row = conn.execute(
                    tracks_table.select().where(tracks_table.c.fingerprint == fingerprint)
                ).fetchone()
                if row:
                    print(f"DUPLICATE DETECTED: {title} already exists via fingerprint.")
                    return row[0]

            result = conn.execute(tracks_table.insert().values(
                title=title, artist=artist, file_path=file_path,
                album=album, genre=genre, duration_seconds=duration,
                fingerprint=fingerprint, source_url=source_url,
                is_zipped=is_zipped, member_name=member_name
            ))
            conn.commit()
            return result.inserted_primary_key[0]
        except Exception as e:
            conn.rollback()
            print(f"DB add_track error: {e}")
            return None
        finally:
            conn.close()

    def get_fingerprint(self, file_path, member_name=None):
        """Calculates SHA-256 of the file content. Supports files inside ZIPs."""
        import hashlib
        import zipfile
        try:
            sha256_hash = hashlib.sha256()
            
            if member_name:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    with zf.open(member_name) as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
            else:
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Hash calculation error: {e}")
            return None

    def get_all_tracks(self):
        conn = self._conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(tracks_table.select()).fetchall()
            # Convert each Row to a plain dict
            columns = [c.key for c in tracks_table.columns]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"DB get_all_tracks error: {e}")
            return []
        finally:
            conn.close()

    def get_track_by_id(self, track_id):
        conn = self._conn()
        if conn is None:
            return None
        try:
            row = conn.execute(
                tracks_table.select().where(tracks_table.c.track_id == track_id)
            ).fetchone()
            if row is None:
                return None
            columns = [c.key for c in tracks_table.columns]
            return dict(zip(columns, row))
        except Exception as e:
            print(f"DB get_track_by_id error: {e}")
            return None
        finally:
            conn.close()

    def get_track_by_path(self, file_path):
        conn = self._conn()
        if conn is None:
            return None
        try:
            row = conn.execute(
                tracks_table.select().where(tracks_table.c.file_path == file_path)
            ).fetchone()
            if row is None:
                return None
            columns = [c.key for c in tracks_table.columns]
            return dict(zip(columns, row))
        except Exception as e:
            print(f"DB get_track_by_path error: {e}")
            return None
        finally:
            conn.close()

    def create_playlist(self, name):
        conn = self._conn()
        if conn is None:
            return None
        try:
            result = conn.execute(playlists_table.insert().values(name=name))
            conn.commit()
            return result.inserted_primary_key[0]
        except Exception:
            conn.rollback()
            return None
        finally:
            conn.close()

    def add_track_to_playlist(self, playlist_id, track_id, order_index=None):
        conn = self._conn()
        if conn is None:
            return False
        try:
            conn.execute(playlist_songs_table.insert().values(
                playlist_id=playlist_id, track_id=track_id, order_index=order_index
            ))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()