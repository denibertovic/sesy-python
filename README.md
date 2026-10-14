# SESY Python SDK

Python client library for the SESY email service.

## Installation

```bash
uv add sesy
```

Or with pip:

```bash
pip install sesy
```

## Quick Start

```python
from sesy import SesyClient

client = SesyClient(api_key="your-api-key")

# Send an email
response = client.send_email(
    to="user@example.com",
    subject="Hello",
    html="<h1>Welcome!</h1>",
)
print(f"Message ID: {response.message_id}")

# Check message status
message = client.get_message(response.message_id)
print(f"Status: {message.status}")
```

## Async Support

```python
from sesy import AsyncSesyClient

async with AsyncSesyClient(api_key="your-api-key") as client:
    response = await client.send_email(
        to="user@example.com",
        template="welcome",
        data={"name": "John"},
    )
```

## API Methods

- `send_email()` - Send an email
- `get_message()` - Get message details
- `list_suppressions()` - List suppressed emails
- `add_suppression()` - Add email to suppression list
- `get_limits()` - Get rate limit status
