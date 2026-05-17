import os
import hashlib
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Track(Base):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    artist = Column(String)
    console = Column(String)
    game = Column(String)
    file_path = Column(String, nullable=False)
    member_name = Column(String)
    fingerprint = Column(String)
    source_url = Column(String)
    format = Column(String)
    duration = Column(Float)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

class PlaylistEntry(Base):
    __tablename__ = 'playlist'
    track_id = Column(Integer, ForeignKey('tracks.id'), primary_key=True)
    position = Column(Integer, primary_key=True)

class DatabaseManager:
    """
    Manages the SQLite database using SQLAlchemy in WAL mode.
    Provides robust methods for indexing, querying, and duplicate avoidance.
    """
    def __init__(self, db_path='chiptunepalace/db/chiptunepalace.db'):
        # Normalize file path and handle absolute/relative path
        # In a development workspace context, check both local and absolute paths
        if not os.path.isabs(db_path):
            # Check if we are running from chiptunepalace parent directory
            # and resolve db path correctly
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, db_path)
            
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        self.db_path = db_path
        
        # Initialize DebugService
        from chiptunepalace.services.debug_service import DebugService
        self.debug_service = DebugService()
        self.debug_service.log_info(f"DatabaseManager: Initializing database at path={db_path}")
        
        # SQLite connection URL
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"timeout": 15})
        
        # Enable WAL mode
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.commit()
            self.debug_service.log_info("DatabaseManager: WAL mode active.")
            
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_fingerprint(self, file_path: str) -> str | None:
        """Calculates MD5 hash of file content."""
        if not os.path.exists(file_path):
            return None
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"DatabaseManager: MD5 hash failed for {file_path}: {e}")
            return None

    def get_all_tracks(self) -> list:
        """Returns all tracks as a list of dicts."""
        session = self.Session()
        try:
            tracks = session.query(Track).order_by(Track.console, Track.game, Track.title).all()
            return [self._to_dict(t) for t in tracks]
        finally:
            session.close()

    def get_track_by_id(self, track_id: int) -> dict | None:
        """Returns details for a single track by its ID."""
        session = self.Session()
        try:
            track = session.query(Track).filter(Track.id == track_id).first()
            return self._to_dict(track) if track else None
        finally:
            session.close()

    def add_track(self, title: str, artist: str, file_path: str, **kwargs) -> int:
        """
        Adds a new track to the database, ensuring duplicate avoidance.
        If a duplicate is found (matching fingerprint or matching file_path + member_name),
        it returns the existing track's ID.
        """
        session = self.Session()
        try:
            fingerprint = kwargs.get('fingerprint')
            member_name = kwargs.get('member_name')
            
            # 1. De-duplicate by fingerprint (if provided)
            if fingerprint:
                existing = session.query(Track).filter(
                    Track.fingerprint == fingerprint,
                    Track.member_name == member_name
                ).first()
                if existing:
                    self.debug_service.log_info(f"DatabaseManager: Duplicate found by fingerprint! ID: {existing.id}")
                    print(f"DatabaseManager: Duplicate found by fingerprint! ID: {existing.id}")
                    # Update file path if it was empty or different (e.g. now local instead of online)
                    if file_path and existing.file_path != file_path:
                        existing.file_path = file_path
                        session.commit()
                    return existing.id

            # 2. De-duplicate by file_path + member_name
            existing = session.query(Track).filter(
                Track.file_path == file_path,
                Track.member_name == member_name
            ).first()
            if existing:
                self.debug_service.log_info(f"DatabaseManager: Duplicate found by file path & member! ID: {existing.id}")
                print(f"DatabaseManager: Duplicate found by file path & member! ID: {existing.id}")
                return existing.id

            # Create new track record
            new_track = Track(
                title=title,
                artist=artist,
                console=kwargs.get('console', 'Unknown Console'),
                game=kwargs.get('game', 'Unknown Game'),
                file_path=file_path,
                member_name=member_name,
                fingerprint=fingerprint,
                source_url=kwargs.get('source_url'),
                format=kwargs.get('format'),
                duration=kwargs.get('duration')
            )
            session.add(new_track)
            session.commit()
            self.debug_service.log_info(f"DatabaseManager: Added new track. Title: '{title}', Game: '{new_track.game}', ID: {new_track.id}")
            return new_track.id
        except Exception as e:
            session.rollback()
            self.debug_service.log_error(f"DatabaseManager: Failed to add track: {e}")
            print(f"DatabaseManager: Failed to add track: {e}")
            raise e
        finally:
            session.close()

    def _to_dict(self, track: Track) -> dict:
        return {
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'console': track.console,
            'game': track.game,
            'file_path': track.file_path,
            'member_name': track.member_name,
            'fingerprint': track.fingerprint,
            'source_url': track.source_url,
            'format': track.format,
            'duration': track.duration,
            'added_at': track.added_at.isoformat() if track.added_at else None
        }
