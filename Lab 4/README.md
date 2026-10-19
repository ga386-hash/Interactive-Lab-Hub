Ph-UI!!!

<details>
	<summary><strong>Instructions for Students (Click to Expand)</strong></summary>
  
	**Submission Cleanup Reminder:**
	- This README.md contains extra instructional text for guidance.
	- Before submitting, remove all instructional text and example prompts from this file.
	- You may delete these sections or use the toggle/hide feature in VS Code to collapse them for a cleaner look.
	- Your final submission should be neat, focused on your own work, and easy to read for grading.
  
	This helps ensure your README.md is clear, professional, and uniquely yours!
</details>

---

---

## Lab Overview
Members: Gal Alon (ga386)

Clock name: Hydration Nudge Coaster


For lab this week, we focus on both sensing and actuation, bringing new modes of input and output into your devices, while also prototyping the physical structure and overall look of the device. You will consider how the physical form supports sensing and actuation, and how these elements come together to shape the interaction and aesthetics of the device.

---

## Lab Structure

A) [Capacitive Sensing](#part-a)

B) [More Sensors](#part-b)

C) [Servo Actuation](#part-c)

D) [Physical Interaction Design: Feast Automata](#part-d)

E) [Build & Integrate](#part-e)

F) [Final Documentation](#part-f)

---

## Part 1 Lab Preparation

---

### Get the latest content:
As always, pull updates from the class Interactive-Lab-Hub to both your Pi and your own GitHub repo. As we discussed in the class, there are 3 ways you can do so:


Option 1: On the Pi, `cd` to your `Interactive-Lab-Hub`, pull the updates from upstream (class lab-hub) and push the updates back to your own GitHub repo. You will need the personal access token for this.
```
pi@ixe00:~$ cd Interactive-Lab-Hub
pi@ixe00:~/Interactive-Lab-Hub $ git pull upstream Fall2026
pi@ixe00:~/Interactive-Lab-Hub $ git add .
pi@ixe00:~/Interactive-Lab-Hub $ git commit -m "get lab4 content"
pi@ixe00:~/Interactive-Lab-Hub $ git push
```

Option 2: On your own GitHub repo, [create pull request](https://github.com/FAR-Lab/Developing-and-Designing-Interactive-Devices/blob/2021Fall/readings/Submitting%20Labs.md) to get updates from the class Interactive-Lab-Hub. After you have latest updates online, go on your Pi, `cd` to your `Interactive-Lab-Hub` and use `git pull` to get updates from your own GitHub repo.

Option 3: (preferred) use the Github.com interface to update the changes.

---

### Quick Start: Python Environment Setup

1. **Create and activate a virtual environment in Lab 4:**
	```bash
	cd ~/Interactive-Lab-Hub/Lab\ 4
	python3 -m venv .venv
	source .venv/bin/activate
	```
2. **Install all Lab 4 requirements:**
	```bash
	pip install -r requirements2025.txt
	```
3. **Check CircuitPython Blinka installation:**
	```bash
	python blinkatest.py
	```
	If you see "Hello blinka!", your setup is correct. If not, follow the troubleshooting steps in the file or ask for help.

---

### Gathering materials for this lab:

* Cardboard (start collecting those shipping boxes!)
* Found objects and materials--like bananas and twigs.
* Cutting board
* Cutting tools
* Markers


(We do offer shared cutting board, cutting tools, and markers on the class cart during the lab, so do not worry if you don't have them!)

---

### Prototyping References 

* [What do prototypes prototype?](https://www.semanticscholar.org/paper/What-do-Prototypes-Prototype-Houde-Hill/30bc6125fab9d9b2d5854223aeea7900a218f149)
* [Paper prototyping](https://www.uxpin.com/studio/blog/paper-prototyping-the-practical-beginners-guide/) is used by UX designers to quickly develop interface ideas and run them by people before any programming occurs. 
* [Cardboard prototypes](https://www.youtube.com/watch?v=k_9Q-KDSb9o) help interactive product designers to work through additional issues, like how big something should be, how it could be carried, where it would sit. 
* [Tips to Cut, Fold, Mold and Papier-Mache Cardboard](https://makezine.com/2016/04/21/working-with-cardboard-tips-cut-fold-mold-papier-mache/) from Make Magazine.
* [Surprisingly complicated forms](https://www.pinterest.com/pin/50032245843343100/) can be built with paper, cardstock or cardboard.  The most advanced and challenging prototypes to prototype with paper are [cardboard mechanisms](https://www.pinterest.com/helgangchin/paper-mechanisms/) which move and change. 
* [Dyson Vacuum Cardboard Prototypes](http://media.dyson.com/downloads/JDF/JDF_Prim_poster05.pdf)
<p align="center"><img src="https://dysonthedesigner.weebly.com/uploads/2/6/3/9/26392736/427342_orig.jpg"  width="200" > </p>

### Feast Automata Inspirations

* [Simone Giertz - The Breakfast Machine](https://www.youtube.com/watch?v=E2evC2xTNWg) turns an everyday breakfast routine into a deliberately awkward robotic performance.
* [Pee-wee’s Big Adventure - Breakfast Machine](https://www.classhook.com/resources/1295-pee-wee-s-big-adventure-pee-wee-s-breakfast-machine?utm_source=chatgpt.com) An elaborate Rube Goldberg-style machine turns the ordinary routine of making breakfast into a playful mechanical performance.
* [Wallace & Gromit - The Autochef](https://www.google.com/search?sca_esv=66d2cd5ecf989ed9&sxsrf=APpeQnuwAWHrA3R0b1GeoQ4r-spKos3vUQ:1789367781228&udm=7&fbs=ABfTbFVyMZGZf1hfvX9uKjN_-G8cxpBkeIeqYwoCbfNVc4vKE7plZzta63Pe5DpJ3XFR9XzI_yj6fb6bfPt1x_5u3nRcG7tR9jg4Omd7-UnDuaw5i86wRQqe-045kPXObjb1eDS649ikhB0y_hSFYfNioDnA60A2i_oC1IzIZywb7ERnDQqnSx10JnfJEaAauzJXglx4123_vjf0_54bKrF6QjM9ne5i3g&q=Wallace+%26+Gromit+%E2%80%94+The+Autochef&sa=X&ved=2ahUKEwiI0OO3uu2WAxVHEFkFHQ3iAOEQtKgLegQIFRAB&biw=1197&bih=613&dpr=2.5#fpstate=ive&vld=cid:72c3eb07,vid:2igRcGxlshA,st:0)
* [Nik Ramage - Jelly Wobbler](http://www.youtube.com/watch?v=pj2t71q68sY#t=33) makes the simple act of wobbling jelly into a dedicated machine.
* [Zekun Chang - Blah Blah](https://zekunchang.com/portfolio/blah-blah/) is an alcohol machine that presents a playful commentary on drunken behavior.

### Mechanical Prototyping Resource

* [Gear Template Generator](https://woodgears.ca/gear_cutting/template.html) can help you prototype simple gear mechanisms for translating servo motion into physical movement.


---

### Part A
### Capacitive Sensing, a.k.a. Human-Twizzler Interaction 

We want to introduce you to the [capacitive sensor](https://learn.adafruit.com/adafruit-mpr121-gator) in your kit. It's one of the most flexible input devices we are able to provide. At boot, it measures the capacitance on each of the 12 contacts. Whenever that capacitance changes, it considers it a user touch. You can attach any conductive material. In your kit, you have copper tape that will work well, but don't limit yourself! In the example below, we use Twizzlers--you should pick your own objects.


<p float="left">
<img src="https://cdn-learn.adafruit.com/guides/cropped_images/000/003/226/medium640/MPR121_top_angle.jpg?1609282424" height="150" />
 
</p>

Plug in the capacitive sensor board with the QWIIC connector. Connect your Twizzlers with either the copper tape or the alligator clips (the clips work better). Install the latest requirements from your working virtual environment:

These Twizzlers are connected to pads 6 and 10. When you run the code and touch a Twizzler, the terminal will print out the following

```
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python cap_test.py 
Twizzler 10 touched!
Twizzler 6 touched!
```

---

### Part B
### More sensors

#### Light/Proximity/Gesture sensor (APDS-9960)

We here want you to get to know this awesome sensor [Adafruit APDS-9960](https://www.adafruit.com/product/3595). It is capable of sensing proximity, light (also RGB), and gesture! 
 
<img src="https://cdn-shop.adafruit.com/970x728/3595-06.jpg" width=200>
 

Connect it to your pi with Qwiic connector and try running the three example scripts individually to see what the sensor is capable of doing!

```
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python proximity_test.py
...
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python gesture_test.py
...
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python color_test.py
...
```

You can go the the [Adafruit GitHub Page](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960) to see more examples for this sensor!

#### Rotary Encoder 

A rotary encoder is an electro-mechanical device that converts the angular position to analog or digital output signals. The [Adafruit rotary encoder](https://www.adafruit.com/product/4991#technical-details) we ordered for you came with separate breakout board and encoder itself, that is, they will need to be soldered if you have not yet done so! We will be bringing the soldering station to the lab class for you to use, also, you can go to the MakerLAB to do the soldering off-class. Here is some [guidance on soldering](https://learn.adafruit.com/adafruit-guide-excellent-soldering/preparation) from Adafruit. When you first solder, get someone who has done it before (ideally in the MakerLAB environment). It is a good idea to review this material beforehand so you know what to look at.

<p float="left">

   
<img src="https://cdn-shop.adafruit.com/970x728/377-02.jpg" height="200" />
<img src="https://cdn-shop.adafruit.com/970x728/4991-09.jpg" height="200">
</p>

Connect it to your pi with Qwiic connector and try running the example script, it comes with an additional button which might be useful for your design!

```
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python encoder_test.py
```

You can go to the [Adafruit Learn Page](https://learn.adafruit.com/adafruit-i2c-qt-rotary-encoder/python-circuitpython) to learn more about the sensor! The sensor actually comes with an LED (neo pixel): Can you try lighting it up? 

#### Joystick 


A [joystick](https://www.sparkfun.com/products/15168) can be used to sense and report the input of the stick for it pivoting angle or direction. It also comes with a button input!

<p float="left">
<img src="https://cdn.sparkfun.com//assets/parts/1/3/5/5/8/15168-SparkFun_Qwiic_Joystick-01.jpg" height="200" />
</p>

Connect it to your pi with Qwiic connector and try running the example script to see what it can do!

```
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python joystick_test.py
```

You can go to the [SparkFun GitHub Page](https://github.com/sparkfun/Qwiic_Joystick_Py) to learn more about the sensor!

#### Distance Sensor


Earlier we have asked you to play with the proximity sensor, which is able to sense objects within a short distance. Here, we offer [Sparkfun Proximity Sensor Breakout](https://www.sparkfun.com/products/15177), With the ability to detect objects up to 20cm away.

<p float="left">
<img src="https://cdn.sparkfun.com//assets/parts/1/3/5/9/2/15177-SparkFun_Proximity_Sensor_Breakout_-_20cm__VCNL4040__Qwiic_-01.jpg" height="200" />

</p>

Connect it to your pi with Qwiic connector and try running the example script to see how it works!

```
(circuitpython) pi@ixe00:~/Interactive-Lab-Hub/Lab 4 $ python qwiic_distance.py
```

You can go to the [SparkFun GitHub Page](https://github.com/sparkfun/Qwiic_Proximity_Py) to learn more about the sensor and see other examples

---

### Part C
### Servo Actuation

Now that you have explored several forms of sensing, add physical output by learning to control a servo motor. Complete the Servo pHAT setup and basic servo test before beginning your interaction design.

### Servo Control with SparkFun Servo pHAT
For this lab, you will use the **SparkFun Servo pHAT** to control a micro servo (such as the Miuzei MS18 or similar 9g servo). The Servo pHAT stacks directly on top of the Adafruit Mini PiTFT (135×240) display without pin conflicts:
- The Mini PiTFT uses SPI (GPIO22, 23, 24, 25) for display and buttons ([SPI pinout](https://pinout.xyz/pinout/spi)).
- The Servo pHAT uses I²C (GPIO2 & 3) for the PCA9685 servo driver ([I2C pinout](https://pinout.xyz/pinout/i2c)).
- Since SPI and I²C are separate buses, you can use both boards together.
**⚡ Power:**
- Plug a USB-C cable into the Servo pHAT to provide enough current for the servos. The Pi itself should still be powered by its own USB-C supply. Do NOT power servos from the Pi’s 5V rail.

<p align="center">
    <img src="Servo_pHAT.gif" alt="Servo pHAT Demo" width="400"/>
</p>

**Basic Python Example:**
We provide a simple example script: `Lab 4/pi_servo_hat_test.py` (requires the `pi_servo_hat` Python package).
Run the example:
```
python pi_servo_hat_test.py
```
For more details and advanced usage, see the [official SparkFun Servo pHAT documentation](https://learn.sparkfun.com/tutorials/pi-servo-phat-v2-hookup-guide/all#resources-and-going-further).
A servo motor is a rotary actuator that allows for precise control of angular position. The position is set by the width of an electrical pulse (PWM). You can read [this Adafruit guide](https://learn.adafruit.com/adafruit-arduino-lesson-14-servo-motors/servo-motors) to learn more about how servos work.

---

### Part D
### Physical Interaction Design: Feast Automata

**Feast Automata:** build a device that **transforms ordinary dining rituals into playful physical interactions.** Begin with a familiar experience around eating, drinking, cooking, serving, or sharing food, and explore how sensing and actuation might augment, exaggerate, automate, or reinterpret your dining experience.

In this part, use the sensing techniques from Parts A–B and the servo actuation from Part C to develop a physical interaction.

#### Physical considerations for sensing

Sensors need to be positioned in specific locations or orientations to make them useful for an application. Choose a sensor that fits the dining interaction you want to explore. For example, a distance sensor could detect when a cup is placed on a coaster; where the sensor is positioned determines what it can reliably detect.

Think about how the larger object needs to be shaped so the sensor can work reliably, where the actuator needs to sit, what moves, and how a person encounters the interaction.

#### Physical Form and Housing

Think about how your sensor, actuator, and electronics are physically arranged within your prototype. Consider where components need to be placed, what parts move, how the device is supported or enclosed, and how the overall form and aesthetics shape the interaction.

Use cardboard, paper, found objects, or other low-fidelity materials to quickly prototype the physical structure before refining your final design.

#### Optional Display Feedback: Qwiic OLED

Your kit includes these [SparkFun Qwiic OLED screens](https://www.sparkfun.com/products/17153). These use less power than the MiniTFTs you have mounted on the GPIO pins of the Pi, but, more importantly, they can be more flexibly mounted elsewhere on your physical interface. The way you program this display is almost identical to the way you program a  Pi display. Take a look at `oled_test.py` and some more of the [Adafruit examples](https://github.com/adafruit/Adafruit_CircuitPython_SSD1306/tree/master/examples).

<p float="left">
<img src="https://cdn.sparkfun.com//assets/parts/1/6/1/3/5/17153-SparkFun_Qwiic_OLED_Display__0.91_in__128x32_-01.jpg" height="200" />

</p>


As you develop your Feast Automata concept, consider where the sensor and actuator need to be placed, what parts move, how electronics are housed, and how the overall form and aesthetics support the interaction.

**\*\*\*Draw 5 sketches that explore different physical arrangements for your sensing and actuation.\*\*\***

<img width="700" height="323" alt="Screenshot 2026-10-13 at 10 50 21 PM" src="https://github.com/user-attachments/assets/e24a840c-9cf6-43b1-a240-2850c6d712cc" />

<img width="673" height="292" alt="Screenshot 2026-10-13 at 10 52 26 PM" src="https://github.com/user-attachments/assets/6817c53b-b5cb-48fc-b11e-9925782e8a44" />

<img width="872" height="315" alt="Screenshot 2026-10-14 at 11 40 07 AM" src="https://github.com/user-attachments/assets/094981c8-78be-4f99-8ce4-ffb3fb5dcea5" />

**\*\*\*What questions do these sketches raise? What do you need to physically prototype to answer them?\*\*\***

These sketches made me think about where the sensor should go, how well it will work, and how well the moving parts will work. In the auto tea steeper, I need to check if the color sensor can see the tea get darker through a glass mug and if room light messes up the reading. In the never-soggy cereal feeder, I need to see if the distance sensor can tell a full bowl from an empty one and if the servo gate can drop cereal without getting stuck. In the hydration nudge coaster, I need to make sure the servo arm taps the glass hard enough to notice but not so hard that it knocks it over. To figure this out, I need to build simple cardboard versions, try different sensor spots and distances, and change the servo angles and speeds until everything works well.


**\*\*\*Pick one design to prototype and explain why.\*\*\***

I chose to prototype the hydration nudge coaster. It solves a real problem, since it is easy to forget to drink water during long study sessions or work days. The design is also simple to build with my kit, using a distance sensor in the coaster to detect the glass, the  screen to show the timer, and a servo arm to tap the glass as a reminder. I can also use the speaker to say “Drink water!” so the reminder is both something you see and hear. Even though the build is simple, it still creates a clear and playful interaction between the person and the device, and it gives me room to add features like escalating taps and a sip counter as I improve it.


**\*\*\*Document your rough prototype with photos and/or video.\*\*\***


https://github.com/user-attachments/assets/231bef70-46da-4cfd-b675-49b6fc7582cc


## Part 2

Following exploration and reflection from Part 1, complete the "looks like," "works like" and "acts like" prototypes for your design, reiterated below.

---

### Part E

#### Build & Integrate: Sensing + Actuation

For Part 2, build the Feast Automata interaction you developed in Part D by connecting sensing/input to physical actuation.

**Your prototype should:**
- Use at least one sensing or input device.
- Use servo-based physical actuation.
- Connect sensing and actuation into a meaningful interaction around eating, drinking, cooking, serving, or sharing food.
- Additional inputs, displays, LEDs, buttons, or other outputs are optional extensions.

**Document your system with:**
- Code for your sensing + actuation prototype
- Photos and/or video of the working prototype in action
- A simple interaction diagram or sketch showing how sensing and actuation are connected
- Written reflection: What did you learn about connecting sensing, movement, and physical form? What was fun, surprising, or challenging?

**Hydration Nudge Coaster:**

The hydration nudge coaster reminds you to drink water while you study or work. When you place your glass on the coaster, a distance sensor detects it and a 20 min countdown starts on the OLED screen. When the countdown reaches zero, a servo arm taps the glass four times and the speaker says “Drink water!” Lifting the glass resets the device so it is ready for the next round.

For testing and the demo, the countdown is set to 10 seconds. In real use, it would be set to around 20 minutes.

**Parts Used:**
- Raspberry Pi
- SparkFun Servo pHAT 
- SparkFun Qwiic Proximity Sensor 
- SparkFun Qwiic OLED display 
- Speaker using espeak for the voice
- Cardboard, tape, and a pen for the tapping arm

**Questions to consider:**
- How does your chosen sensor or input shape the physical response?

**The distance sensor only knows if something is close to it, so the whole interaction is built around the glass sitting on the coaster. Because the sensor gives a clear jump in readings when the glass is placed, the device can start the countdown right away and respond with a quick, clear tap.**

- How does the physical arrangement of the sensor and actuator change the interaction?

**The sensor sits inside the coaster facing up, so the glass has to be centered over it to be detected. The servo arm is mounted next to the coaster at the height of the bottom of the glass, so it hits the side of the glass instead of the table. If the arm or the glass is too far away, the tap does not reach, so the spacing between them matters a lot.**
  
- What thresholds, timing, or movement patterns make the interaction feel clear or playful?

**With nothing on it, the sensor read about 1 to 3. With the glass 1 cm above it, it read about 5,100, and with the glass touching it, about 21,600. A threshold of 1000 made detection reliable. Four quick taps at 0.2 seconds each felt more noticeable and playful than one slow tap, and pairing the taps with the voice made the reminder hard to miss.**

- What changes when you adjust the sensor placement or servo motion?

**Moving the glass even a little off center lowered the sensor readings, so the hole in the coaster needed to line up with the sensor. Making the servo swing faster made the tap louder and more noticeable, but if it is too fast, the arm does not swing all the way before turning back. Changing the tap angle changed how hard the arm hit the glass, so I tuned it until the tap was clear but did not move the glass.**



**Reflection: This project showed me that connecting sensing and movement is not just about the code, but also about how the physical parts are placed. The sensor worked well once the glass was centered over it, and the servo needed to be at the right height and distance to actually tap the glass. One challenge was a Qwiic cable that caused the sensor to throw errors, which I fixed by connecting the sensor directly to the Servo pHAT and reseating the cable. It was fun to see the device react on its own and hear it say “Drink water!” for the first time. I was surprised by how much small changes, like the tap speed or the glass position, changed how the interaction felt.**


---

### Part F

### Final Documentation

Document all the prototypes and iterations you have designed and worked on! Again, deliverables for this lab are writings, sketches, photos, and videos that show what your prototype:
* "Looks like": shows how the device should look, feel, sit, weigh, etc.
* "Works like": shows what the device can do
* "Acts like": shows how a person would interact with the device

---
**Interaction diagram: the distance sensor detects the glass, the Raspberry Pi runs a 10 second countdown on the OLED, and when it hits zero the servo taps the glass and the speaker says “Drink water!” Lifting the glass resets the device for the next round.**

<img width="670" height="471" alt="Screenshot 2026-10-19 at 3 03 57 PM" src="https://github.com/user-attachments/assets/17996140-968d-4aa2-9c83-59ffe8640cc0" />






**Looks Like**

The device looks like a small coaster with a servo arm standing next to it. The water bottle/glass sits on top of the coaster, right over the distance sensor, and the OLED screen shows the countdown. It is small enough to sit on a desk next to a laptop.

<img width="552" height="724" alt="Screenshot 2026-10-19 at 2 54 56 PM" src="https://github.com/user-attachments/assets/4acf91cd-4af8-437b-82b3-dc9cae10ec47" />

**Prototype setup:** a cardboard coaster holds the distance sensor in a cutout at its center so it can detect the glass placed on top. Next to it, a servo taped to the desk swings a pen, which acts as the tapping arm, and both are wired to the Raspberry Pi through the Servo pHAT.


**Works Like**

When a glass is placed on the coaster, the distance sensor detects it and the OLED starts a 10 second countdown. When the countdown reaches zero, the servo arm taps the glass four times and the speaker says “Drink water!” When the glass is lifted, the device resets and shows “Place your glass” again.

<img width="552" height="631" alt="Screenshot 2026-10-19 at 2 55 06 PM" src="https://github.com/user-attachments/assets/12eb0e33-a979-47f3-8709-1abf482d3288" />

**Prototype in use:** a water bottle sits on the cardboard coaster, right over the distance sensor, which starts the countdown. The servo with the pen arm is taped down next to it so it can swing over and tap the bottle when time runs out, and the speaker on the left says “Drink water!”


<img width="468" height="449" alt="Screenshot 2026-10-19 at 2 54 36 PM" src="https://github.com/user-attachments/assets/3e7a0252-7b2c-443c-9961-5545b1436846" />

**Waiting:** The OLED, mounted in the front of the cardboard base, tells the user to place their glass on the coaster.

<img width="512" height="531" alt="Screenshot 2026-10-19 at 2 54 29 PM" src="https://github.com/user-attachments/assets/c42ca180-b9a3-4d23-a462-f8789a577689" />

**Countdown:** Once the glass is detected, the OLED counts down the seconds until the next reminder.

<img width="533" height="543" alt="Screenshot 2026-10-19 at 2 54 24 PM" src="https://github.com/user-attachments/assets/aa26d880-489e-4b49-8d5f-936a4f12ea4f" />

**Reminder:** When the countdown hits zero, the OLED shows “Drink water!” while the servo taps the glass and the speaker says the reminder out loud.



**Acts Like**

A person sets their glass on the coaster while they study or work and forgets about it. When the timer runs out, the tapping sound and the voice get their attention and remind them to take a drink. Picking up the glass to drink resets the device, so the reminder fits into the normal habit of drinking water without needing any buttons or extra steps.


**Final Interactive Video:** https://drive.google.com/file/d/1BMjYWUDDqvZp8Z3TMxqV-f14SEcyf-VD/view?usp=sharing

**The code**for this prototype is in [hydration_coaster.py](hydration_coaster.py).


