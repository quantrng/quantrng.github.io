# The Quest for Quantum Noise (Part 1): The First Working Prototype

### SG-10 Noise Source, Transistor Protection on Breadboard, and FT232H Interface

## 1. Objective & Setup
This first test was kept deliberately simple: build a working analog front end on a breadboard and see if the noise from an **SG-10** source could be read safely by an **FT232H** USB 2.0 interface.

The SG-10 output can go beyond what the FT232H input pin should see, so I added a small protection and conditioning stage between the source and the controller.

## 2. Hardware Architecture (Breadboard Phase)

![alt text](images/qrng_sg10_fth.jpg)

### Component List:
* **SG-10:** Noise source (https://attach01.oss-us-west-1.aliyuncs.com/IC/DIY-Manual/12589.pdf)
* **FT232H breakout board:** USB 2.0 sampling and data acquisition interface [AliExpress](https://www.aliexpress.com/item/1005005796716386.html?osf=ppc_ug&guideModule=ppc_ug&src=google&albch=search&acnt=479-062-3723&isdl=y&aff_short_key=UneMJZVf&albcp=22578521270&albag=185025180612&slnk=&trgt=kwl-42862830006&plac=&crea=816691060214&albad=816691060214&netw=g&device=c&mtctp=a&memo1=&albbt=Google_7_search&aff_platform=google&albagn=888888&isSmbActive=false&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=22578521270&gclid=CjwKCAjw1IHTBhAaEiwA4AYNFhK7HE2KKaUis3wZYnRlg5vG5ZAABt_dnd882O72pwgDe5Gc8Z8wqRoCGogQAvD_BwE)
* **1x NPN transistor (2N3904):** Protection element
* **1x Capacitor (100 nF):** AC coupling
* **2x Capacitor (220 uF, 100 nF):** Power supply filtering
* **2x Resistors (4.7 kOhm, 100 kOhm):** Current limiting and biasing


## 3. How It Works Step-by-Step

* **Power Supply Filtering:** The 220 uF and 100 nF capacitors sit in parallel between 12V and GND, right before the SG-10 module. That helps take the edge off small bench-supply fluctuations.
* **AC Coupling:** The noise from the J1 output passes through a 100 nF capacitor. That blocks the DC component and leaves the AC part for the transistor stage.
* **Operating Point (Bias):** The 100 kOhm resistor connected between the Base and GND (Emitter) keeps the transistor near its switching threshold, so small positive noise spikes can flip the output state.
* **Digital Signal Generation:**
	
  * When the noise produces a positive spike, the transistor turns on and pulls the Collector (and thus the AD2 pin) down to GND (Logical 0).
  * When the noise drops to zero or goes negative, the transistor turns off and the 4.7 kOhm pull-up resistor pulls the Collector up to the FT232H's internal 3.3V level (Logical 1).

### Circuit Diagram Concept:

![schematics_sg10-fth](images/schematics_sg10-fth.png)

KICAD Schematic: [sg10-ft232h.sch](../hardware/kicad/SG10_FT232H/SG10_FT232H.kicad_sch)



## 4. Initial Benchmark & Entropy Testing (Standard Read vs. Bitbang Mode)

### Environment Setup & Prerequisites

<details>
<summary><b>👉 Click here for step-by-step setup instructions (Virtualenv, Drivers & Permissions)</b></summary>

#### 1. Create a Virtual Environment & Install Dependencies
It is recommended to run the script inside a clean Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Hardware Driver & USB Permissions

The pyftdi library talks directly to the FT232H via standard libusb drivers (without relying on VCP/COM port drivers).

Linux / Raspberry Pi: You need to grant non-root access to the FTDI USB device. Add a udev rule:

```bash

    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", MODE="0666"' | sudo tee /etc/udev/rules.d/11-ftdi.rules
    sudo udevadm control --reload-rules
```
*  Windows: If the default FTDI driver is bound as a COM port, use Zadig to replace the driver for Interface 0 with WinUSB or libusbK.

*  macOS: Ensure no native VCP drivers are locking the chip (sudo kextunload -b com.FTDI.driver.FTDIUSBSerialDriver if necessary).
---
</details>

### Testing scenarios

To evaluate how data acquisition timing affects signal fidelity, I tested two distinct sampling strategies using John Walker's `ent` (Pseudorandom Number Sequence Test Program):

1. **Standard Read Mode:** Continuous byte streaming over the regular USB buffer path.
2. **Bitbang Mode:** GPIO timing that is controlled more directly during sampling.

The Standard Read run is the raw acquisition reference. The Bitbang run also includes post-processing, so I would treat the two results as pipeline outcomes rather than a perfectly matched A/B test.


#### 1. Standard Read Mode Test

Python script:
[`fth_normal.py`](../software/python/sg10_ft232h/fth_normal.py)
```bash
(venv) :~/Oleesoft/fth-test$ python fth_normal.py
Smart entropy collection started (stride: 100)...
Progress: 100.0% (10 KB / 10 KB)

Done! Runtime: 72.97 s | Speed: 0.14 KB/s
```

```text
Entropy = 7.759041 bits per byte.

Optimum compression would reduce the size
of this 10240 byte file by 3 percent.

Chi square distribution for 10240 samples is 3793.05, and randomly
would exceed this value less than 0.01 percent of the times.

Arithmetic mean value of data bytes is 128.0612 (127.5 = random).
Monte Carlo value for Pi is 3.261430246 (error 3.81 percent).
Serial correlation coefficient is -0.014158 (totally uncorrelated = 0.0).
```

#### 2. Bitbang Mode Test

Python script:
[`fth_bitbang.py`](../software/python/sg10_ft232h/fth_bitbang.py)

```bash
(venv) :~/Oleesoft/fth-test$ python fth_bitbang.py
=======================================================
 FT232H HARDWARE RANDOM NUMBER GENERATOR (TRNG) v1.0
=======================================================
PHASE 1: High-speed raw data collection from USB...
--> Buffer size: 128 MB. Please wait...
-> Hardware read complete! Time: 18.86 s (1.91 MB/s)

PHASE 2: Mathematical post-processing (vectorized Von Neumann filtering)...
-> Filtering complete! Remaining clean sample: 2976 bytes.

PHASE 3: Cryptographic whitening (SHA-256 avalanche effect)...
=======================================================
 SUCCESSFUL SAVE: noise_bb.bin
 Final file size: 1472 bytes (1 KB)
 Total runtime: 18.92 seconds
=======================================================
```

```text
Entropy = 7.874101 bits per byte.

Optimum compression would reduce the size
of this 1472 byte file by 1 percent.

Chi square distribution for 1472 samples is 250.09, and randomly
would exceed this value 57.51 percent of the times.

Arithmetic mean value of data bytes is 126.6984 (127.5 = random).
Monte Carlo value for Pi is 3.134693878 (error 0.22 percent).
Serial correlation coefficient is 0.020705 (totally uncorrelated = 0.0).
```

### Summary

| Metric | Standard Read | Bitbang Mode | Theoretical Ideal |
| :--- | :--- | :--- | :--- |
| **Entropy** | 7.7590 bits/byte | **7.8741 bits/byte** | 8.0000 bits/byte |
| **Chi-Square Susceptibility** | < 0.01% *(Pattern bias)* | **57.51%** *(Looks random)* | ~50.00% |
| **Mean Byte Value** | 128.0612 | **126.6984** | 127.5000 |
| **Monte Carlo $\pi$ Error** | 3.81% | **0.22%** | 0.00% |
| **Serial Correlation** | -0.0141 | **0.0207** | 0.0000 |


## 5. Test Results & Key Findings

### Understanding the Benchmark Parameters & Results

#### 1. Shannon Entropy (Bits per Byte)
* **What it measures:** How much randomness is packed into each byte. In a perfect physical source, that would be 8.0 bits per byte ($100\%$ unpredictable).
* **Our Results:**
  * **Standard Read:** 7.7590 bits/byte.
  * **Bitbang Mode:** 7.8741 bits/byte.
* **Why it matters:** The jump from 7.76 to 7.87 suggests that the Bitbang sampling path is picking up a cleaner signal and a bit less fixed pattern from the acquisition chain.



#### 2. Chi-Square ($\chi^2$) Test Susceptibility
* **What it measures:** How evenly the values 0 through 255 are spread across the sample file. In random data, the score should land somewhere near the middle.
* **Our Results:**
  * **Standard Read:** < 0.01% *(Fails — indicates non-random periodic patterns)*
  * **Bitbang Mode:** 57.51% *(Passes — decent spread)*
* **Why it matters:** This is the clearest difference between the two modes. Standard Read picks up more USB buffering and transfer timing artifacts, while the Bitbang path seems less exposed to them. The result is a flatter distribution.



#### 3. Arithmetic Mean
* **What it measures:** The average value of the sampled bytes. If all values from 0 to 255 appear equally often, the mean should be 127.5.
* **Our Results:**
  * **Standard Read:** 128.0612
  * **Bitbang Mode:** 126.6984
* **Why it matters:** Both modes stay close to the ideal 127.5 target, so there is no obvious DC drift in the output.



#### 4. Monte Carlo Value for π
* **What it measures:** A spatial randomness test. Bytes are grouped into 2D coordinate pairs and used to estimate π from how many points fall inside a circle in a square.
* **Our Results:**
  * **Standard Read:** π ≈ 3.2614 *(Error: 3.81%)*
  * **Bitbang Mode:** π ≈ 3.1347 *(Error: 0.22%)*
* **Why it matters:** A lower error means the byte stream is less likely to form obvious patterns in 2D space. The Bitbang run does a bit better here.



#### 5. Serial Correlation Coefficient
* **What it measures:** Dependency between consecutive bytes. It checks whether one byte depends on the one before it. A completely uncorrelated sequence yields 0.0000.
* **Our Results:**
  * **Standard Read:** -0.0141
  * **Bitbang Mode:** 0.0207
* **Why it matters:** Both values are close to zero, so there is no strong sign of memory effect in the data.



### Conclusion: Why Bitbang Mode Wins

Standard USB reads are fine for throughput, but they leave more of the timing to the FTDI buffering path. In this setup that seems to introduce repeatable structure, and the Chi-square test picks that up quickly.

Bitbang mode gives tighter control over when each sample is taken. In practice, that makes the output look a little cleaner and nudges the entropy up a bit.


## 6. Summary & Next Steps

### What We Achieved in Part 1

We turned a noisy transistor stage into a working, USB-connected **Hardware Quantum Random Number Generator (QRNG)** prototype on a breadboard.

What the first build showed was pretty simple:
* the noise source is usable as a random signal;
* the Bitbang path gives cleaner results than the basic USB read path;
* the byte stream does not show much obvious correlation.


### The Problem with Breadboards (And Why We Need a PCB)

The breadboard version also has the usual drawbacks:
1. **EMF & External Noise Susceptibility:** Unshielded jumper wires act as tiny antennas, picking up $50\text{ Hz}/60\text{ Hz}$ mains hum, Wi-Fi ripple, and ambient electromagnetic interference.
2. **Parasitic Capacitance:** Long breadboard traces limit our maximum switching frequency and introduce subtle phase delays.
3. **Mechanical Instability:** Hot-glued components and loose jumper wires are great for proof-of-concept testing, but not for a reliable, production-ready cryptographic tool.


### Coming Up in Part 2: Custom KiCad PCB & RP2350 Integration

In **Part 2**, the jumper wires go away and the circuit moves onto a proper printed circuit board.

That next article will cover:
* **KiCad Schematic & Layout:** Designing low-noise power rails, precision filtering, and sensible signal routing for the avalanche noise generator.
* **RP2350 Board Integration:** Interfacing our analog noise generator board directly with the new RP2350 microcontroller module for high-speed sampling.
* **EMI & Physical Layout Considerations:** Designing ground planes and compact traces to isolate the sensitive analog breakdown node from external noise.
* **Gerber Export & Manufacturing:** Preparing the manufacturing package (Gerber, CPL, BOM) to order our custom prototype PCBs.

If you want to look at the underlying files, the [QuantRNG GitHub Repository](https://github.com/quantrng/quantrng.github.io) has the raw entropy datasets, Python acquisition scripts, and early schematic drafts. Part 2 follows from there.