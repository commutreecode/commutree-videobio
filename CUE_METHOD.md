# How to set voice_cues.txt (do this every time)

1. Run: ffmpeg -i voice.wav -af "silencedetect=n=-30dB:d=0.45" -f null -
2. Count sentences (।) in EACH narration line:
   L1 name/city = 2, L2 personal = up to 5, L3 education/work = 2,
   L4 parents = 2, L5 gotra = 1, L6 CTA = 1
3. Walk the gap list IN ORDER. A line with N sentences consumes N-1 gaps as
   INTERNAL pauses; the NEXT gap is that line's break. The line's start = that
   gap's silence_end.
4. NEVER pick "the 5 biggest gaps" — an internal pause can be longer than a real
   break (e.g. 0.66s internal vs 0.56s break). Sentence counting is what's reliable.
5. Cue file = 6 line-start times + the voice's total duration, one per line.
