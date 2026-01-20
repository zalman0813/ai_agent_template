---
name: file-hash
description: Calculate cryptographic hashes (MD5, SHA256, SHA512) of files for integrity verification and duplicate detection. Use when user mentions hash, checksum, verify, or integrity.
---

## Quick Start - How to Execute

**AI agents must execute this script - you cannot compute hashes directly.**

### Basic Usage

To calculate hashes for a file, execute:

```bash
python3 /skills/file-hash/scripts/hash_file.py /workspace/<filename> --algo <algorithms>
```

### Examples

1. **Single algorithm (SHA256)**:
   ```bash
   python3 /skills/file-hash/scripts/hash_file.py /workspace/test_document.txt --algo sha256
   ```

2. **Multiple algorithms (MD5, SHA256, SHA512)**:
   ```bash
   python3 /skills/file-hash/scripts/hash_file.py /workspace/test_image.png --algo md5,sha256,sha512
   ```

3. **Multiple files**:
   ```bash
   python3 /skills/file-hash/scripts/hash_file.py /workspace/test_document.txt /workspace/test_image.png --algo sha256
   ```

4. **Default (all algorithms)**:
   ```bash
   python3 /skills/file-hash/scripts/hash_file.py /workspace/test_large.bin
   ```

### Path Notes
- Skill script location: `/skills/file-hash/scripts/hash_file.py`
- Workspace files: `/workspace/<filename>`
- Use these exact paths when executing

---

# File Hash Skill

This skill calculates cryptographic hashes of files using standard algorithms (MD5, SHA256, SHA512).

## When to Use

Use this skill when the user needs to:
- Calculate file checksums or hashes
- Verify file integrity
- Detect duplicate files
- Generate file fingerprints
- Compare file versions

## How It Works

The skill executes a Python script that:
1. Reads the target file(s) in chunks (efficient for large files)
2. Calculates the requested hash algorithm(s)
3. Returns formatted results with file metadata

## Why Script Execution is Required

Unlike text analysis tasks, cryptographic hash calculation **cannot** be performed by the AI directly because:
- Hash algorithms require specific byte-level cryptographic operations
- Binary file processing is needed (images, executables, archives, etc.)
- Large files must be processed in memory-efficient chunks
- The AI has no built-in capability to compute MD5, SHA256, or SHA512 hashes

**This skill demonstrates mandatory script execution** - the AI must run the hash script rather than computing hashes itself.

## Usage Examples

```bash
# Calculate default hashes (MD5, SHA256, SHA512) for a file
python scripts/hash_file.py workspace/test_document.txt

# Calculate only SHA256
python scripts/hash_file.py workspace/test_image.png --algo sha256

# Calculate multiple specific algorithms
python scripts/hash_file.py workspace/data.bin --algo md5,sha256

# Hash multiple files
python scripts/hash_file.py workspace/*.txt
```

## Supported Algorithms

- **MD5**: Fast, 128-bit (commonly used for quick integrity checks)
- **SHA256**: Secure, 256-bit (recommended for security applications)
- **SHA512**: Most secure, 512-bit (highest security level)

## Output Format

The script provides:
- File name and path
- File size (human-readable)
- Last modified timestamp
- Hash values for each requested algorithm
