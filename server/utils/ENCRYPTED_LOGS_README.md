# Encrypted Server Logs

## Overview
This system encrypts server logs from the FastAPI/uvicorn application before storing them on disk. 
Logs are encrypted using Fernet symmetric encryption (from the cryptography library) and stored in 
rotating log files to manage disk space.

## Configuration
Configure the logging system through environment variables in `.env`:

- `LOG_DIR`: Directory to store encrypted log files (default: './logs')
- `LOG_ENCRYPTION_KEY_PATH`: Path to store the encryption key (default: 'log_encryption.key')
- `LOG_LEVEL`: Logging level (default: INFO)

## Viewing Logs
Logs are encrypted on disk and cannot be read directly. To view logs, use the decryption utility:

```
# View logs in console
python utils/decrypt_logs.py /path/to/logs/server.log

# Write decrypted logs to a file
python utils/decrypt_logs.py /path/to/logs/server.log -o decrypted_logs.txt

# Use a specific key file
python utils/decrypt_logs.py /path/to/logs/server.log -k /path/to/key/file
```

## Security Notes
- Keep the encryption key secure. Anyone with access to the key can decrypt the logs.
- The key is automatically generated if it doesn't exist.
- For production, store the key in a secure location separate from the logs.
- Logs in memory and console output are not encrypted, only the persistent storage is encrypted.
