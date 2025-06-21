import numpy as np
import pygame
import socket
import struct
import queue
import threading
import sounddevice as sd
import time

audio_queue = queue.Queue()
samplerate = 44100
CHUNK_SIZE = 4096
clock = pygame.time.Clock()

def clamp(min_value, max_value, value):

    if value < min_value:
        return min_value

    if value > max_value:
        return max_value

    return value


class AudioBar:

    def __init__(self, x, y, freq, color, width=50, min_height=10, max_height=100, min_decibel=-60, max_decibel=0):

        self.x, self.y, self.freq = x, y, freq

        self.color = color

        self.width, self.min_height, self.max_height = width, min_height, max_height

        self.height = min_height

        self.min_decibel, self.max_decibel = min_decibel, max_decibel

        self.__decibel_height_ratio = (self.max_height - self.min_height)/(self.max_decibel - self.min_decibel)

    def update(self, dt, decibel):

        desired_height = (decibel - self.min_decibel) * self.__decibel_height_ratio + self.min_height

        speed = (desired_height - self.height)/0.1

        self.height += speed * dt

        self.height = clamp(self.min_height, self.max_height, self.height)

    def render(self, screen):
        print(f"x={self.x}, y={self.y}, max_height={self.max_height}, height={self.height}, width={self.width}")
        x = int(self.x)
        y = int(self.y + self.max_height - self.height)
        width = int(self.width)
        height = int(self.height)
        pygame.draw.rect(screen, self.color, (x, y, width, height))


#filename = "audio.mp3"

PORT = 8080
HOST = "127.0.0.1"

def receive_and_play():
    with socket.create_connection((HOST, PORT)) as s:
        channels = 2
        dtype = 'int16'

        stream = sd.OutputStream(samplerate=samplerate, channels=channels, dtype=dtype, blocksize=2048)
        stream.start()
        time.sleep(0.1)
        try:
            while True:
                data = s.recv(CHUNK_SIZE)
                if not data:
                    break

                # Convert bytes to numpy array and reshape for stereo
                samples = np.frombuffer(data, dtype=np.int16).reshape(-1, 2)
                #mono = samples.mean(axis=1)
                audio_queue.put(samples.mean(axis=1))
                try:
                    stream.write(samples)
                except Exception as e:
                    print("Audio write error:", e)
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()

#time_series, sample_rate = librosa.load(filename)  # getting information from the file

# getting a matrix which contains amplitude values according to frequency and time indexes
#stft = np.abs(librosa.stft(time_series, hop_length=512, n_fft=2048*4))

#spectrogram = librosa.amplitude_to_db(stft, ref=np.max)  # converting the matrix to decibel matrix

#frequencies = librosa.core.fft_frequencies(n_fft=2048*4)  # getting an array of frequencies

# getting an array of time periodic
#times = librosa.core.frames_to_time(np.arange(spectrogram.shape[1]), sr=sample_rate, hop_length=512, n_fft=2048*4)

#time_index_ratio = len(times)/times[len(times) - 1]

#frequencies_index_ratio = len(frequencies)/frequencies[len(frequencies)-1]


def get_decibel(target_time, freq):
    return spectrogram[int(freq * frequencies_index_ratio)][int(target_time * time_index_ratio)]

def compute_fft_decibels(samples, samplerate, n_fft=4096):
    window = np.hanning(len(samples))
    fft = np.fft.rfft(samples * window, n=n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1 / samplerate)
    magnitude = np.abs(fft)
    magnitude /= np.max(magnitude + 1e-6)
    db = 20 * np.log10(magnitude + 1e-6)  # avoid log(0)
    return freqs, db


pygame.init()

infoObject = pygame.display.Info()

screen_w = int(infoObject.current_w/2.5)
screen_h = int(infoObject.current_w/2.5)

# Set up the drawing window
screen = pygame.display.set_mode([screen_w, screen_h])


bars = []


frequencies = np.arange(100, 8000, 100)

r = len(frequencies)


width = screen_w/r


x = (screen_w - width*r)/2

for c in frequencies:
    bars.append(AudioBar(x, 300, c, (255, 0, 0), max_height=400, width=width))
    x += width

t = pygame.time.get_ticks()
getTicksLastFrame = t
threading.Thread(target=receive_and_play, daemon=True).start()
#pygame.mixer.music.load(filename)
#pygame.mixer.music.play(0)

# Run until the user asks to quit
running = True
while running:

    t = pygame.time.get_ticks()
    deltaTime = (t - getTicksLastFrame) / 1000.0
    getTicksLastFrame = t

    # Did the user click the window close button?
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill the background with white
    screen.fill((255, 255, 255))

    if not audio_queue.empty():
        frame = audio_queue.get()
        freqs, decibels = compute_fft_decibels(frame, samplerate)
        for b in bars:
            idx = np.argmin(np.abs(freqs - b.freq))
            db_val = np.clip(decibels[idx], b.min_decibel, b.max_decibel)
            b.update(deltaTime, db_val)
            b.render(screen)

    #for b in bars:
    #    b.update(deltaTime, get_decibel(pygame.mixer.music.get_pos()/1000.0, b.freq))
    #    b.render(screen)

    # Flip the display
    clock.tick(40)
    pygame.display.flip()

# Done! Time to quit.
pygame.quit()

