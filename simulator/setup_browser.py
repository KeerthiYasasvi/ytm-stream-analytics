# simulator/setup_browser.py
from ytmusicapi import setup

if __name__ == "__main__":
    # This will prompt you to paste in your full request-header block
    setup(filepath="browser.json")
    print("✅ Wrote browser.json")
