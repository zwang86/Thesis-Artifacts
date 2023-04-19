import argparse
import csv
import statistics
from pathlib import Path
from enum import Enum


class LogItemType(Enum):
    GPT_TIME = 1
    CONTEXT = 2
    OUTPUT = 3
    LATENCY = 4
    TOTAL_TIME = 5
    TOKEN_COUNT = 6


def parseline(line):
    items = line.split()
    if not items:
        return None
    if items[0] == '[INFO]':
        try:
            if items[1] == 'Total':
                if items[2] == 'time':
                    return LogItemType.TOTAL_TIME, float(items[4])
                elif items[2] == 'token':
                    return LogItemType.TOKEN_COUNT, int(items[4])
            time = float(items[4])
            if items[1] == 'batch':
                return None
        except:
            return None
        return LogItemType.GPT_TIME, time
    elif items[0] == '[Context]':
        return LogItemType.CONTEXT,
    elif items[0] == '[Output]':
        return LogItemType.OUTPUT,
    elif items[0] == '[latency]':
        return LogItemType.LATENCY, float(items[1]) * 1000
    else:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str)
    parser.add_argument('--gpu', type=int)

    sample_input_file = parser.parse_args().input
    num_gpu = parser.parse_args().gpu

    gpt_time = []
    input_token_length = []
    latency = []
    total_time = 0
    throughput = 0

    folder_path = Path(f"./{sample_input_file[:-4]}")

    try:
        folder_path.mkdir(parents=True)
    except Exception as e:
        print("Error: Unable to create folder. " + str(e))

    with open(sample_input_file, "r") as f:
        contexts = f.read().splitlines()

    for i in range(len(contexts)):
        items = parseline(contexts[i])
        if items is None:
            continue

        if items[0] == LogItemType.GPT_TIME:
            gpt_time.append(items[1])
        elif items[0] == LogItemType.CONTEXT:
            i += 1
            input_token_length.append(len(contexts[i])/token_length)
        elif items[0] == LogItemType.OUTPUT:
            i += 1
        elif items[0] == LogItemType.LATENCY:
            i += 1
            latency.append(items[1])
        elif items[0] == LogItemType.TOTAL_TIME:
            total_time = max(total_time, items[1])
        elif items[0] == LogItemType.TOKEN_COUNT:
            throughput = max(throughput, items[1])

    gpt_sum = sum(gpt_time)
    gpt_avg = gpt_sum / len(gpt_time)

    print("Total request: ", len(latency))
    print("------------------------")
    print("gpt_sum:", gpt_sum)
    print("gpt_avg:", gpt_avg)
    print("max gpt:", max(gpt_time))
    print("min gpt:", min(gpt_time))

    latency_sum = sum(latency)
    latency_avg = latency_sum / len(latency)
    std_dev = statistics.stdev(latency)
    print("------------------------")
    print("Average Latency: ", latency_avg)
    print("Max Latency: ", max(latency))
    print("Min latency:", min(latency))
    print("Standard Deviation: ", std_dev)

    print("------------------------")
    print("throughput: ", throughput/total_time)
    print("total time: ", total_time)
    print("token generated: ", throughput)

    with open(f'./{sample_input_file[:-4]}/kernel_{num_gpu}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Batch ID', 'Kernel Time'])  # Write header row
        for i, value in enumerate(gpt_time):
            writer.writerow([i, value])

    with open(f'./{sample_input_file[:-4]}/latency_{num_gpu}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Request ID', 'latency'])
        for i, value in enumerate(latency):
            writer.writerow([i, value])


if __name__ == '__main__':
    main()
