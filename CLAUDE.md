# pycozmo (amnuts fork)

A fork of [zayfod/pycozmo](https://github.com/zayfod/pycozmo), which has been
unmaintained since August 2022 and has open pull requests that will not be
merged. Upstream describes itself as "unstable and heavily under development",
and that is accurate — treat it as a reverse-engineering tool rather than a
finished SDK.

## Branches

- `main` — upstream's `master`, renamed. Do not commit here.
- `develop` — all work. This is what consumers pin to.

## What this fork adds

Merged from upstream pull requests:

- [#56](https://github.com/zayfod/pycozmo/pull/56) — `drive_off_charger_contacts`,
  `drive_straight`, `turn_in_place`, `turn_in_place_at_speed`, charger events.
- [#55](https://github.com/zayfod/pycozmo/pull/55) — `enable_jpeg_decoding=False`
  for undecoded camera frames.
- [#48](https://github.com/zayfod/pycozmo/pull/48) — `display_image` duration fix,
  camera matrix and saved cube IDs. **Adds opencv-python as a dependency.**

Our own fixes: raw camera frames return JPEG bytes rather than a numpy array;
debug prints removed from the NV storage handler; usage messages for
`pycozmo_dump` and `pycozmo_replay` instead of `IndexError`; the u-law overflow
below.

## Do not "correct" the u-law encoder

`audio.u_law_encoding` composes the standard byte and then does **not** invert
it, which means it disagrees with `audioop.lin2ulaw` on every sample. This looks
like an obvious bug. It is not.

Cozmo's firmware expects the un-inverted form. Encoding to the ITU standard was
tried on hardware and made every sound badly distorted. The code carries a
comment saying so; leave it alone.

The one genuine defect there was `-(~x)`, which evaluates to `x + 1` and reaches
256 for full-scale negative samples — raising `byte must be in range(0, 256)` and
crashing playback on loud audio. That is clamped now, leaving every other sample
byte-for-byte unchanged.

## Python version

**3.10.** `pycozmo/audio.py` imports `chunk` and consumers commonly use
`audioop`; both were removed in Python 3.13. Upstream issue #69 covers this.
Raising the floor means finding replacements first.

## Architecture worth knowing

The robot is reached over **UDP at `172.31.1.1:5551`** across its own Wi-Fi
access point. Bluetooth links the robot to its cubes, never to the computer.

`Connection` is a `Thread` with separate send and receive threads, pinging at
2Hz. There is **no disconnect event** — absence of `RobotState` packets is the
only signal a link has dropped.

`AnimationController` runs its own thread draining a queue at 30fps. Each frame
is a triple of `(audio, image, packets)` sent together, so face and voice can
play simultaneously — but `play_anim_ppclip` passes `None` for audio on every
frame, so `play_audio` queues *behind* an animation rather than with it. Both
only enqueue; neither waits for playback. `cancel_anim()` empties the whole
queue, discarding any audio still to play.

Animation clips contain body motion, emitted as `DriveWheels`, `AnimBody` or
`TurnInPlaceAtSpeed` depending on the keyframe's radius. There is no way to
disable that track: `enabled_anim_tracks` is reported *by* the robot, not set by
the client.

Roughly 5% of clips fail to preprocess under current Pillow, raising
`ValueError: y1 must be greater than or equal to y0` while rendering procedural
faces.

## Consumers

[amnuts/cozmo-bridge](https://github.com/amnuts/cozmo-bridge) pins a commit of
`develop` and uses these internals: `_clip_metadata`, `_ppclips`, `_clips`,
`_load_clips`, `_next_anim_id`, `anim_controller`. Changing them is a breaking
change even though they are private.

## Verifying

The robot is the authority, not the specification it appears to implement. The
u-law episode above is the cautionary example: a change verified against
`audioop` and the ITU standard was still wrong on hardware. State plainly what
was tested on a real Cozmo and what was not.
