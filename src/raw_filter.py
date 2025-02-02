import argparse
import os
import colorama
import datetime
colorama.init()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    print(colorama.Fore.GREEN + f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Filtering raw data..." + colorama.Fore.RESET)

    with open(args.input, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            
            if len(line.strip()) == 0:
                continue

            if line.strip() == "":
                continue

            parsed_line = line.strip().split(" ")
            target_is = parsed_line[0]
            
            with open(args.output, "a") as f_out:
                f_out.write(f"{target_is}\n")

    print(colorama.Fore.GREEN + f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Filtering raw data done." + colorama.Fore.RESET)

if __name__ == "__main__":
    main()
