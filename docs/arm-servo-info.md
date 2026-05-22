# WeArm Robotic Arm Servo Control Guide

## Hardware Parameters

| Parameter | Value |
|------|-----|
| Model | WeArm (older version) |
| Communication | PWM text protocol (CH340 USB-to-serial) |
| Baud Rate | 115200 |
| PWM Range | 500 ~ 2500 |
| Neutral Value | 1500 (neutral_value) |

## Servo Definitions

| ID | Name | Axis | Description |
|----|------|------|------|
| S0 | Base | Vertical rotation | Controls overall left-right rotation, approximately 270-degree range |
| S1 | Upper arm | Pitch | Determines the forward/backward pitch angle of the arm; vertical upward at 1500 |
| S2 | Forearm | Pitch | Assists the upper arm in controlling the pitch angle |
| S3 | Wrist | Pitch | Controls the up-down pitch of the wrist |
| S4 | Wrist | Rotation | Controls wrist rotation |
| S5 | Gripper | Open/close | Controls gripper opening/closing |

## PWM and Angle Relationship

- **S1 (Upper arm)**: At neutral position 1500, the arm points vertically upward. Moving from 1500 toward 500 or 2500, the arm rotates from front to back.
- **S0 (Base)**: Controls overall left-right rotation; centered at 1500.

## Stamping Motion Sequence

The stamping motion is executed in three phases:

```
Phase 1: Neutral → Position 1
  - S1: 1500 → 920  (upper arm tilts forward)
  - S2: 1500 → 1655 (forearm follows)
  - Duration: 800ms

Phase 2: Press down
  - S3: 1500 → 1630 (wrist presses down)
  - Duration: 600ms

Phase 3: Lift and return to neutral
  - All servos → 1500
  - Duration: 800ms
```

Key values:
- `STAMP_POS1 = {0:1500, 1:920, 2:1655, 3:1500, 4:1500, 5:1500}`
- `STAMP_WRIST_DOWN = 1630` (wrist press-down target)
- `STAMP_DOWN_PWM = 2400` (upper arm press-down force)
- `STAMP_UP_PWM = 800` (upper arm lift)
- `STAMP_WRIST_DOWN_PWM = 1200` (wrist press-down)
- `STAMP_WRIST_UP_PWM = 1700` (wrist lift)

## Calibration Page Test

On the `/calibration` calibration page, clicking the "Test Stamp" button executes the complete stamping sequence.

## Related Files

- `hardware/wearm.py` - WeArm controller implementation
- `api/calibration.py` - Calibration API endpoint
- `config.py` - Serial port configuration (SERIAL_PORT, SERIAL_BAUD)
