#!/usr/bin/python
#
"""A collection of functions and classes useful for music generation."""
#
# Copyright 2017 David Talkin.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'dtalkin@gmail.com (David Talkin)'


import sys
import math
import array
import pyaudio
import time
import random

def MakeMajorChords(n_semis, base_i):
    """Given a count of notes ascending by semitones, and an index into
    that (virtual) array, generate indices to the notes, including all
    extensions and reflections that can comprise the major chord based
    on the indexed semitone.  Return an array of indices of these notes.
    """
    chord = []
    skips = [4, 3, 5]
    base_i = base_i % 12
    if (base_i - 8) >= 0:
        ind = base_i - 8
        skipi = 1
    elif (base_i - 5) >= 0:
        ind = base_i - 5
        skipi = 2
    else:
        ind = base_i
        skipi = 0
    while ind < n_semis:
        chord.append(ind)
        ind += skips[skipi]
        skipi = (skipi + 1) % len(skips)
    return chord


def MakeMinorChords(n_semis, base_i):
    """Given a count of notes ascending by semitones, and an index into
    that (virtual) array, generate indices to the notes, including all
    extensions and reflections that can comprise the minor chord based
    on the indexed semitone.  Return an array of indices of these notes.
    """
    chord = []
    skips = [3, 4, 5]
    base_i = base_i % 12
    if (base_i - 9) >= 0:
        ind = base_i - 9
        skipi = 1
    elif (base_i - 5) >= 0:
        ind = base_i - 5
        skipi = 2
    else:
        ind = base_i
        skipi = 0
    while ind < n_semis:
        chord.append(ind)
        ind += skips[skipi]
        skipi = (skipi + 1) % len(skips)
    return chord


def MakeAllNotes(low, high):
    twelth2 = pow(2.0, 1.0/12.0)
    a4 = 440.0
    names = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
    notes = []
    tex = []
    for n in range(low, high + 1):
        notes.append(a4 * pow(twelth2, n))
        ind = n % 12
        tex.append(names[ind])
    return notes, tex


def MakeSimpleNotes(low, high):
    twelth2 = pow(2.0, 1.0/12.0)
    a4 = 440.0
    notes = []
    skips = [2, 2, 1, 2, 2, 2, 1]
    ski = 0
    n = low
    while n <= high:
        notes.append(a4 * pow(twelth2, n))
        n += skips[ski]
        ski = (ski+1)%len(skips)
    return notes


class Notes(object):

    def __init__(self, tonic, n_semis):
        self.tonic = tonic
        self.n_semis = n_semis
        self.c_sharp_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#',
                              'A', 'A#', 'B']
        self.c_flat_names = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab',
                             'A', 'Bb', 'B']
        self.a4 = 440.0
        self.notes, self.names = self.CreateSemitoneFrequencies(self.tonic,
                                                                n_semis)
        self.progression_steps = {'I':0, 'II':2, 'III':4, 'IV':5, 'V':7,
                                  'VI':9, 'VII':11}

    def GetNoteName(self, note_ind):
        return self.c_sharp_names[note_ind % 12]

    def GetIndexFromNoteName(self, note_name, tonic_name='C'):
        if note_name in self.c_sharp_names:
            ind = self.c_sharp_names.index(note_name)
        elif note_name in self.c_flat_names:
            ind = self.c_flat_names.index(note_name)
        else:
            sys.stderr.write('Note name (%s) not found in name lists.\n' %
                             (note_name))
            return None
        if tonic_name in self.c_sharp_names:
            tind = self.c_sharp_names.index(tonic_name)
        elif tonic_name in self.c_flat_names:
            tind = self.c_flat_names.index(tonic_name)
        else:
            sys.stderr.write('Tonic name (%s) not found in name lists.\n' %
                             (tonic_name))
            return None
        return (ind - tind) % 12

    def CreateSemitoneFrequencies(self, tonic, n_notes):
        if type(tonic) != type(''):
            sys.stderr.write('Bad base note specification (%s).\n' %
                             (str(tonic)))
            return None
        if tonic[-1].isdigit():
            oct = int(tonic[-1])
            note = tonic[:-1]
        else:
            oct = 4
            note = tonic
        if note in self.c_sharp_names:
            ind = self.c_sharp_names.index(note)
        elif note in self.c_flat_names:
            ind = self.c_flat_names.index(note)
        else:
            sys.stderr.write('Unrecognized base note spec (%s)\n' % (tonic))
            return None
        a_ind = self.c_sharp_names.index('A')
        i_diff = ind - a_ind
        o_diff = oct - 4
        low_ind = i_diff + (12 * o_diff)
        high_ind = low_ind + n_notes
        twelth2 = pow(2.0, 1.0/12.0)
        notes = []
        names = []
        for n in range(low_ind, high_ind):
            notes.append(self.a4 * pow(twelth2, n))
            ind = (n + a_ind) % 12
            names.append(self.c_sharp_names[ind])
        return notes, names

    def ChordSpecToIndices(self, spec):
        sp = spec
        if sp[0] == 'b':
            flatted = True
            sp = sp[1:]
        else:
            flatted = False
        i = 0
        while  (i < len(sp)) and (sp[i] in 'VvIi'):
            i += 1
        sint = sp[:i]
        try:
            interval = self.progression_steps[sint.upper()]
        except KeyError:
            sys.stderr.write('Bad chord specification (%s)\n' % spec)
            return None
        if flatted:
            interval -= 1
        is_minor = sint.islower()
        is_dim = 'o' in sp
        has_7 = '7' in sp
        if is_minor:
            int_2 = 3
            int_3 = 4
        else:
            int_2 = 4
            int_3 = 3
        if is_dim:
            if is_minor:
                int_3 -= 1
            else:
                int_2 -= 1
        if has_7:
            if sint in ['I', 'IV', 'vii']:
                int_7 = 11
            else:
                int_7 = 10
            if is_dim:
                int_7 -= 1
        else:
            int_7 = 0
        chord = []
        chord.append(interval)
        chord.append(interval + int_2)
        chord.append(interval + int_2 + int_3)
        if int_7:
            chord.append(interval + int_7)
        ninds = []
        for n in chord:
            if n >= len(self.notes):
                n = n % 12
            ninds.append(n)
        ninds.sort()
        return ninds

    def ChordSpecToNotes(self, chord_spec):
        inds = self.ChordSpecToIndices(chord_spec)
        if not inds:
            return None
        return [self.notes[i] for i in inds]
        
    def ChordSpecToNoteNames(self, chord_spec):
        inds = self.ChordSpecToIndices(chord_spec)
        if not inds:
            return None
        return [self.names[i] for i in inds]
        
    def PrintNotes(self):
        for i in range(len(self.notes)):
            print self.names[i], self.notes[i]


class Tones(object):
    """A class to generate and manipulate musical signals."""

    def __init__(self, sample_rate):
        self.fs = sample_rate
        self.notes = []
        self.args  = []
        self.incs = []
        self.amps = []
        self.n_notes = 0
        self.ResetChord(4)
        self.ping_notes = []
        self.ping_args = []
        self.ping_incs = []
        self.ping_amps = []
        self.ping_decay = 0.9995
        self.ping_reset_amp = 1000.0
        self.ping_samples = 0
        self.ping_inds = []
        self.n_pings = 0
        self.ResetPings(10)
        self.ping_is_on = True
        self.chord_is_on = True
        self.detune_is_on = True

    def ToggleDetune(self):
        self.detune_is_on = not self.detune_is_on

    def TogglePing(self):
        self.ping_is_on = not self.ping_is_on

    def ToggleChord(self):
        self.chord_is_on = not self.chord_is_on

    def ResetPings(self, max_notes):
        self.ping_notes = [0.0 for i in range(max_notes)]
        self.ping_args = [0.0 for i in range(max_notes)]
        self.ping_incs = [0.0 for i in range(max_notes)]
        self.ping_reset_amp = 32000.0 / max_notes
        self.ping_amps = [0.0 for i in range(max_notes)]
        self.ping_decay = 0.9995
        self.ping_samples = int(self.fs * 1.0)
        self.ping_inds = [self.ping_samples for i in range(max_notes)]
        self.n_pings = 0

    def ResetChord(self, max_notes):
        self.notes = [0.0 for i in range(max_notes)]
        self.args = [0.0 for i in range(max_notes)]
        self.incs = [0.0 for i in range(max_notes)]
        amp = 6000.0 / max_notes
        self.amps = [amp for i in range(max_notes)]
        self.n_notes = 0

    def SetupPings(self, ping_notes, time_const=0.5, dur=1.0):
        if len(ping_notes) > self.n_pings:
            self.ResetPings(len(ping_notes))
        self.ping_notes = ping_notes
        pi2 = math.pi * 2.0
        self.ping_samples = int(dur * self.fs)
        self.ping_decay = math.exp(-1.0 / (time_const * self.fs))
        for i in range(len(ping_notes)):
            if self.detune_is_on:
                freq = (8.0 * (random.random() - 0.5)) + ping_notes[i]
            else:
                freq = ping_notes[i]
            self.ping_incs[i] = pi2 * freq / self.fs
        self.n_pings = len(ping_notes)

    def Ping(self, ping_ind, new_ping_freq=None):
        if new_ping_freq:
            self.ping_incs[ping_ind] = 2.0 * math.pi * new_ping_freq / self.fs
        self.ping_amps[ping_ind] = self.ping_reset_amp
        self.ping_inds[ping_ind] = 0
        self.ping_args[ping_ind] = 0.0

    def ChangeChord(self, new_notes):
        if len(new_notes) > len(self.notes):
            self.ResetChord(len(new_notes))
        self.notes = new_notes
        self.n_notes = len(new_notes)
        pi2 = math.pi * 2.0
        for i in range(self.n_notes):
            self.incs[i] = pi2 * self.notes[i] / self.fs

    def SetupGenreator(self, notes):
        self.ChangeChord(notes)

    def GeneratePingSignal(self, n_samp):
        output = [0.0 for i in range(n_samp)]
        if not self.ping_is_on:
            return output
        pi2 = math.pi * 2.0
        decay = self.ping_decay
        for ping in range(self.n_pings):
            if self.ping_inds[ping] >= self.ping_samples:
                continue
            ngen = min(n_samp, self.ping_samples - self.ping_inds[ping])
            finc = self.ping_incs[ping]
            farg = self.ping_args[ping]
            famp = self.ping_amps[ping]
            for i in range(ngen):
                output[i] += famp * math.sin(farg)
                famp *= decay
                farg = math.fmod(farg + finc, pi2)
            self.ping_amps[ping] = famp
            self.ping_args[ping] = farg
            self.ping_inds[ping] += ngen
        return output

    def GetSamples(self, n_samp):
        pi2 = 2.0 * math.pi
        sig = [0 for i in range(n_samp)]
        pings = self.GeneratePingSignal(n_samp)
        for i in range(n_samp):
            sum = pings[i]
            if self.chord_is_on:
                for j in range(self.n_notes):
                    sum += self.amps[j] * math.sin(self.args[j])
                    self.args[j] = math.fmod(self.args[j] + self.incs[j], pi2)
            sig[i] = int(sum)
        return sig

class Music(object):
    """A class to create sound from musical signals."""

    def __init__(self, audio, sample_rate=22050.0, tonic='A3'):
        self.pyaudio = audio
        self.fs = sample_rate
        self.progression = ['I', 'iii', 'vi', 'V', 'I', 'vi', 'iii', 'IV', 'V']
        self.tonic = tonic
        self.n_semis = 24
        self.tone_gen = Tones(self.fs)
        self.note_gen = None
        self.chords = []
        self.names = []
        self.n_frames = 2048
        self.change_int = 3.0
        self.audio_on = False
        self.pa_stream = None
        self.print_progression = False

    def SetupProgression(self, chord_seq=None, tonic=None, n_semitones=None):
        if chord_seq:
            self.progression = chord_seq
        else:
            sys.stderr.write('No progression specified; using default.\n')
        if tonic:
            self.tonic = tonic
        if n_semitones:
            self.n_semis = n_semitones
        self.chords = []
        self.names = []
        self.note_gen = Notes(self.tonic, self.n_semis)
        for chord in self.progression:
            self.chords.append(self.note_gen.ChordSpecToNotes(chord))
            self.names.append(self.note_gen.ChordSpecToNoteNames(chord))

    def TogglePrintProgression(self):
        self.print_progression = not self.print_progression

    def ToggleDetune(self):
        self.tone_gen.ToggleDetune()

    def TogglePing(self):
        self.tone_gen.TogglePing()

    def ToggleChord(self):
        self.tone_gen.ToggleChord()

    def HandleAudioOutput(self, in_data, n_samps, time_info, status):
        if not self.audio_on:
            return '', pyaudio.paComplete
        data = array.array('h', self.tone_gen.GetSamples(n_samps)).tostring()
        return data, pyaudio.paContinue

    def SetupAudioStream(self):
        self.StopAudioOutput()
        self.pa_stream = self.pyaudio.open(format=pyaudio.paInt16, start=False,
                                           channels=1,
                                           frames_per_buffer=self.n_frames,
                                           rate=int(self.fs), output=True,
                                        stream_callback=self.HandleAudioOutput)

    def StopAudioOutput(self):
        if self.audio_on:
            self.audio_on = False
            time.sleep(1.5 * self.n_frames/self.fs)
        if self.pa_stream:
            self.pa_stream.close()
            self.pa_stream = None

    def StartAudio(self):
        if not self.audio_on:
            self.audio_on = True
            self.pa_stream.start_stream()

    def ChangeChord(self, chord_ind):
        if self.print_progression:
            print self.progression[chord_ind], self.names[chord_ind]
        self.tone_gen.ChangeChord(self.chords[chord_ind])

    def MakeChordCompatiblePingNotes(self, chord_ind, n_pings):
        pingc = 0
        multiplier = 1.0
        pings = []
        notes = self.chords[chord_ind]
        while pingc <= n_pings:
            for note in notes:
                pings.append(note * multiplier)
                pingc += 1
                if pingc >= n_pings:
                    break
            multiplier *= 2.0
        pings.sort()
        self.tone_gen.SetupPings(pings, .5, 1.0)

    def Ping(self, note_ind):
        self.tone_gen.Ping(note_ind)

    def RepeatProgression(self, change_int=3.0, reps=1):
        self.SetupAudioStream()
        self.change_int = change_int
        rcount = reps
        while rcount > 0:
            rcount -= 1
            cind = 0
            while cind < len(self.progression):
                self.ChangeChord(cind)
                notes = []
                for freq in self.chords[cind]:
                    notes.append(freq)
                #   notes.append(2.0 * freq)
                #   notes.extend(notes)
                #   random.shuffle(notes)
                notes.sort()
                self.tone_gen.SetupPings(notes, .7, 2.0)
                self.StartAudio()
                print self.progression[cind], '   ', self.names[cind]
                for note in range(len(notes)):
                    self.tone_gen.Ping(note)
                    time.sleep(self.change_int/len(notes))
                cind = cind + 1

def main(args):
    p = pyaudio.PyAudio()
    m = Music(p, tonic='C4')
    m.SetupProgression(chord_seq=args[1:], n_semitones=24)
    m.RepeatProgression(2.0, 4)

if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)

