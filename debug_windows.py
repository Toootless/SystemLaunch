#!/usr/bin/env python3
"""Debug script to see what windows pygetwindow finds"""
import time
import pygetwindow as gw

print("Waiting 3 seconds for windows to settle...")
time.sleep(3)

all_windows = gw.getAllWindows()
print(f"\nTotal windows found: {len(all_windows)}")
print("\nChrome windows:")
for w in all_windows:
    if w and w.visible and any(kw in w.title.lower() for kw in ["chrome", "google", "untitled", "messenger", "gmail", "youtube", "spotify"]):
        print(f"  - '{w.title}' @ ({w.left}, {w.top}) {w.width}x{w.height} [hwnd={w._hWnd}]")

print("\nVS Code windows:")
for w in all_windows:
    if w and w.visible and "code" in w.title.lower():
        print(f"  - '{w.title}' @ ({w.left}, {w.top}) {w.width}x{w.height} [hwnd={w._hWnd}]")

print("\nAll visible windows:")
for i, w in enumerate(all_windows):
    if w and w.visible:
        title = w.title[:50] if w.title else "(untitled)"
        print(f"  [{i}] '{title}' @ ({w.left}, {w.top}) {w.width}x{w.height}")
