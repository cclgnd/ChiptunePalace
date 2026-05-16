from chiptunepalace.db.orm_stubs import DatabaseManager


class TrackService:
    """Handles all database interactions related to tracks."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def get_all_tracks(self):
        """Returns a list of dicts, one per track."""
        return self.db_manager.get_all_tracks()

    def get_track_by_id(self, track_id: int):
        """Returns a single track dict or None."""
        return self.db_manager.get_track_by_id(track_id)

    def add_track(self, title: str, artist: str, file_path: str, **kwargs):
        """Adds a new track; returns the track_id."""
        return self.db_manager.add_track(title, artist, file_path, **kwargs)
