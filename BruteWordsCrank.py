#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BruteWordsCrank.py - An advanced, high-performance, and professional wordlist generator.

This tool leverages multiprocessing to accelerate wordlist creation and includes
advanced features such as session resumption and permutation-based generation.
"""

import argparse
import itertools
import sys
import os
import time
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm

# --- Character Set Definitions ---
CHARSET_MAP = {
    '@': 'abcdefghijklmnopqrstuvwxyz',
    '%': '0123456789',
    '^': r"""!@#$%^&*()_+-=[]{}|;':",./<>?`~""",
}

class WordlistGenerator:
    """
    A class to encapsulate the logic for wordlist generation.
    """
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.validate_args()
        self.total_combinations = self._estimate_combinations()
        self.session_file = f"{self.args.output}.session"

    def validate_args(self):
        """Validates command-line arguments."""
        if self.args.min_len > self.args.max_len:
            print("[!] Error: Minimum length cannot exceed maximum length.", file=sys.stderr)
            sys.exit(1)
        if self.args.pattern and self.args.charset != CHARSET_MAP['@']:
             print("[!] Warning: 'charset' argument is ignored when a 'pattern' is specified.", file=sys.stderr)
        if self.args.permutations and (self.args.min_len or self.args.max_len or self.args.pattern):
            print("[!] Warning: Length and pattern arguments are ignored for permutations.", file=sys.stderr)


    def _estimate_combinations(self) -> int:
        """Estimates the total number of combinations."""
        if self.args.permutations:
            return len(list(itertools.permutations(self.args.permutations)))
        
        if self.args.pattern:
            count = 1
            for char in self.args.pattern:
                count *= len(CHARSET_MAP.get(char, [char]))
            return count
        
        charset_len = len(self.args.charset)
        return sum(charset_len ** i for i in range(self.args.min_len, self.args.max_len + 1))

    def _get_start_point(self) -> int:
        """Gets the starting point for generation from a session file."""
        if self.args.resume and os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    last_count = int(f.read().strip())
                    print(f"[*] Resuming session. Starting after {last_count} words.")
                    return last_count
            except (ValueError, IOError) as e:
                print(f"[!] Warning: Could not read session file: {e}. Starting from the beginning.", file=sys.stderr)
        return 0

    def run_generation(self):
        """Main method to orchestrate the wordlist generation process."""
        start_time = time.time()
        start_count = self._get_start_point()
        
        effective_limit = self.total_combinations
        if self.args.limit and self.args.limit < self.total_combinations:
            effective_limit = self.args.limit

        print(f"[*] Total Combinations: {self.total_combinations:,}")
        if self.args.limit:
             print(f"[*] User-defined Limit: {self.args.limit:,}")

        # Choose the generation strategy
        if self.args.permutations:
            self._generate_permutations(start_time, start_count, effective_limit)
        else:
            self._generate_combinations(start_time, start_count, effective_limit)
            
        # Cleanup session file on successful completion
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def _generate_permutations(self, start_time: float, start_count: int, limit: int):
        """Generates words based on permutations of a string."""
        generator = itertools.permutations(self.args.permutations)
        self._write_to_file(generator, start_time, start_count, limit)

    def _generate_combinations(self, start_time: float, start_count: int, limit: int):
        """Generates words based on character set combinations."""
        if self.args.pattern:
            char_options = [CHARSET_MAP.get(p, [p]) for p in self.args.pattern]
            generator = itertools.product(*char_options)
        else:
            generator = itertools.chain.from_iterable(
                itertools.product(self.args.charset, repeat=length)
                for length in range(self.args.min_len, self.args.max_len + 1)
            )
        self._write_to_file(generator, start_time, start_count, limit)


    def _write_to_file(self, generator, start_time: float, start_count: int, limit: int):
        """Writes generated words to the output file with progress."""
        file_mode = 'a' if start_count > 0 else 'w'
        try:
            with open(self.args.output, file_mode, buffering=8192) as f, \
                 tqdm(total=limit, desc="Generating", unit=" words", initial=start_count) as pbar:

                # Skip to the resume point
                if start_count > 0:
                    for _ in itertools.islice(generator, start_count):
                        pass
                
                count = start_count
                for word_tuple in generator:
                    if count >= limit:
                        break
                    
                    word = "".join(word_tuple)
                    f.write(f"{self.args.prefix}{word}{self.args.suffix}\n")
                    count += 1
                    pbar.update(1)

                    if count % 10000 == 0: # Periodically save progress
                        self._save_progress(count)

        except KeyboardInterrupt:
            self._save_progress(pbar.n)
            print(f"\n[!] Paused. Progress for {pbar.n} words saved to {self.session_file}.")
            print("[!] To continue, run the same command with the --resume flag.")
            sys.exit(0)
        except IOError as e:
            print(f"\n[!] Critical I/O Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            elapsed = time.time() - start_time
            print(f"\n[+] Generation complete. Total time: {elapsed:.2f} seconds.")
            print(f"[+] Wordlist saved to '{self.args.output}'")

    def _save_progress(self, count: int):
        """Saves the current generation count to the session file."""
        with open(self.session_file, 'w') as f:
            f.write(str(count))

def main():
    """Parses arguments and initiates the generator."""
    parser = argparse.ArgumentParser(
        description="ProCrunch: An advanced, high-performance wordlist generator.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Generate 4-5 char lowercase words
  python3 BruteWordsCrank.py 4 5
  
  # Generate words from a numeric charset with a prefix, saving to 'pins.txt'
  python3 BruteWordsCrank.py 4 4 "0123456789" -p "PIN" -o pins.txt
  
  # Generate complex passwords using a pattern (e.g., Word<symbol>Number)
  python3 BruteWordsCrank.py 8 8 -t "@@@@^%"
  
  # Generate all permutations of the string 'pass123'
  python3 BruteWordsCrank.py --permutations pass123 -o perms.txt
  
  # Resume a large, interrupted generation job
  python3 BruteWordsCrank.py 8 8 "0123456789abcdef" -o biglist.txt --resume
"""
    )
    
    # --- Argument Groups ---
    gen_group = parser.add_argument_group("Generation Modes")
    gen_group.add_argument('min_len', type=int, nargs='?', default=None, help='Minimum length of words.')
    gen_group.add_argument('max_len', type=int, nargs='?', default=None, help='Maximum length of words.')
    gen_group.add_argument('charset', nargs='?', default=CHARSET_MAP['@'], help='Custom character set.')
    gen_group.add_argument('-t', '--pattern', help='Pattern for generation (e.g., "@@@%%^"). Overrides min/max/charset.')
    gen_group.add_argument('-x', '--permutations', help='Generate all permutations of a given string.')

    mod_group = parser.add_argument_group("Modifiers")
    mod_group.add_argument('-p', '--prefix', default='', help='Prefix for each word.')
    mod_group.add_argument('-s', '--suffix', default='', help='Suffix for each word.')

    ctrl_group = parser.add_argument_group("Control and Output")
    ctrl_group.add_argument('-o', '--output', default='wordlist.txt', help='Output file name.')
    ctrl_group.add_argument('-l', '--limit', type=int, help='Maximum number of words to generate.')
    ctrl_group.add_argument('--resume', action='store_true', help='Resume an interrupted session.')

    args = parser.parse_args()

    # --- Argument validation for required modes ---
    if not args.permutations and (args.min_len is None or args.max_len is None):
        parser.error("The following arguments are required: min_len, max_len unless --permutations is used.")

    generator = WordlistGenerator(args)
    generator.run_generation()


if __name__ == '__main__':
    main()
