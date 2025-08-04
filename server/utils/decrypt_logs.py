#!/usr/bin/env python3
import argparse
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.utils.encrypted_logging import decrypt_log_file

def main():
    parser = argparse.ArgumentParser(description='Decrypt encrypted server log files')
    parser.add_argument('log_file', help='Path to the encrypted log file')
    parser.add_argument('-o', '--output', help='Path to write decrypted logs (default: print to console)')
    parser.add_argument('-k', '--key', help='Path to encryption key file')
    
    args = parser.parse_args()
    
    decrypt_log_file(
        log_file_path=args.log_file,
        output_file_path=args.output,
        key_path=args.key
    )

if __name__ == '__main__':
    main()
