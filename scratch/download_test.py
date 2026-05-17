import os
import sys
import shutil

# Ensure chiptunepalace is in path
sys.path.append(os.path.abspath('.'))

from chiptunepalace.services.web_scraper_service import WebScraperService
from chiptunepalace.services.download_service import DownloadService
from chiptunepalace.services.track_service import TrackService
from chiptunepalace.db.orm_stubs import DatabaseManager

def run_test():
    print("=== STARTING DOWNLOAD & DUPLICATE TEST ===")
    
    scraper = WebScraperService()
    ts = TrackService()
    # Note: We use a test-specific DB or just use the current one if safe
    
    print("\n--- Testing Database Duplicate Avoidance ---")
    os.makedirs("chiptunepalace/scratch", exist_ok=True)
    test_file = os.path.abspath("chiptunepalace/scratch/test_track.vgm")
    
    with open(test_file, "wb") as f:
        f.write(b"CHIP" * 100) # Mock chiptune data
        
    # Calculate fingerprint
    fingerprint = ts.db_manager.get_fingerprint(test_file)
    print(f"Test File Fingerprint: {fingerprint}")
    
    # Add first time
    tid1 = ts.add_track(
        title="Test Sonic Track",
        artist="Sega",
        file_path=test_file,
        fingerprint=fingerprint,
        source_url="http://source1.com/sonic.zip"
    )
    print(f"Added track 1, ID: {tid1}")
    
    # Add second time with DIFFERENT PATH but SAME CONTENT
    test_file_dup = os.path.abspath("chiptunepalace/scratch/test_track_copy.vgm")
    shutil.copy(test_file, test_file_dup)
    
    print("Attempting to add duplicate content via different path...")
    tid2 = ts.add_track(
        title="Test Sonic Track (Duplicate)",
        artist="Sega",
        file_path=test_file_dup,
        fingerprint=fingerprint,
        source_url="http://another-source.com/sonic.zip"
    )
    
    if tid1 == tid2:
        print("SUCCESS: Duplicate avoided via fingerprinting!")
    else:
        print(f"FAILURE: Duplicate created (ID: {tid2}) despite same fingerprint.")

    # Cleanup
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(test_file_dup): os.remove(test_file_dup)

if __name__ == "__main__":
    run_test()
