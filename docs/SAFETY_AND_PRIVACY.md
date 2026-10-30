# Safety and privacy

## Robot and electrical safety

- Lift the robot so its wheels cannot touch the floor before the first motor test.
- Keep hands, wires and loose clothing away from wheels and gears during movement.
- Use a correctly rated motor supply. Never power motors from Raspberry Pi GPIO pins.
- Verify the L298N board wiring, common ground requirements, GPIO levels and motor polarity against the actual board datasheet.
- Keep a physical way to disconnect motor power. Voice recognition is not an emergency-stop system.
- Stop the robot before changing wiring or camera/audio connections.

## Camera and face data

- Record or stream video only where you have the right to do so and where people have been informed appropriately.
- Obtain consent before enrolling someone's face. Do not upload face images, face vectors or personal captures to a public repository.
- Face files are written under `data/`, which is ignored by Git. Verify `git status` before every public push.
- The included face-matching prototype is not suitable for identification, authentication, access control, attendance or other high-impact decisions.

## Network streaming

- The Flask streaming servers bind to `127.0.0.1` by default.
- Setting `VISIO_HOST=0.0.0.0` allows other devices on the network to reach the server, but the current stream endpoints do not provide login/authentication.
- Do not expose the stream ports through router port-forwarding, a public IP, a public tunnel or an untrusted Wi-Fi network.
- A self-signed TLS certificate encrypts transport but does not establish trusted server identity. Browser certificate warnings are expected.
- For multi-user or remote access, implement authentication, access control, rate limits and a production-grade server / reverse proxy before deployment.

## API credentials

- Store `GROQ_API_KEY` in a local `.env` file or shell environment. Never hard-code or commit API tokens.
- Rotate any token that has ever been committed or shared publicly.
- Error logs should not contain API keys or private user prompts.

## Git publishing checklist

Before pushing:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

Confirm that `.env`, TLS private keys, `data/`, face images, WAV recordings, captured photographs and downloaded model weights are not staged.
