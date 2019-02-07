# balls

A collection of classes and prograns that simulate elastic collisions
between moving masses and which produce somewhat musical sounds.

_This is and will remain a work in progress.  Enjoy, but don't ask for help!_

The Python modules can be run as main programs as follows:

```
balls9.py [<chord sequence>]

tune.py [<chord sequence>]

pend.py [mass1,angle1,color1 mass2,angle2,color2 ...]
```
```[<chord sequence>]``` is an optional specfication of chords using
relative notation of the form I ii IV iio vi V7 bII II ..., where
uppercase indicates a major chord and lower indicates minor.  The b
prefix means to flat the chord.  The o and 7 suffixes specify a
diminished and a seventh chord, respectively.  The tonic is set in
tune.py:main() when tune.py is run as a program.  (tune is imported by
balls9.py, which sets the tonic randomly.)  tune.py cycles through the
sequence four times, then exits.  balls9.py cycles continuously but
chooses a new tonic and a new ball configuration (both at random) with
each click of the left mouse button.  See method
balls9.py:Baller.Start() for other button/key bindings.

The optional mass,angle,color specifications to pend.py sets the
initial configuration of one or more pendulums. mass is in kilograms,
angle is in degrees with 0 at 3 o'clock increasing clockwise, and
color is any common color name (e.g. red, blue, yellow).

### Examples:  
```
  balls9.py I vi IV V  
  tune.py I v vo IV IV7 V  
  pend.py .1,0,red .03,180,blue .15,269,purple
```

### Notes:

tune.py and balls9.py require pyaudio, which may be obtained from ```  people.csail.mit.edu/hubert/pyaudio/ ```

