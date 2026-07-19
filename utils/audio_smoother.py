class AudioSmoother:
    def __init__(self, attack_ms=70, release_ms=260):
        self.attack_ms = attack_ms
        self.release_ms = release_ms
        self.value = 0.0

    def process(self, new_level, delta_time_ms=16.0):
        if new_level > self.value:
            factor = min(1.0, delta_time_ms / self.attack_ms)
        else:
            factor = min(1.0, delta_time_ms / self.release_ms)
        self.value = self.value * (1 - factor) + new_level * factor
        return self.value