# TARS — Smart Transport And Retrieval System

**TARS** is an autonomous rover with a camera-guided robotic arm. Give it a command — `start`, `stop`, or the name of an object — and it will scan its surroundings, identify the target, drive up to it, pick it up with a 4-DoF arm, and return it to its starting point.

It combines a car-like mobile base, real-time object detection (YOLOv5s) and inverse-kinematics-based manipulation on a low-cost **Raspberry Pi Zero 2 W** platform.

> Senior Design Project (CSE499B) · Department of Electrical and Computer Engineering · North South University · Spring 2025

---

## Links

| | |
|---|---|
| 🌐 Demo website | https://trulyfalse.github.io/Autonomous-Rover-CSE499/ |
| 📄 Final report | [Google Drive](https://drive.google.com/file/d/1x4nU5dVO1PKBptkkQc-nvLlIwuIzyJZN/view?usp=sharing) |

## Features

- **Voice-free, web-based control:** start/stop detection and choose a target object from a browser UI.
- **Real-time object detection:** YOLOv5s trained on a custom dataset (paper ball, eraser, paper cup).
- **Search by rotation:** the rover performs repeated 360° scans until the target is found, then aligns to it.
- **Proximity-aware approach:** an HC-SR04 ultrasonic sensor stops the rover about 10 cm from the object.
- **Inverse-kinematics grasping:** joint angles for the 4-DoF arm are computed so the claw points down at the object.
- **Closed-loop return:** the object is carried back to the start point and placed down.
- **Emergency stop:** a stop command can interrupt the process at any time.

## How it works

1. **Choose the object** — the user presses *Start Detection* and picks a target in the web UI.
2. **Align toward it** — the rover scans in place until YOLOv5s detects the target, then lines up with it.
3. **Approach** — it drives forward until the distance sensor reads about 10 cm.
4. **Grasp** — inverse kinematics computes the servo angles; the arm swings down and the claw closes.
5. **Return & release** — the rover drives back to its start position and puts the object down.

### Software architecture

TARS uses a two-tier Flask architecture over a local network:

| Laptop (Flask server) | Raspberry Pi Zero 2 W (Flask server) |
|---|---|
| Hosts the web UI | Streams camera video |
| Runs YOLOv5s detection | Drives motors and servos through GPIO |
| Sends commands to the Pi | Reads the distance sensor |

Commands travel from the laptop UI to the Pi; the processed video stream is relayed back so detection and robot actions can be monitored live.

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi Zero 2 W | Onboard computer: sensors, actuators, video streaming |
| Raspberry Pi Camera Rev 1.3 (5 MP) | Video frames for detection |
| 4× SG90 micro servos | Joints of the 4-DoF arm |
| 4× BO DC motors | Four-wheel drive base |
| L293D motor driver shield | Motor speed and direction control |
| HC-SR04 ultrasonic sensor | Distance measurement / obstacle range |
| 5000 mAh power bank + 3× 18650 Li-ion cells | Pi power; motor and servo power |

## Software & tools

- **Ultralytics (YOLOv5s)** — model training and inference
- **Roboflow** — dataset labeling and augmentation
- **Flask** (Python) — laptop and Raspberry Pi servers
- **VNC Viewer** — headless access to the Raspberry Pi
- **DroidCam** — phone camera as a webcam for testing

## Model & results

YOLOv5s was trained for 25 epochs on 3,000+ labeled 640×640 images (70:20:10 train/validation/test split) with augmentation (flips, rotations, cropping, shear, hue shifts, blur, noise) and a background class to avoid false positives on look-alike objects.

| Class | Labels | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|---:|
| **All** | 149 | 0.970 | 0.922 | 0.978 | 0.680 |
| Cup | 22 | 0.978 | 0.955 | 0.992 | 0.742 |
| Eraser | 52 | 1.000 | 0.826 | 0.953 | 0.575 |
| Paper ball | 75 | 0.933 | 0.987 | 0.991 | 0.724 |

Evaluated on 100 images (149 labels).

## Limitations & future work

**Limitations**
- Detection quality depends on the diversity of the training data and on lighting.
- Arm reach, payload and degrees of freedom limit the objects it can handle.
- The Pi Zero's limited processing power can add latency.
- The system needs careful calibration and is not yet suited to safety-critical tasks.

**Future work**
- Room mapping and path planning for autonomous navigation.
- Voice command support and other human-robot interaction methods.

## Demo website

The `index.html`, `style.css`, `script.js` and `assets/` files make up a static, frontend-only project website (plain HTML/CSS/JS, no build step) hosted with GitHub Pages:

**https://trulyfalse.github.io/Autonomous-Rover-CSE499/**

To preview it locally:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Team

- Abrar Ur Alam
- Hasan Bin Omar
- Mahbub Mokaddes Akash
- Abdullah Mohammad Muntasir Adnan Jami

**Faculty advisor:** Md. Shahriar Hussain, Senior Lecturer, Department of Electrical and Computer Engineering, North South University

## Acknowledgements

Thanks to the Department of Electrical and Computer Engineering at North South University for facilitating the project, and to Mahamadul Mahin Bablu for his help.
