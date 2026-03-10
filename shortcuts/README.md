# Apple Shortcuts for Voice Access

These Shortcuts must be created manually on each iPhone using the Shortcuts app.
See [docs/siri-shortcut-setup.md](../docs/siri-shortcut-setup.md) for step-by-step instructions.

## Shortcuts

| Shortcut | Trigger Phrase | Endpoint | Input Required |
|----------|---------------|----------|----------------|
| Run Our House | "Hey Siri, run our house" | POST /api/v1/voice/message | Yes (Dictate Text) |
| Family Calendar | "Hey Siri, family calendar" | POST /api/v1/voice/preset | No |
| Grocery Add | "Hey Siri, grocery add" | POST /api/v1/voice/preset | Yes (Ask for Input) |
| What's for Dinner | "Hey Siri, what's for dinner" | POST /api/v1/voice/preset | No |
| Remind Me | "Hey Siri, remind me" | POST /api/v1/voice/preset | Yes (Ask for Input) |

## Notes

- Each partner needs their own copy with their unique Bearer token
- Shortcuts sync via iCloud to Apple Watch, iPad, and Mac
- .shortcut export files are not practical for distribution — create manually per setup guide
