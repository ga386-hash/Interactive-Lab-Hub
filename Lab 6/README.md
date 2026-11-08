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

<img width="4284" height="5712" alt="IMG_0789" src="https://github.com/user-attachments/assets/0a9e27e1-8281-4c84-9258-ff365fd69e19" />


<img width="361" height="346" alt="Screenshot 2026-11-08 at 3 21 26 PM" src="https://github.com/user-attachments/assets/74d45ce4-119a-4181-b91b-909e34b61898" />


<img width="298" height="234" alt="Screenshot 2026-11-08 at 3 23 15 PM" src="https://github.com/user-attachments/assets/70f3a12e-4006-4c0c-b6ba-91f52862506f" />


<img width="181" height="165" alt="Screenshot 2026-11-08 at 3 22 55 PM" src="https://github.com/user-attachments/assets/9e622096-bf02-47c5-88b0-43fb77eb6de5" />



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

The biggest surprise was the release rule. If a player was already holding a color when GO appeared, nothing happened until they pulled away and came back. Both testers thought the game was broken the first time this happened.

They also had trouble with the sensor at first. They held objects too far away, since it only works within a few cm. Some colors like pink, orange, and white were ignored because no single color clearly won. A phone screen showing a solid color worked much better than a notebook.

The best moment was when all three Pis showed GO and then the winner at the same time. Seeing three separate devices react together made the game feel connected.

When we asked what they would change, they wanted clearer instructions at the start, especially about the release rule and how close to hold the object. They also wanted to see everyone’s reaction time after each round, not just the winner’s. They also suggested sound effects for GO, wins, and the final champion, since the Mini PiTFT is small and hard to watch from a distance.


**5. Reflection**

What worked well was the moment all three Pis reacted together. When GO appeared and then the winner showed up on every screen at once, the game felt connected, and it was the part testers enjoyed most. MQTT made this easy since every Pi just subscribed to the same topics.

The main challenge with distributed interaction was making the rules clear across separate devices. Rules that made sense to us, like the release rule and the hold time, confused new players. Timing was also a challenge, since we had to decide what counts as a tie when two players finish almost at once, which is why we used a 0.08 second window.

For sensor events, each Pi read its own APDS-9960 color sensor and checked whether the correct color was held close enough and long enough. A quick flash did not count, and if a player was already holding a color when GO appeared, they had to pull away first. Once a task was completed, the Pi published a message with a timestamp over MQTT.

To improve the game, we would add on-screen instructions at the start, show everyone’s reaction time after each round instead of just the winner, and add sound effects since the Mini PiTFT is small and hard to watch.

Computation happened in two places. Each Pi handled its own sensor reading and color detection locally, so it could react quickly and only send a small message when something happened instead of streaming raw sensor data. [The host Pi / server] collected the results and picked the winner, so there was one source of truth and every screen showed the same result. We did not use a language model, so nothing ran per event or at setup. 

**Final Video of Neon Race:** https://drive.google.com/file/d/1hGqOS-wmcjMtV6QPC1937JpnXOPRor-4/view?usp=sharing

## Submission Checklist

Before submitting:
- [ ] Document user testing with non-team members
