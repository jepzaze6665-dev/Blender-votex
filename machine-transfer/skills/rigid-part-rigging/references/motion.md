# Motion for rigid characters

A stiff body reads through timing, so exaggerate. Angles that look wild in a single frame look right in play. Values assume 24 fps.

## Principles

- **Pose to pose:** key strong poses and let the curve fill in. Three to five keys per clip per bone is enough.
- **Fast in, slow out:** attacks move in 2 to 4 frames and recover in 8 or more.
- **Anticipation:** move opposite the action first. A strike without a windup reads as a twitch.
- **Follow-through:** the torso leads, then the arm, then the weapon. Offset keys by a frame.
- **Bounce:** rigid bodies gain life from vertical motion. Root or torso rises on the passing pose.
- **Opposites:** the left arm swings with the right leg, and the torso twists against the hips.

## Starting values

| Clip | Frames | Notes |
|---|---|---|
| Idle | 48, loop | Torso bob 1 to 3 cm, arms sway 3 to 6 degrees, head lags by a few frames |
| Walk | 16 to 20, loop | Legs ±30 to 40 degrees, arms opposite at ±25 to 35, two bounces per cycle, slight torso yaw |
| Run | 12 to 14, loop | Legs ±55, torso leans forward 10 to 15, bigger bounce |
| Attack | 14 to 20, once | Windup 4 frames, strike 3 to 4, hold 1 to 2, recover 8 or more |
| Hit | 8 to 10, once | Torso snaps back 15 to 25, returns with a small overshoot |

For a walk, the last key must equal the first. Check both ends of every loop.

## Cast clips

Give each major skill its own clip instead of reusing an attack. Time the pose to the effect: start the effect on the planted or released frame, and land a slam on the impact frame. Block normal attacks during a cast so it cannot be cut off. A full-body jump can live in the clip when it does not need real physics.

## Game feel

Part of the impact belongs to the engine, not the clip: hit-stop of 50 to 90 ms, screen shake, a flash, and knockback. Tune these with the clip rather than making the animation carry all of it.
