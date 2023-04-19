import statistics
import csv
import argparse
from pathlib import Path
from enum import Enum


class LogItemType(Enum):
    NEW_REQUEST = 0
    NEXT_BATCH = 1
    NEW_BATCH = 2
    BATCH_CONFIG = 3
    ELAPSED = 4


def parseline(line):
    items = line.split()
    if len(items) < 6:
        if items[0] == 'BatchConfig,':
            return LogItemType.BATCH_CONFIG, int(items[-1])
        return None
    if items[5] == '[NewRequest]':
        id = int(items[6][5:-1])
        length = int(items[7][7:-1])
        return LogItemType.NEW_REQUEST, id, float(items[3]), length
    elif items[5] == '[Done]':
        id = int(items[6][5:-1])
        length = int(items[7][13:-1])
        return LogItemType.NEW_BATCH, id, float(items[3]), length
    elif items[5] == '[NextBatch]':
        num = int(items[6][11:-1])
        return LogItemType.NEXT_BATCH, num, float(items[3])
    elif items[0] == 'ELAPSED':
        return LogItemType.ELAPSED, float(items[3][:-2])
    else:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str)
    parser.add_argument('--gpu', type=int)
    parser.add_argument('--stride', type=int, default=3)
    parser.add_argument('--arrival', type=str, default='arrival_times.txt')

    sample_input_file = parser.parse_args().input
    num_gpu = parser.parse_args().gpu
    contexts = []
    requests = dict()
    batches = []
    length = []
    final_length = []
    batch_size = []
    start_time = 0
    arrival_times = []
    total_time = 100

    folder_path = Path(f"./{sample_input_file[:-4]}")

    try:
        folder_path.mkdir(parents=True)
    except Exception as e:
        print("Error: Unable to create folder. " + str(e))

    with open(sample_input_file, "r") as f:
        contexts = f.read().splitlines()
    with open(parser.parse_args().arrival, "r") as f:
        arrival_times = [float(time)/1000 for time in f.read().splitlines()]

    for line in contexts:
        result = parseline(line)

        if result is None:
            continue

        if result[0] == LogItemType.NEXT_BATCH:  # new batch
            batches.append([result[1], result[2]])

        elif result[0] == LogItemType.NEW_REQUEST:  # new request
            if result[1] not in requests:
                start_time = min(start_time, result[2])
                requests[result[1]] = [arrival_times[result[1]] + start_time]
            else:
                requests[result[1]].append(result[2] - start_time)
            length.append(result[3])

        elif result[0] == LogItemType.NEW_BATCH:  # request done
            if result[1] not in requests:
                raise Exception('Error')
            else:
                requests[result[1]].append(result[2])
                final_length.append(result[3])
        elif result[0] == LogItemType.BATCH_CONFIG:
            batch_size.append(result[1])
        elif result[0] == LogItemType.ELAPSED:
            total_time = result[1]

    batch_size = batch_size[::parser.parse_args().stride]

    latency = []
    for key, value in requests.items():
        latency.append((value[1] - value[0])*1000)

    # calculate each batch's gpt time
    gpt_time = []
    for i in range(num_gpu, len(batches)):
        gpt_time.append((batches[i][1] - batches[i-num_gpu][1]) * 1000)

    with open(f'./{sample_input_file[:-4]}/kernel_{num_gpu}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Batch Id', 'kernel Time'])  # Write header row
        for i, value in enumerate(gpt_time):
            writer.writerow([i, value])

    # Write latency values to CSV file
    with open(f'./{sample_input_file[:-4]}/latency_{num_gpu}.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Request Id', 'Latency'])  # Write header row
        for i, value in enumerate(latency):
            writer.writerow([i, value])

    # Calculate latency statistics
    avg_latency = sum(latency) / len(latency)
    max_latency = max(latency)
    min_latency = min(latency)
    std_dev = statistics.stdev(latency)

    # Print latency statistics
    throughput = sum(final_length) - sum(length)

    print("Total request: ", len(requests))

    print("------------------------")
    print("total gpt_time", sum(gpt_time))
    print("avg gpt_time", sum(gpt_time)/len(gpt_time))
    print("max gpt_time", max(gpt_time))
    print("min gpt_time", min(gpt_time))

    print("------------------------")
    print("Average Latency: ", avg_latency)
    print("Max Latency: ", max_latency)
    print("Min Latency: ", min_latency)
    print("Standard Deviation: ", std_dev)

    print("------------------------")
    print("throughput: ", throughput/total_time)
    print("total time: ", total_time)
    print("token generated: ", throughput)


if __name__ == "__main__":
    main()
