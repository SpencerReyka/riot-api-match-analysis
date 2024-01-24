import time

class RateLimit():
    def __init__(self):
        self.period_start = time.time() 
        self.PERIOD = 150
        self.count = 0
        self.MAX_COUNT = 100
    
    def check_and_sleep(self):
        elapsed = time.time() - self.period_start
        if elapsed > self.PERIOD:
            print("resetting period")
            self.period_start = time.time()
            self.count = 1
        elif self.count >= self.MAX_COUNT:
            sleeptime = self.PERIOD - elapsed
            print("max count, restarting, sleeping for: " + str(sleeptime))
            time.sleep(self.PERIOD - elapsed)
            self.period_start = time.time()
            self.count = 1
        else:
            print("successful call, count: " + str(self.count))
            self.count += 1     