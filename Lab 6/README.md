# Distributed Interaction

**NAMES OF COLLABORATORS HERE: Gal Alon, Stephen Monahan, Jonathan Sharpy**

---

## Part A: MQTT Messaging

**💡 Brainstorm 5 ideas for messaging between devices**

1. Roommate presence board: Each room has a Pi with a proximity sensor that publishes when someone is there. A display by the door shows which rooms are in use.

2. Laundry done alert: A Pi on the washing machine senses vibration. When the shaking stops, it publishes "done" and a Pi in your room beeps.

3. Shared mood lamp: Each friend picks a color on their Pi. Every Pi subscribes to the others and shows a mix of everyone's colors, so you can see how the group is feeling.

4. Study focus check: A Pi at each desk publishes motion. If one person has been away for a while but their friends are still working, their Pi sends a nudge to come back.

5. Apartment doorbell: A button Pi at the front door publishes "ring." Every other Pi in the apartment flashes its screen or plays a sound, so you hear it from any room.
   
---

## Part B: Collaborative Pixel Grid


**📸 Include: Screenshot of grid + photo of your Pi setup**

<img width="488" height="652" alt="Screenshot 2026-11-04 at 6 20 46 PM" src="https://github.com/user-attachments/assets/ff717afd-f254-48c1-87b6-b0a0bc176e01" />

---

## Part C: Make Your Own

### Deliverables

Replace this README with your documentation:

**1. Project Description**

NEON RACE is a reaction game for 3 Raspberry Pis. Every round, all three screens show the same task at the same time, like SHOW RED or HAND CLOSE (or PEACE SIGN and THUMBS UP when a webcam is attached). The first player to do the task with their sensor wins the round. After 5 rounds, the player with the most wins is the champion.

It is interesting because the game only works when all three devices stay in sync over the network. Each Pi senses its own player, but one Pi has to decide the winner fairly. For the user, it feels like a fast arcade game: a countdown, a task, a race, and a scoreboard on every screen.

To keep it fair, players must release first and then hold the task for a short moment. This stops someone from winning by just leaving their hand over the sensor before the round starts.

**2. Architecture Diagram**
<img width="656" height="425" alt="Screenshot 2026-11-08 at 3 16 09 PM" src="https://github.com/user-attachments/assets/9428b8c9-81f8-48ea-804c-cfdf0fffebf6" />

* Input: APDS-9960 on each Pi (color and proximity), optional USB webcam (hand gestures)
* Computation: each Pi checks its own sensor and times its own reaction; the host Pi picks tasks, collects times, and keeps score
* Output: Mini PiTFT screen on every Pi shows the task, countdown, and scoreboard

**3. Build Documentation**
Photos of each Pi + sensors:
<img width="4284" height="5712" alt="IMG_0789" src="https://github.com/user-attachments/assets/e5ecd588-a4b9-4894-96a4-8464078b2793" />
<img width="361" height="346" alt="Screenshot 2026-11-08 at 3 21 26 PM" src="https://github.com/user-<img width="298" height="234" alt="Screenshot 2026-11-08 at 3 23 15 PM" src="https://github.com/user-attachments/assets/d988d2ff-b6f6-4a00-9985-f03b5e060219" />
attachments/assets/4bde4580-d127-4793-a6fb-8c9f79864610" /><img width="181" height="165" alt="Screenshot 2026-11-08 at 3 22 55 PM" src="https://github.com/user-attachments/assets/5cf10534-365e-4a34-9114-b56621a651f8" />

To run the game, the host Pi starts with `python neon_race.py --host --name pi1`, and the other two Pis run `python neon_race.py --name pi2` and `python neon_race.py --name pi3`. A Pi without a webcam adds `--no-camera`. The host presses the top button on its screen to start the match. If some Pis do not have a webcam, the game automatically only uses tasks that every Pi can do, which are the color tasks and HAND CLOSE.

All of our MQTT topics live under `IDD/stephen-neon/race/`. Every Pi publishes to `hello` every few seconds to say it is online and which tasks its sensors can handle. The host publishes the next round's task on `prepare`, and each Pi answers on `ready` once its sensors are ready. When every Pi is ready, the host publishes `go` to start the countdown. When a player finishes, their Pi publishes to `done` with how long it took. The host then publishes the round winner and scores on `result`, and uses `state` for lobby updates, the scoreboard, and the final champion. Each Pi also publishes live sensor readings on `sensor/<name>`, which was helpful for debugging.

The first important piece of code turns raw RGB values from the sensor into "red," "green," or "blue." It only counts a color if one channel is clearly stronger than the others, so white light or mixed colors are ignored instead of being guessed.

```python
peak = max(values)
if peak < ordered[1] * 1.35 or peak / max(sum(values), 1) < .43:
    return None
return ("red", "green", "blue")[values.index(peak)]
```

The second piece is the release first, then hold rule. A player first has to not match the task, which arms them. Then they have to match the task and hold it for 0.35 seconds before their Pi sends a finish message with their time.

```python
if not matches:
    self.armed = True
    ...
if not self.armed:
    self.note = "Release first, then do it!"
    return
self.progress = (stamp - self.hold_since) / 0.35
if self.progress >= 1.0:
    elapsed = now - self.go_at
    self.send("done", self.packet(task=self.task, elapsed=round(elapsed, 4)))
```

The third piece is how the host picks the winner. Each Pi measures how long it took on its own clock and sends that number, instead of the host judging by which message arrived first. The host compares the times, and anyone within 0.08 seconds of the best time counts as a tie, since differences that small are too close to call with the sensors we used.

```python
best = min(self.answers.values())
self.winners = sorted(p for p, elapsed in self.answers.items()
                      if elapsed - best <= 0.08000001)
```

**4. User Testing**
- **Test with 2+ people NOT on your team**
- Photos/video of use
- What did they think before trying?
- What surprised them?
- What would they change?

**5. Reflection**
- What worked well?
- Challenges with distributed interaction?
- How did sensor events work?
- What would you improve?
- Where did computation happen in your system, and why there? (If you used a language model: did it run on every event, or only at setup?)

---

**Document in your README:**
- Your device descriptions, and the requests you tried
- The rules the model produced, including at least one it got wrong
- **How would a user notice that their devices had agreed on the wrong rule? How would they fix it?**

---

## Code Files

**Server files:**
- `app.py` - Pixel grid server (Flask + WebSocket + MQTT)
- `mqtt_viewer.py` - MQTT message viewer for debugging
- `mqtt_bridge.py` - MQTT → WebSocket bridge
- `requirements-server.txt` - Server dependencies

**Pi files:**
- `pixel_grid_publisher.py` - Example (RGB sensor → MQTT)
- `requirements-pi.txt` - Pi dependencies

**Web interface:**
- `templates/grid.html` - Pixel grid display
- `templates/controller.html` - Color picker
- `templates/mqtt_viewer.html` - Message viewer

---

## Debugging Tools

**MQTT Message Viewer:** `http://farlab.infosci.cornell.edu:5001`
- See all MQTT messages in real-time
- View topics and payloads
- Helpful for debugging your own projects

**Command line:**
```bash
# See all IDD messages
mosquitto_sub -h farlab.infosci.cornell.edu -p 1883 -t "IDD/#" -u idd -P "device@theFarm"
```

---

## Troubleshooting

**MQTT:** Broker `farlab.infosci.cornell.edu:1883`, user `idd`, pass `device@theFarm`

**Sensor:** Check `i2cdetect -y 1`, APDS-9960 at `0x39`

**Grid:** Verify server running, check MQTT in console, test with web controller

**Pi venv:** Make sure to activate: `source .venv/bin/activate`


---

## Submission Checklist

Before submitting:
- [ ] Delete prep/instructions above
- [ ] Add YOUR project documentation
- [ ] Include photos/videos/diagrams  
- [ ] Document user testing with non-team members
- [ ] Add reflection on learnings
- [ ] List team names at top

**Your README = story of what YOU built!**

---

Resources: [MQTT Guide](https://www.hivemq.com/mqtt-essentials/) | [Paho Python](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php) | [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
