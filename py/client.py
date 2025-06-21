import socket
import struct
import numpy as np
import sounddevice as sd

HOST = '127.0.0.1'
PORT = 8080
CHUNK_SIZE = 4096

def receive_and_play():
    with socket.create_connection((HOST, PORT)) as s:
        samplerate = 44100
        channels = 2
        dtype = 'int16'

        stream = sd.OutputStream(samplerate=samplerate, channels=channels, dtype=dtype)
        stream.start()

        try:
            while True:
                data = s.recv(CHUNK_SIZE)
                if not data:
                    break

                samples = np.frombuffer(data, dtype=np.int16)
                if len(samples) % channels != 0:
                    continue  # skip incomplete frame
                stereo_samples = samples.reshape(-1, channels)
                stream.write(stereo_samples)
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()

if __name__ == '__main__':
    receive_and_play()

