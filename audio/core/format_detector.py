import os

# Set of extensions supported by Game Music Emu
GME_EXTENSIONS = {
    '.vgm', '.vgz', '.spc', '.nsf', '.nsfe', '.gbs', '.hes', '.gym', '.sgc', '.kss'
}

def is_emulation_supported(file_path: str, member_name: str = None) -> bool:
    """
    Checks if a file extension (or ZIP member extension) is supported
    by the real-time chip emulation system.
    """
    target = member_name if member_name else file_path
    if not target:
        return False
        
    _, ext = os.path.splitext(target.lower())
    return ext in GME_EXTENSIONS
