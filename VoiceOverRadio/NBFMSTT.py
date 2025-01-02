import SoapySDR
from scipy.signal import lfilter, firwin
import wave
from SoapySDR import * #SOAPY_SDR_ constants
import numpy #use numpy for buffers

# NBFM demodulation
def nbfm_demodulate(samples, sample_rate):
    # Differentiator
    diff = numpy.diff(numpy.angle(samples))
    # Low-pass filter
    cutoff = 15000.0  # 15 kHz
    numtaps = 101
    fir_coeff = firwin(numtaps, cutoff / (sample_rate / 2))
    demodulated = lfilter(fir_coeff, 1.0, diff)
    return demodulated

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
sdr.setSampleRate(SOAPY_SDR_RX, 0, 1e6)
sdr.setFrequency(SOAPY_SDR_RX, 0, 162.4e6)

#setup a stream (complex floats)
rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
sdr.activateStream(rxStream) #start streaming

#create a re-usable buffer for rx samples
buff = numpy.array([0]*1024, numpy.complex64)


with wave.open('output.wav', 'wb') as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16 bits
    wav_file.setframerate(48000)  # 48 kHz
#receive some samples
    for i in range(10000):
        sr = sdr.readStream(rxStream, [buff], len(buff))
        print(sr.ret) #num samples or error code
        print(sr.flags) #flags set by receive operation
        print(sr.timeNs) #timestamp for receive buffer
        

        # Normalize audio to 16-bit PCM range
        audio_int16 = numpy.int16(demodulated_audio / numpy.max(numpy.abs(demodulated_audio)) * 32767)

        # Write to WAV file
        wav_file.writeframes(audio_int16.tobytes())

#shutdown the stream
sdr.deactivateStream(rxStream) #stop streaming
sdr.closeStream(rxStream)