#!/usr/bin/env python3
"""
File Hash Calculator

Calculates cryptographic hashes (MD5, SHA256, SHA512) of files for integrity
verification and duplicate detection.

This script demonstrates mandatory script execution - AI cannot compute
cryptographic hashes directly and must execute this script.
"""

import hashlib
import sys
from pathlib import Path
from datetime import datetime
import argparse
from typing import List, Dict


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def calculate_hashes(file_path: Path, algorithms: List[str]) -> Dict[str, str]:
    """
    Calculate cryptographic hashes for a file.

    Args:
        file_path: Path to the file to hash
        algorithms: List of hash algorithms to use (md5, sha256, sha512)

    Returns:
        Dictionary mapping algorithm names to hash values
    """
    # Initialize hash objects
    hash_objects = {}
    for algo in algorithms:
        algo_lower = algo.lower()
        if algo_lower == 'md5':
            hash_objects['MD5'] = hashlib.md5()
        elif algo_lower == 'sha256':
            hash_objects['SHA256'] = hashlib.sha256()
        elif algo_lower == 'sha512':
            hash_objects['SHA512'] = hashlib.sha512()
        else:
            print(f"Warning: Unknown algorithm '{algo}', skipping", file=sys.stderr)

    if not hash_objects:
        raise ValueError("No valid hash algorithms specified")

    # Read file in chunks and update all hash objects
    chunk_size = 8192  # 8KB chunks
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                for hash_obj in hash_objects.values():
                    hash_obj.update(chunk)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {str(e)}")

    # Return hexadecimal digest for each algorithm
    return {name: hash_obj.hexdigest() for name, hash_obj in hash_objects.items()}


def hash_file(file_path: Path, algorithms: List[str]) -> None:
    """
    Hash a single file and print formatted results.

    Args:
        file_path: Path to the file to hash
        algorithms: List of hash algorithms to use
    """
    try:
        # Get file metadata
        stat = file_path.stat()
        size = format_size(stat.st_size)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        # Calculate hashes
        hashes = calculate_hashes(file_path, algorithms)

        # Print formatted output
        print("\n" + "=" * 60)
        print(f"File: {file_path.name}")
        print(f"Path: {file_path}")
        print(f"Size: {size}")
        print(f"Modified: {modified}")
        print("\n--- Hashes ---")

        for algo_name, hash_value in sorted(hashes.items()):
            print(f"{algo_name:8s}: {hash_value}")

        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError processing {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the hash calculator."""
    parser = argparse.ArgumentParser(
        description='Calculate cryptographic hashes of files',
        epilog='Example: python hash_file.py file.txt --algo sha256,md5'
    )

    parser.add_argument(
        'files',
        nargs='+',
        help='File(s) to hash (supports glob patterns)'
    )

    parser.add_argument(
        '--algo',
        '--algorithm',
        dest='algorithms',
        default='md5,sha256,sha512',
        help='Comma-separated list of algorithms: md5, sha256, sha512 (default: all)'
    )

    args = parser.parse_args()

    # Parse algorithms
    algorithms = [algo.strip() for algo in args.algorithms.split(',')]

    # Validate at least one algorithm
    valid_algorithms = {'md5', 'sha256', 'sha512'}
    if not any(algo.lower() in valid_algorithms for algo in algorithms):
        print("Error: No valid algorithms specified. Use: md5, sha256, or sha512", file=sys.stderr)
        sys.exit(1)

    # Process each file
    file_paths = []
    for file_pattern in args.files:
        path = Path(file_pattern)
        if path.exists() and path.is_file():
            file_paths.append(path)
        else:
            # Try glob expansion
            parent = path.parent if path.parent.exists() else Path('.')
            matches = list(parent.glob(path.name))
            file_paths.extend([p for p in matches if p.is_file()])

    if not file_paths:
        print("Error: No valid files found", file=sys.stderr)
        sys.exit(1)

    # Process each file
    for file_path in file_paths:
        hash_file(file_path, algorithms)

    # Summary if multiple files
    if len(file_paths) > 1:
        print(f"\nProcessed {len(file_paths)} file(s)")


if __name__ == '__main__':
    main()
