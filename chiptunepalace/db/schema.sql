-- Database Schema for Chiptunes Player
-- Tracks music and stores metadata.

CREATE TABLE IF NOT EXISTS tracks (
    track_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT,
    duration_seconds INTEGER,
    file_path TEXT NOT NULL,  -- Absolute path to file or ZIP
    is_zipped INTEGER DEFAULT 0,
    member_name TEXT,         -- Name inside ZIP if is_zipped=1
    fingerprint TEXT UNIQUE,
    source_url TEXT,
    album TEXT,
    genre TEXT,
    UNIQUE(file_path, member_name)
);

CREATE TABLE IF NOT EXISTS playlists (
    playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist_song_id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    order_index INTEGER,
    FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id),
    FOREIGN KEY (track_id) REFERENCES tracks(track_id),
    UNIQUE (playlist_id, track_id)
);
