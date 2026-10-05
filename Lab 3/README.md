# Chatterboxes

**Gal Alon and Jonathan Sharpy**

[![Watch the video](https://user-images.githubusercontent.com/1128669/135009222-111fe522-e6ba-46ad-b6dc-d1633d21129c.png)](https://www.youtube.com/embed/Q8FWzLMobx0?start=19)

In this lab, we want you to design interaction with a speech-enabled device — something that listens and talks to you. This device can do anything *but* control lights (since we already did that in Lab 1). First, we want you to storyboard what you imagine the conversational interaction to be like. Then you will use wizarding techniques to elicit examples of what people might say, ask, or respond. We then want you to use the examples collected from at least two other people to inform the redesign of the device.

We will focus on **audio** as the main modality for interaction to start; these general techniques can be extended to **video**, **haptics** or other interactive mechanisms in the second part of the Lab.

A note on what you are building with. Speech interfaces are usually taught as two boxes — speech-in, speech-out — and that framing hides the part that actually determines whether an interaction works. Between listening and speaking sits the question of **whose turn it is**: when does the device decide you have finished talking, and how long does it make you wait before it answers? This lab gives you direct control over both, and we will ask you to notice what changes when you move them.

## Prep for Part 1: Get the Latest Content and Pick up Additional Parts

Please check instructions in [prep.md](prep.md) and complete the setup.

### Pick up Web Camera If You Don't Have One

Students who have not already received a web camera will receive their Webcam and at the beginning of lab. If you cannot make it to class this week, please contact the TAs to ensure you get these.

### Get the Latest Content

As always, pull updates from the class Interactive-Lab-Hub to both your Pi and your own GitHub repo.

**\[recommended\]** Option 1: On the Pi, `cd` to your `Interactive-Lab-Hub`, pull the updates from upstream (class lab-hub) and push the updates back to your own GitHub repo. You will need the *personal access token* for this.

```
pi@ixe00:~$ cd Interactive-Lab-Hub
pi@ixe00:~/Interactive-Lab-Hub $ git pull upstream Fall2026
pi@ixe00:~/Interactive-Lab-Hub $ git add .
pi@ixe00:~/Interactive-Lab-Hub $ git commit -m "get lab3 updates"
pi@ixe00:~/Interactive-Lab-Hub $ git push
```

Option 2: On your own GitHub repo, create a pull request to get updates from the class Interactive-Lab-Hub. After you have the latest updates online, go to your Pi, `cd` to your `Interactive-Lab-Hub` and use `git pull`.

---

# Part 1

## Setup

Create and activate a virtual environment for this lab:

```
pi@ixe00:~$ cd Interactive-Lab-Hub/Lab\ 3
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ python3 -m venv .venv
pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $ source .venv/bin/activate
(.venv) pi@ixe00:~/Interactive-Lab-Hub/Lab 3 $
```

Install the Python dependencies:

```
(.venv) $ pip install -r requirements.txt
```

This takes a few minutes. If you would like it to take considerably less time, [`uv`](https://docs.astral.sh/uv/) is a drop-in replacement for `pip` that is dramatically faster on the Pi:

```
(.venv) $ pip install uv && uv pip install -r requirements.txt
```

Then run the setup script, which installs the classic speech synthesizers, downloads the voice activity detection model, and pre-fetches a neural voice and a speech recognition model so you are not waiting on downloads during lab:

```
(.venv):~$ cd speech-scripts
(.venv) $ ./setup.sh
```

Check your audio devices before going further. `arecord -l` lists capture devices and `aplay -l` lists playback devices; if your webcam microphone or Bluetooth speaker does not appear, fix that first — every script below assumes the system defaults are the ones you want.

## A. Text to Speech

Your Pi can speak in several quite different ways, and the differences are audible in a way that matters for design. In `speech-scripts/` there are shell scripts for each.

### The classic engines

```
(.venv) $ cd speech-scripts

(.venv) $ sudo apt update
(.venv) $ sudo apt install -y espeak festival festvox-kallpc16k

(.venv) $ ./espeak_demo.sh
(.venv) $ ./festival_demo.sh
```

You can run these `.sh` files by typing `./filename`, and read one with `cat filename`. You can also play audio files directly with `aplay filename` — try `aplay lookdave.wav`.

These are all decades-old technology and they sound like it. `espeak-ng` is a *formant synthesizer*: it generates speech from an acoustic model of the vocal tract, which is why it sounds robotic but also why the whole thing fits in a couple of megabytes and responds instantly. `festival` is *concatenative*: they stitch together recorded fragments of a real speaker, which sounds more human but breaks audibly at the seams.

### Neural TTS with Piper

Note that the Piper command line changed in version 1.x — voices are now downloaded explicitly with `python3 -m piper.download_voices`, and you invoke it as `python3 -m piper`. Tutorials you find online may show the old `echo ... | piper --model ...` form, which no longer works. Browse the [voice samples](https://rhasspy.github.io/piper-samples) and download a different one if you'd like:

```
(.venv) $ python3 -m piper.download_voices en_US-lessac-medium
```

[Piper](https://github.com/OHF-Voice/piper1-gpl) synthesizes speech with a small neural network, runs comfortably on the Pi 5, and sounds markedly better than the above.

```
(.venv) $ ./piper_demo.sh
```

The demo script also shows `--output-raw`, which streams audio to the speaker as it is generated rather than writing a file first. Listen for the difference in how quickly speech begins. In a conversational system this gap is the thing your user experiences as responsiveness.

\*\***Write your own shell file to use your favorite of these TTS engines to have your Pi greet you by name.**\*\*
(This shell file should be saved to your own repo for this lab.)

\*\***Then answer: Is the same greeting, in these different voices, the same greeting? Describe one concrete way the voice changed what the utterance seemed to mean or who seemed to be speaking.**\*\*

**No. The words were the same, but each voice changed who it sounded like. Some voices sounded flat and robotic, like a computer alert, and "excited" almost sounded sarcastic because the voice didn't sound excited at all. Others sounded more human but choppy, like a recorded message. The most natural one sounded like a real person, so the same line felt like an actual welcome. My name is a good example. I had to spell it "Gahl" and stretch out the vowel to get the voice to say it right. When a voice says your name wrong, the greeting stops feeling personal.**

## B. Speech to Text

We use [faster-whisper](https://github.com/SYSTRAN/faster-whisper), a reimplementation of OpenAI's Whisper model that runs several times faster on CPU and does not require PyTorch. All processing happens on the Pi; nothing is sent to a server.

```
(.venv) $ python transcribe.py lookdave.wav
```

The transcript is not the interesting output here — the timings are. Run it again with a larger model and compare:

```
(.venv) $ python transcribe.py lookdave.wav --model base.en
(.venv) $ python transcribe.py lookdave.wav --model small.en
#  noted that the first run may take longer because the model is downloaded, and that the HF unauthenticated-request warning is expected and not an error.
```

Available sizes, smallest first: `tiny.en`, `base.en`, `small.en`, `medium.en`. The `.en` variants are English-only and faster than their multilingual counterparts at the same size.

\*\***Record a few seconds of your own speech (`arecord -d 5 -f cd -c 1 -r 16000 test.wav`) and transcribe it with at least two model sizes. Report the real-time factor for each. At what point does the accuracy improvement stop being worth the delay, for a system that has to answer you?**\*\*

**I recorded myself saying "My zip code is 10016" and transcribed it with three model sizes. Tiny had a real-time factor of 0.21x, base was 0.37x, and small was 1.06x. All three got it right, so the bigger models added delay without improving accuracy. Small was even slower than real time, meaning it took longer to transcribe than it took me to say it.**

**For a system that has to answer you, the improvement stops being worth it after base. Tiny and base respond fast enough to feel like a conversation, while small adds a noticeable wait. On my first try, all three models heard "1001" because the recording cut off before I finished. A bigger model couldn't fix that, which shows that timing matters as much as model size.**


\*\***Write your own script that verbally asks for a numerical input (a phone number, zipcode, number of pets) and records the answer the respondent provides.**\*\* Numbers are a good stress test — transcription systems make characteristic errors on digit strings, and you will want to know what they are before you design around them.

**I wrote ask_number.sh, which asks "What is your zip code?" out loud, records 5 seconds, and turns the answer into text using base.en. When I said "10016" or "one zero zero one six," it wrote "1 0 0 1 6." The numbers were right, but it added spaces that would need to be removed. When I said "one double-oh one six," it wrote "1,000, 1,6," so the zip code was lost. People often say numbers this way, so a real device should repeat the number back to check it or ask people to say one digit at a time.**

## C. Turn-taking: knowing when someone has stopped talking

Everything so far has worked on fixed audio files. A real conversational device does not get told when to start and stop recording — it has to decide. This is the problem that makes speech interfaces hard, and it is mostly not a speech recognition problem.

We use a **voice activity detector** (VAD) to segment the microphone stream into utterances. `listen.py` runs Silero VAD continuously and hands each detected utterance to faster-whisper:

```
(.venv) $ cd speech-scripts
(.venv) $ python listen.py
```

Speak, pause, and watch it transcribe. Now change the endpointing threshold — the amount of silence the system requires before it decides your turn is over:

```
(.venv) $ python listen.py --min-silence 0.2
(.venv) $ python listen.py --min-silence 1.5
```

\*\***Try both extremes, and something in between. Describe what each one feels like to talk to. Note specifically: at 0.2s, what kinds of normal speech get cut off? At 1.5s, what does the delay make the system seem like?**\*\*

**At 0.2s, the system was fast but split almost every sentence into its own turn. Any normal pause, like stopping to think or pausing in the middle of a phone number, would get cut off too early. At 0.4s, the default, it grouped my sentences together because my pauses were shorter than that. At 0.8s, it felt the most natural, since each question was its own turn and it didn't cut me off. At 1.5s, it grouped several sentences together and took a long time to respond, which made it feel slow, like it wasn't paying attention.**

There is no correct value. A system that takes drink orders and a system that listens to someone think out loud want very different thresholds, and the right one depends on what your users are doing with their pauses.

### The complete loop

`echo_bot.py` puts the pieces together: it listens, endpoints, transcribes, and speaks a reply through Piper. The dialogue policy is deliberately trivial — it repeats what you said — so that everything you notice is a property of the timing rather than the content.

```
(.venv) $ python echo_bot.py
```

## D. Storyboard

Storyboard and/or use a Verplank diagram to design a speech-enabled device. (Stuck? Make a device that talks for dogs. If that is too stupid, find an application that is better than that.)

\*\***Post your storyboard and diagram here.**\*\*

**My device, RasPi, is a voice-controlled grocery list keeper that sits on the kitchen counter. Whenever someone notices they're running low on something, they can say "Hey RasPi, add milk to my grocery list," and it confirms the item was added. Before heading to the store, they can ask RasPi to read their list, and it reads back everything they added. This makes it easy to keep track of groceries hands-free, right when you notice something is missing, so nothing gets forgotten at the store.**

<img width="719" height="280" alt="Screenshot 2026-09-27 at 10 11 20 PM" src="https://github.com/user-attachments/assets/e50832e4-7039-40b9-b59e-941a64d44e94" />

**Dialogue:**

Write out what you imagine the dialogue to be. Use cards, post-its, or whatever method helps you develop alternatives or group responses.

**Dialogue:**

Scene 1: Adding items

User: Hey RasPi, add milk to my grocery list.
[RasPi waits for 0.8s of silence, then responds]
RasPi: Added milk.

User: Also add... um... strawberries.
[The "um" pause is shorter than 0.8s, so RasPi keeps listening. After 0.8s of silence, it responds]
RasPi: Added strawberries.

User: And two oranges and chicken.
[RasPi waits for 0.8s of silence]
RasPi: Added two oranges and chicken.

Scene 2: Reading the list

User: Hey RasPi, I'm about to head to the grocery store. Can you read me my list?
[RasPi waits for 0.8s of silence]

RasPi: You have four items.
[0.5s pause]

RasPi: Milk.
[0.5s pause]

RasPi: Strawberries.
[0.5s pause]

RasPi: Two oranges.
[0.5s pause]

RasPi: Chicken.
[0.5s pause]

RasPi: That's everything. Have a good trip!

**RasPi waits in two places. First, it waits for 0.8 seconds of silence before deciding the user is done talking. I chose this because in Part C, 0.2 seconds cut me off when I paused to think, and 1.5 seconds made the device feel slow. Second, when reading the list, RasPi pauses 0.5 seconds between items so the user has time to follow along instead of hearing everything at once.**

Your script should include the pauses. Where does your device wait, and for how long? You now know from Part C that this is a parameter you have to choose, not something that happens for free.

## E. Acting out the dialogue

Find a partner, and *without sharing the script with your partner* try out the dialogue you've designed, where you (as the device designer) act as the device you are designing. Please record this interaction (for example, using Zoom's record feature).



https://github.com/user-attachments/assets/1cf88b5e-20ed-438a-87e2-6646253e73f7



\*\***Describe if the dialogue seemed different than what you imagined when it was acted out, and how.**\*\*

**Yes, the dialogue went differently than I imagined. In my script, the user said short commands like "add milk," but my partner started by explaining the situation ("I need to run to the grocery store") and asked RasPi to take items one at a time. They also gave more detail than I expected, like "five bananas" and "Nespresso capsules, strength eight," and as the device, I ended up asking follow-up questions like "What size milk?" and "What kind of coffee?" that weren't in my script at all. These came after my partner said "Okay, great," which showed they thought they were done, so the questions felt a little late. When reading the list back, I also left out the details they gave, saying "milk" instead of "a gallon of milk." Finally, the pauses were longer than the 0.8 seconds I planned, since it took me a few seconds to think of each response.**

---

# Lab 3 Part 2

For Part 2, you will redesign the interaction with the speech-enabled device using the data collected, as well as feedback from part 1.

**For Part 1, my original idea was a voice-controlled grocery list keeper. For Part 2, I am working with Jonathan Sharpy, and we decided to continue with his idea instead, a hands-free workout assistant. We chose this idea because speech is even more useful during a workout than remembering your grocery list, since the user's hands are busy with weights and they can't easily use a screen.**

## Prep for Part 2

1. What are concrete things that could use improvement in the design of your device? For example: wording, timing, anticipation of misunderstandings.

**One thing to improve is how the device knows a set is finished. Right now it relies on a pause, but the user is silent the whole time they lift, so the device could end the set too early or not at all. Having the user say "done" would be clearer. The timing could also be better. A 0.6 second threshold worked when I tested it calmly, but after a hard set the user may be out of breath and pause mid-sentence, so the device might cut them off. A longer threshold right after a set could help. The device should also expect answers outside "easy, good, or hard," like "kind of tough" or "the last two reps were hard." Finally, gym noise, heavy breathing, and music could trigger the microphone by mistake, so the device should confirm important changes, like a new weight, before moving on.**


2. What are other modes of interaction *beyond speech* that you might also use to clarify how to interact? In particular: how does someone know when the device is listening, and when it is thinking? You have a screen and an LED.

**Besides speech, I could also add a rotary encoder. After each set, the user could turn the knob to pick easy, good, or hard and press it to confirm, instead of speaking. This helps when the user is out of breath, the gym is loud, or speech recognition gets it wrong. The screen would show the three options and highlight the current one as the knob turns, so the user knows what they are choosing.**

3. Make a new storyboard, diagram and/or script based on these reflections.

<img width="907" height="358" alt="Screenshot 2026-10-04 at 11 43 53 AM" src="https://github.com/user-attachments/assets/698479db-5329-4a3f-a274-d93023660595" />

4. (optional) Integrate [input devices](inputs.md) in the system

## Prototype your system

The system should:
* use the Raspberry Pi
* use one or more sensors
* require participants to speak to it

*Document how the system works.*

*Include videos or screencaptures of both the system and the controller.*

## Test the system

Try to get at least two people to interact with your system. (Ideally, you would inform them that there is a wizard *after* the interaction, but we recognize that can be hard.)

Answer the following:

### What worked well about the system and what didn't?

**The system worked well at creating a clear back-and-forth interaction between the user and VoiceFit. The push-to-talk rotary encoder made the timing of the conversation clear, and users naturally waited for VoiceFit's response before continuing with information about their workout. Speech recognition was generally accurate and the response timing felt smooth. One transcription error occurred when Stephen said "I want to do less reps," which was interpreted as "I want to last rest." There were also a few minor inaccuracies during Arnav's interaction, potentially due to the noise in the room.**

**A larger limitation was the scope of the interaction. Without much initial context, users did not necessarily begin at the point in a workout that the predefined responses assumed. I had to use a custom response almost immediately to establish the conversation. Arnav also quickly moved beyond simple set guidance by asking about exercise selection, sets and reps, and pain. This showed that a real workout assistant would need to support a much broader range of conversation.**

### What worked well about the controller and what didn't?

**The predefined Wizard controls worked very well when the user's statement matched one of the available options. I could select a response almost immediately, which made the Wizard-of-Oz interaction feel like an autonomous system with very little delay.**

**The limitation was that users frequently said things that did not fit the predefined responses. In those cases, I had to use the custom-response option. This allowed me to keep the interaction going, but typing a response introduced more delay than selecting one of the instant controls. The tests showed that the preset controls are useful for predictable workout interactions, but they do not yet cover the variety of things users naturally ask a workout assistant.**

### What lessons can you take away from the WoZ interactions for designing a more autonomous version of the system?

**The testing showed me that an autonomous VoiceFit would need to handle much more than simple post-set feedback. Users naturally asked about what exercise to do next, how many sets and reps to perform, and even whether pain might indicate fatigue or a form problem. Rather than relying only on a fixed set of responses, an autonomous version would likely need a more flexible conversational layer capable of interpreting these different intents and generating context-appropriate responses.**

**The tests also highlighted the importance of the physical environment. Speech recognition worked well overall, but even the classroom produced occasional transcription errors. Since VoiceFit would ultimately be used in a noisy gym, the quality and placement of the microphone and the volume and clarity of the speaker would be important parts of the system design.**

### How could you use your system to create a dataset of interaction? What other sensing modalities would make sense to capture?

**A useful interaction dataset could contain the user's spoken statement, its transcription, the current workout context, the user's intent, and the response or action VoiceFit should provide. For example, interactions could be categorized as starting an exercise, reporting that a set was easy or difficult, requesting a change in weight, asking about sets or repetitions, reporting fatigue or discomfort, asking what exercise to perform next, or making a request outside the expected categories. Collecting these interactions across many users and workouts could reveal common conversational patterns and help determine which interactions could use predefined responses and which require more flexible reasoning.**

**Voice interaction could also be combined with additional sensing modalities to give the system information about the user's physical state instead of relying entirely on what they say. Thinking beyond the current prototype, wearable sensors could potentially measure signals related to exertion, such as heart rate or movement, while more experimental wearables could examine factors such as perspiration or breathing. Combining these measurements with the user's workout history and spoken feedback could give VoiceFit more context for adapting its recommendations.**

**Acknowledgment:**

**I worked with Jonathan Sharpy on portions of this lab, as noted throughout the documentation. I also used ChatGPT for technical assistance with code explanation, debugging, hardware/software integration, and organizing my own testing observations. All design decisions, implementation, participant testing, and conclusions are my own.**

