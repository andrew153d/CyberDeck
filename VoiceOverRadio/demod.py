"""
Mono FM Demodulator

Dependencies:
numpy
scipy


This script is meant to take in raw IQ samples from stdin and output audio samples via stdout.
An SDR utility like rtl_sdr (from librtlsdr) can be used to capture IQ samples and a media
player like mplayer can be used to play the audio.


Example usage:
rtl_sdr -s 240000 -f 102.1e6 -g 20 - | python3 fm.py | mplayer -cache 1024 -quiet -rawaudio samplesize=2:channels=1:rate=48000 -demuxer rawaudio -
"""

import sys

import numpy as np
import scipy.signal as sig

IN_FS = 240000  # input sample rate in Hz
OUT_FS = 48000  # output sample rate in Hz
BLOCK_SIZE = 240000  # number of samples to process at once
LPF_FREQ = 16000  # cutoff frequency for low pass filter
LPF_NUM_TAPS = 150  # number of taps in low pass filter
DEEM_TAU = 75e-6  # time constant for deemphasis filter

# check that BLOCK_SIZE is divisible by 2
assert BLOCK_SIZE % 2 == 0
# check that IN_FS is a integer multiple of OUT_FS
assert IN_FS % OUT_FS == 0

last_phase = 0  # state for finite differencing of phase
lpf = sig.firwin(LPF_NUM_TAPS, LPF_FREQ, fs=IN_FS)  # low pass filter coefficients
lpf_state = np.zeros(LPF_NUM_TAPS - 1)  # low pass filter state
deem_dt = 1 / OUT_FS  # delta-t deemphasis filter
deem_alpha = deem_dt / (DEEM_TAU + deem_dt)
deem_filt = ((deem_alpha,), (1, -(1 - deem_alpha)))  # deemphasis filter coefficients
deem_state = np.zeros(1)  # deemphasis filter state
while True:
    # read and create array of uint8s from stdin
    u8 = np.frombuffer(sys.stdin.buffer.read(BLOCK_SIZE), dtype=np.uint8)  
    # uint8 -> float64 where 0 -> -1, 255 -> 1
    double = u8 / (((1 << 8) - 1) / 2) - 1
    # (float64, float64) -> complex128
    complex = np.reshape(double, (BLOCK_SIZE // 2, 2)).view(np.complex128)[:,0]
    # apply atan2 to calculate phase
    phase = np.angle(complex)
    # use backward difference to take derivative of phase
    dphase = np.empty_like(phase)
    dphase[1:] = phase[1:] - phase[:-1]
    # handle edge case of difference between blocks
    dphase[0] = phase[0] - last_phase
    last_phase = phase[-1]
    # wrap and scale to (-1, 1]
    dphase = (dphase / np.pi + 1) % 2 - 1
    # low pass filter
    filtered, lpf_state = sig.lfilter(lpf, (1,), dphase, zi=lpf_state)
    # decimate to output sample rate
    decimated = filtered[::(IN_FS // OUT_FS)]
    # deemphasis filter
    deemphasized, deem_state = sig.lfilter(*deem_filt, decimated, zi=deem_state)
    # float64 -> int16 where -1 -> -32767, 1 -> 32767
    s16 = (deemphasized * ((1 << 15) - 1)).astype(np.int16)
    # write int16s to stdout
    sys.stdout.buffer.write(s16)