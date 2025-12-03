import math
import time

NUM_TICKS = 100
APPROX_LINKS_PER_SECOND = 22

class ProgressBar:
    def __init__(self, total_items):
        self.total_items = total_items
        est_seconds_to_finish = math.floor(total_items / APPROX_LINKS_PER_SECOND)
        self.est_minutes_to_finish = math.floor(est_seconds_to_finish/60)
        self.remainder_seconds_to_finish = est_seconds_to_finish % 60
        self.start_time = time.time()


    def print(self, completed_items):
        if self.total_items == 0:
            print("No items")
            return
        percent_finished = math.floor((completed_items/self.total_items)*NUM_TICKS)
        bar_string = "["
        for i in range(NUM_TICKS):
            if i <= percent_finished:
                bar_string += "|"
            else:
                bar_string += "-"
        bar_string += "]"
        run_time = math.floor(time.time() - self.start_time)
        print(f"RUNNING TIME: {run_time}s")
        print(f"EST TIME TO FINISH: {self.est_minutes_to_finish}m {self.remainder_seconds_to_finish}s.")
        print(bar_string)
        