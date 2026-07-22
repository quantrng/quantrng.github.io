import sys
import os
import time
import hashlib
import numpy as np
from pyftdi.gpio import GpioController

# --- SETTINGS ---
# Pull 128 MB of raw data over USB.
# After the Von Neumann filter and hash whitening, this leaves ~100-200 KB of pure entropy.
RAW_BYTES_TO_READ = 128 * 1024 * 1024 
OUTPUT_FILE = "noise_bb.bin"

gpio = GpioController()
try:
    # The proven, stable asynchronous open
    gpio.configure('ftdi://ftdi:232h/1', direction=0x00)
    gpio.ftdi.set_latency_timer(1)
except Exception as e:
    print(f"Initialization error: {e}")
    sys.exit(1)

print("=======================================================")
print(" FT232H HARDWARE RANDOM NUMBER GENERATOR (TRNG) v1.0")
print("=======================================================")
print(f"PHASE 1: High-speed raw data collection from USB...")
print(f"--> Buffer size: {RAW_BYTES_TO_READ // (1024*1024)} MB. Please wait...")

start_time = time.time()

try:
    # Read the raw stream in a single block (C-level burst read)
    raw_data = gpio.read(RAW_BYTES_TO_READ)
    
    read_end_time = time.time()
    read_elapsed = read_end_time - start_time
    print(f"-> Hardware read complete! Time: {read_elapsed:.2f} s ({len(raw_data)/(1024*1024*read_elapsed):.2f} MB/s)")
    
    print("\nPHASE 2: Mathematical post-processing (vectorized Von Neumann filtering)...")
    
    # Convert raw data into a NumPy array for fast processing
    data_arr = np.frombuffer(raw_data, dtype=np.uint8)
    
    # Extract the state of the AD2 pin (bit 2 of the bytes, zero-based)
    bits = (data_arr >> 2) & 1
    
    # Prepare bit pairs (even vs odd indices)
    end_idx = len(bits) - (len(bits) % 2)
    b1 = bits[0:end_idx:2]
    b2 = bits[1:end_idx:2]
    
    # We only need pairs where a state change occurred (01 or 10)
    valid_mask = b1 != b2
    clean_bits = b1[valid_mask]
    
    # Keep only as many bits as are exactly divisible by 8 (full bytes)
    usable_len = len(clean_bits) - (len(clean_bits) % 8)
    clean_bits = clean_bits[0:usable_len]
    
    # Convert to bytes with matrix multiplication (runs in a fraction of a second)
    reshape_bits = clean_bits.reshape(-1, 8)
    powers = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint8)
    output_bytes = np.dot(reshape_bits, powers).tobytes()
    
    print(f"-> Filtering complete! Remaining clean sample: {len(output_bytes)} bytes.")
    
    print("\nPHASE 3: Cryptographic whitening (SHA-256 avalanche effect)...")
    
    whitened_bytes = bytearray()
    # Process the raw entropy in 64-byte blocks
    block_size = 64
    
    for i in range(0, len(output_bytes), block_size):
        block = output_bytes[i:i+block_size]
        # Only hash complete blocks; discard any incomplete remainder for safety
        if len(block) == block_size:
            whitened_bytes.extend(hashlib.sha256(block).digest())
    
    # Save the final result to the binary file
    with open(OUTPUT_FILE, "wb") as f:
        f.write(bytes(whitened_bytes))
        
    total_elapsed = time.time() - start_time
    print("=======================================================")
    print(f" SUCCESSFUL SAVE: {OUTPUT_FILE}")
    print(f" Final file size: {len(whitened_bytes)} bytes ({len(whitened_bytes)//1024} KB)")
    print(f" Total runtime: {total_elapsed:.2f} seconds")
    print("=======================================================")

except KeyboardInterrupt:
    print("\nCollection interrupted by the user.")
finally:
    gpio.close()