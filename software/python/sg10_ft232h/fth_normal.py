import sys
import os
import time
from pyftdi.gpio import GpioAsyncController

TARGET_BYTES = 10 * 1024  # 1 MB
OUTPUT_FILE = "noise.bin"
CHUNK_SIZE = 65536

TARGET_KB = TARGET_BYTES // 1024

# Fine-tuning can be done here:
# Keep only every 100th sample so the hardware has time to change.
SAMPLE_STRIDE = 100  

gpio = GpioAsyncController()
try:
    gpio.configure('ftdi://ftdi:232h/1', direction=0x00)
    gpio.ftdi.set_latency_timer(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print(f"Smart entropy collection started (stride: {SAMPLE_STRIDE})...")

collected_bits = []
bytes_written = 0
start_time = time.time()

try:
    with open(OUTPUT_FILE, "wb") as f:
        while bytes_written < TARGET_BYTES:
            # Read a large chunk
            raw_data = gpio.read(CHUNK_SIZE)
            
            # We do not extract every bit; we sample with SAMPLE_STRIDE spacing
            for i in range(0, len(raw_data), SAMPLE_STRIDE):
                byte_state = raw_data[i]
                noise_bit = (byte_state >> 2) & 1
                collected_bits.append(noise_bit)
            
            # Von Neumann post-processing (optional, but cleans bits):
            # If two consecutive bits are '01', keep the 1
            # If '10', keep the 0
            # If '00' or '11', discard both (this removes DC bias)
            clean_bits = []
            while len(collected_bits) >= 2:
                b1 = collected_bits.pop(0)
                b2 = collected_bits.pop(0)
                if b1 != b2:
                    clean_bits.append(b1)
            
            # Pack the cleaned bits into bytes
            while len(clean_bits) >= 8:
                byte_to_write = 0
                for _ in range(8):
                    byte_to_write = (byte_to_write << 1) | clean_bits.pop(0)
                
                f.write(bytes([byte_to_write]))
                bytes_written += 1
                
                if bytes_written >= TARGET_BYTES:
                    break
            
            # Put back any remaining clean bits, if there are any
            collected_bits = clean_bits + collected_bits
            
            progress = (bytes_written / TARGET_BYTES) * 100
            print(f"Progress: {progress:.1f}% ({bytes_written // 1024} KB / {TARGET_KB} KB)", end="\r")

    elapsed = time.time() - start_time
    print(f"\n\nDone! Runtime: {elapsed:.2f} s | Speed: {TARGET_KB/elapsed:.2f} KB/s")

except KeyboardInterrupt:
    print("\nCollection interrupted.")
finally:
    gpio.close()