import math
import time

NUM_TICKS = 100

def seconds_to_min_sec(seconds):
    mins = math.floor(seconds/60)
    remaining_seconds = seconds % 60
    return f"{mins}m {remaining_seconds}s"

class ProgressBar:
    def __init__(self, total_items, rate_limit):
        self.total_items = total_items
        self.est_seconds_to_finish = math.floor(total_items / rate_limit)
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
        run_time_in_seconds = math.floor(time.time() - self.start_time)
        print(f"RUNNING TIME: {seconds_to_min_sec(run_time_in_seconds)}")
        print(f"EST TIME TO FINISH: {seconds_to_min_sec(self.est_seconds_to_finish)}.")
        print(bar_string)
        