import SoapySDR
from scipy.signal import lfilter, firwin
import wave
from SoapySDR import * #SOAPY_SDR_ constants
import numpy #use numpy for buffers


import sys

import numpy as np
import scipy.signal as sig

FREQ = 162.4e6
IN_FS = 240000  # input sample rate in Hz
OUT_FS = 48000  # output sample rate in Hz
BLOCK_SIZE = 1024 #240000  # number of samples to process at once
LPF_FREQ = 16000  # cutoff frequency for low pass filter
LPF_NUM_TAPS = 150  # number of taps in low pass filter
DEEM_TAU = 75e-6  # time constant for deemphasis filter

# check that BLOCK_SIZE is divisible by 2
assert BLOCK_SIZE % 2 == 0
# check that IN_FS is a integer multiple of OUT_FS
assert IN_FS % OUT_FS == 0



# NBFM demodulation
def nbfm_demodulate(samples):
    last_phase = 0  # state for finite differencing of phase
    lpf = sig.firwin(LPF_NUM_TAPS, LPF_FREQ, fs=IN_FS)  # low pass filter coefficients
    lpf_state = np.zeros(LPF_NUM_TAPS - 1)  # low pass filter state
    deem_dt = 1 / OUT_FS  # delta-t deemphasis filter
    deem_alpha = deem_dt / (DEEM_TAU + deem_dt)
    deem_filt = ((deem_alpha,), (1, -(1 - deem_alpha)))  # deemphasis filter coefficients
    deem_state = np.zeros(1)  # deemphasis filter state
    #u8 = np.frombuffer(sys.stdin.buffer.read(BLOCK_SIZE), dtype=np.uint8)  
    # uint8 -> float64 where 0 -> -1, 255 -> 1
    #double = u8 / (((1 << 8) - 1) / 2) - 1
    # (float64, float64) -> complex128
    complex = samples#np.reshape(double, (BLOCK_SIZE // 2, 2)).view(np.complex128)[:,0]
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
    return s16

#enumerate devices
results = SoapySDR.Device.enumerate()
for result in results: print(result)

#create device instance
#args can be user defined or from the enumeration result
args = dict(driver="rtlsdr")
sdr = SoapySDR.Device(args)

#query device info
print(sdr.listAntennas(SOAPY_SDR_RX, 0))
print(sdr.listGains(SOAPY_SDR_RX, 0))
freqs = sdr.getFrequencyRange(SOAPY_SDR_RX, 0)
for freqRange in freqs: print(freqRange)

#apply settings
sdr.setSampleRate(SOAPY_SDR_RX, 0, IN_FS)
sdr.setFrequency(SOAPY_SDR_RX, 0, FREQ)

#setup a stream (complex floats)
rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
sdr.activateStream(rxStream) #start streaming

#create a re-usable buffer for rx samples
buff = numpy.array([0]*BLOCK_SIZE, numpy.complex64)


with wave.open('output.wav', 'wb') as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16 bits
    wav_file.setframerate(OUT_FS)  # 48 kHz
#receive some samples
    for i in range(10000):
        sr = sdr.readStream(rxStream, [buff], len(buff))
        print(sr.ret) #num samples or error code
        print(sr.flags) #flags set by receive operation
        print(sr.timeNs) #timestamp for receive buffer
        
        # Perform NBFM demodulation
        demodulated_audio = nbfm_demodulate(buff)

        # Normalize audio to 16-bit PCM range
        audio_int16 = numpy.int16(demodulated_audio / numpy.max(numpy.abs(demodulated_audio)) * 32767)

        # Write to WAV file
        wav_file.writeframes(audio_int16.tobytes())

#shutdown the stream
sdr.deactivateStream(rxStream) #stop streaming
sdr.closeStream(rxStream)