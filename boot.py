print("--- Booting ESP32 ---")
import os
import gc

try:
    print("Files:", os.listdir())
except:
    print("Filesystem error")

gc.collect()
